# Наполнение БД демо-данными (django-seed + Faker)

Гайд по созданию management-команды `seed_db`, которая заполняет PostgreSQL
тестовыми пользователями, курсами, модулями, квизами и прогрессом студентов.


---

## 1. Установка

### Задача

Подключить `django-seed`, чтобы генерировать фейковые данные через Faker
и вызывать `python manage.py seed …` / свою команду `seed_db`.

### Код

```bash
pip install django-seed
```

В `educa/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'embed_video',
    'django_seed',
]
```
в `requirements.txt`:

```text
django-seed==0.3.1
```

### Разбор

- `django-seed` — обёртка над **Faker** специально для Django-моделей.
- Пакет сам ставит зависимости `Faker` и `toposort`.
- Без записи в `INSTALLED_APPS` не заработает встроенная команда
  `python manage.py seed`, а наш `Seed.seeder()` всё равно можно импортировать —
  но для единообразия пакет лучше подключить явно.

---

## 2. Структура файлов

### Задача

Сделать так, чтобы Django нашёл команду `seed_db`.

### Код

```text
courses/
  management/
    __init__.py          # пустой
    commands/
      __init__.py        # пустой
      seed_db.py         # весь код ниже
```

### Разбор

- Management-команды живут только в
  `<app>/management/commands/<имя>.py`.
- Имя файла = имя команды: `seed_db.py` → `python manage.py seed_db`.
- Оба `__init__.py` обязательны: без них Python не считает папки пакетами,
  и Django команду не зарегистрирует.
- Класс внутри файла **должен** называться `Command` и наследоваться от
  `BaseCommand`.

---

## 3. Что создаёт команда

| Сущность | Как создаётся | Почему так |
|---|---|---|
| `Subject` | `Seed.add_entity` | простая модель, без вложенности |
| `Badge` | `add_entity` на курс | тоже «плоская» запись |
| Users | вручную + `set_password` | нужны **известные** логины/пароли |
| `Course` → `Module` → контент | вручную | нужна связная иерархия |
| `Content` (GFK) | вручную | django-seed плохо дружит с GenericForeignKey |
| Вопросы/ответы | вручную | нужен ровно один `is_correct=True` |
| Прогресс / сертификаты | вручную | логика «часть модулей пройдена» |

**Идея:** django-seed для «плоских» сущностей, руками — для структуры курса.
Faker берём из `seeder.faker`, чтобы текст был правдоподобным.

---

## 4. Импорты и константы

### Задача

Подготовить всё, что понадобится команде: модели, Seed, пароль, URL видео.

### Код

В начало `courses/management/commands/seed_db.py`:

```python
import random
import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django_seed import Seed

from courses.models import (
    Answer, Content, Course, Module, Question, Quiz, QuizResult,
    Subject, Text, Video,
)
from students.models import (
    Badge, Certificate, CourseProgress, ModuleProgress, UserBadge,
)

DEFAULT_PASSWORD = 'password123'

YOUTUBE_URLS = [
    'https://www.youtube.com/watch?v=rfscVS0vtbw',
    'https://www.youtube.com/watch?v=kqtD5dpn9C8',
    'https://www.youtube.com/watch?v=8DvywoWv6fI',
    'https://www.youtube.com/watch?v=Z1Yd7upQsXY',
]
```

### Разбор

| Импорт / константа | Зачем |
|---|---|
| `random` | выбор преподавателя, числа модулей, сэмпл студентов |
| `uuid` | fallback для уникального `slug`, когда `slugify` пустой |
| `User` | преподаватели и студенты |
| `ContentType` | связать `Content` с Text/Video/Quiz через GFK |
| `BaseCommand` | базовый класс management-команды |
| `transaction.atomic` | либо всё запишется, либо ничего (при ошибке откат) |
| `timezone.now` | дата завершения модуля/курса |
| `slugify` | человекочитаемый URL-slug из названия |
| `Seed` | точка входа django-seed |
| `DEFAULT_PASSWORD` | один пароль на всех демо-юзеров — удобно для тестов |
| `YOUTUBE_URLS` | реальные публичные ролики; Faker-URL'ы YouTube не откроет |

---

## 5. Класс команды и аргументы CLI

### Задача

Описать команду и параметры `--teachers`, `--students`, `--courses`, `--clear`.

### Код

```python
class Command(BaseCommand):
    help = 'Наполняет БД демо-данными через django-seed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--teachers', type=int, default=3,
            help='Количество преподавателей (по умолчанию 3)',
        )
        parser.add_argument(
            '--students', type=int, default=10,
            help='Количество студентов (по умолчанию 10)',
        )
        parser.add_argument(
            '--courses', type=int, default=5,
            help='Количество курсов (по умолчанию 5)',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Очистить связанные таблицы перед наполнением',
        )
```

### Разбор

- `help` — текст в `python manage.py help seed_db`.
- `add_arguments` — стандартный argparse Django.
- `type=int` — CLI-строка сразу станет числом в `options['teachers']`.
- `default=…` — можно запускать просто `seed_db` без флагов.
- `action='store_true'` — флаг без значения: есть `--clear` → `True`,
  нет → `False`.

Пример:

```bash
python manage.py seed_db --clear --teachers 2 --students 5 --courses 3
```

---

## 6. Точка входа `handle`

### Задача

Собрать сценарий сида: создать seeder → (опционально очистить) →
предметы → юзеры → курсы → запись → прогресс.

### Код

```python
    def handle(self, *args, **options):
        seeder = Seed.seeder(locale='ru_RU')
        fake = seeder.faker

        with transaction.atomic():
            if options['clear']:
                self._clear()

            subjects = self._seed_subjects(seeder)
            teachers = self._seed_teachers(fake, options['teachers'])
            students = self._seed_students(fake, options['students'])
            courses = self._seed_courses(
                seeder, fake, subjects, teachers, options['courses'])
            self._enroll_students(fake, courses, students)
            self._seed_progress(seeder, fake, students)

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {Subject.objects.count()} предметов, '
            f'{len(teachers)} преподавателей, '
            f'{len(students)} студентов, '
            f'{len(courses)} курсов.\n'
            f'Пароль для всех пользователей: {DEFAULT_PASSWORD}\n'
            f'Логины: teacher1…, student1…, admin'
        ))
```

### Разбор

```text
Seed.seeder(locale='ru_RU')
        │
        ├─ seeder.add_entity(...)   ← массовое создание моделей
        └─ seeder.faker             ← тот же Faker (имена, абзацы, фразы)
```

- `locale='ru_RU'` — русские имена/слова (часть провайдеров всё равно на EN).
- `fake = seeder.faker` — короткий алиас, чтобы не писать `seeder.faker` везде.
- `transaction.atomic()` — если на середине упадёт исключение, БД не останется
  «наполовину насеянной».
- Порядок важен: сначала предметы и юзеры (FK), потом курсы, потом M2M и прогресс.
- `self.stdout.write(self.style.SUCCESS(...))` — зелёный вывод в терминал.

---

## 7. Очистка `_clear`

### Задача

Перед повторным сидом удалить демо-данные, чтобы не плодить дубликаты курсов.

### Код

```python
    def _clear(self):
        self.stdout.write('Очистка данных…')
        UserBadge.objects.all().delete()
        Badge.objects.all().delete()
        Certificate.objects.all().delete()
        CourseProgress.objects.all().delete()
        ModuleProgress.objects.all().delete()
        QuizResult.objects.all().delete()
        Content.objects.all().delete()
        Answer.objects.all().delete()
        Question.objects.all().delete()
        Quiz.objects.all().delete()
        Text.objects.all().delete()
        Video.objects.all().delete()
        Module.objects.all().delete()
        Course.objects.all().delete()
        Subject.objects.all().delete()
        User.objects.filter(username__startswith='teacher').delete()
        User.objects.filter(username__startswith='student').delete()
        User.objects.filter(username='admin').delete()
```

### Разбор

- Удаляем **снизу вверх по зависимостям**: сначала то, что ссылается на курсы
  (`UserBadge`, прогресс, результаты), потом контент, модули, курсы, предметы.
- `Content` удаляем до `Text`/`Video`/`Quiz` — иначе останутся «осиротевшие»
  записи GFK или наоборот сломаются FK (порядок безопаснее такой).
- Юзеров трогаем **только** с префиксами `teacher` / `student` и `admin` —
  ваши личные аккаунты в БД не сотрёт.
- Без `--clear` этот метод не вызывается.

---

## 8. Предметы через django-seed

### Задача

Создать 5 категорий курсов (`Subject`) через API django-seed.

### Код

```python
    def _seed_subjects(self, seeder):
        seeder.add_entity(Subject, 5, {
            'title': lambda x: seeder.faker.unique.word().capitalize(),
            'slug': lambda x: (
                slugify(seeder.faker.unique.lexify(text='????-????'))
                or f'subject-{uuid.uuid4().hex[:8]}'
            ),
        })
        inserted = seeder.execute()
        subjects = list(
            Subject.objects.filter(pk__in=inserted[Subject]))
        self.stdout.write(f'  предметы: {len(subjects)}')
        return subjects
```

### Разбор

1. **`add_entity(Model, count, field_map)`**  
   Говорит сидеру: «создай `count` объектов `Model`».  
   Третий аргумент — словарь кастомных генераторов полей.

2. **`lambda x: …`**  
   django-seed вызывает лямбду на каждый объект.  
   Параметр `x` — сам создаваемый экземпляр (нам не нужен).

3. **`unique.word()` / `unique.lexify(...)`**  
   Faker с `.unique` не повторяет значения в рамках сессии — важно для
   `Subject.slug` (`unique=True` в модели).

4. **`lexify(text='????-????')`**  
   Заменяет `?` на случайные латинские буквы → slug вроде `abkd-wqpl`.

5. **`seeder.execute()`**  
   Реально пишет в БД. Возвращает словарь:
   `{ModelClass: [pk1, pk2, …]}`.

6. **`inserted[Subject]`**  
   Список primary key только что созданных предметов — ими удобно
   дальше кормить `_seed_courses`.

---

## 9. Преподаватели и студенты

### Задача

Создать предсказуемых пользователей с известным паролем для входа в UI.

### Код — преподаватели

```python
    def _seed_teachers(self, fake, count):
        teachers = []
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@educa.local',
                'first_name': 'Admin',
                'last_name': 'Educa',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin.set_password(DEFAULT_PASSWORD)
            admin.save()
        teachers.append(admin)

        for i in range(1, count + 1):
            username = f'teacher{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@educa.local',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'is_staff': True,
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
            teachers.append(user)
        self.stdout.write(f'  преподаватели: {len(teachers)}')
        return teachers
```

### Код — студенты

```python
    def _seed_students(self, fake, count):
        students = []
        for i in range(1, count + 1):
            username = f'student{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@educa.local',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                },
            )
            if created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
            students.append(user)
        self.stdout.write(f'  студенты: {len(students)}')
        return students
```

### Разбор

- **`get_or_create`** — повторный сид без `--clear` не упадёт на дубликате
  username и не перезапишет уже существующего юзера.
- **`defaults={...}`** — поля только при **создании**. Если юзер уже есть,
  `defaults` игнорируются.
- **`set_password` только если `created`** — иначе при каждом сиде вы бы
  сбрасывали пароль (и хешировали заново зря).
- **`set_password` + `save`** — нельзя писать
  `password='password123'` напрямую: Django хранит хеш, не открытый текст.
- **`is_staff=True`** у преподавателей — доступ в `/admin/` и CMS.
- **`is_superuser=True`** только у `admin`.
- Студенты — обычные User без staff-флагов; курсы получат через M2M позже.

---

## 10. Уникальный slug

### Задача

Гарантировать уникальный `Course.slug` даже для кириллических названий.

### Код

```python
    def _unique_slug(self, title):
        # slugify для кириллицы часто даёт пустую строку — нужен fallback
        base = slugify(title) or f'course-{uuid.uuid4().hex[:8]}'
        slug = base
        n = 1
        while Course.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug
```

### Разбор

```text
title = "Reactive multi-tasking loyalty"
        │
        ▼
slugify → "reactive-multi-tasking-loyalty"   # ок

title = "Открытая методичная функция"
        │
        ▼
slugify → ""                                 # пусто!
        │
        ▼
fallback → "course-a1b2c3d4"
```

- Цикл `while … exists()` добавляет `-1`, `-2`, … если slug уже занят.
- Без этого `Course.objects.create(...)` упадёт на `IntegrityError`
  (поле `slug` уникально).

---

## 11. Курсы, модули, бейджи

### Задача

Создать N курсов: у каждого — владелец, предмет, 2–4 модуля и один Badge.

### Код

```python
    def _seed_courses(self, seeder, fake, subjects, teachers, count):
        courses = []
        text_ct = ContentType.objects.get_for_model(Text)
        video_ct = ContentType.objects.get_for_model(Video)
        quiz_ct = ContentType.objects.get_for_model(Quiz)

        for _ in range(count):
            owner = random.choice(teachers)
            subject = random.choice(subjects)
            title = fake.catch_phrase().capitalize()
            course = Course.objects.create(
                owner=owner,
                subject=subject,
                title=title,
                slug=self._unique_slug(title),
                overview=fake.paragraph(nb_sentences=4),
            )

            seeder.add_entity(Badge, 1, {
                'name': lambda x: f'Значок: {title[:40]}',
                'description': lambda x: fake.sentence(),
                'course': lambda x: course,
                'icon': lambda x: '',
            })
            seeder.execute()

            for _ in range(random.randint(2, 4)):
                module = Module.objects.create(
                    course=course,
                    title=fake.sentence(nb_words=3).rstrip('.'),
                    description=fake.paragraph(nb_sentences=2),
                )
                self._seed_module_content(
                    fake, owner, module, text_ct, video_ct, quiz_ct)

            courses.append(course)
            self.stdout.write(f'  курс: {course.title}')
        return courses
```

### Разбор

1. **`ContentType.objects.get_for_model(Text)`**  
   Один раз достаём ContentType для Text/Video/Quiz — потом многократно
   используем при создании `Content` (GFK). Без этого пришлось бы
   дёргать БД на каждый блок контента.

2. **`random.choice(teachers)`**  
   Курс «принадлежит» случайному преподавателю (`Course.owner`).

3. **`fake.catch_phrase()`**  
   Короткий маркетинговый заголовок курса от Faker.

4. **Badge через `add_entity`**  
   Пример «точечного» django-seed: одна запись, поля заданы лямбдами.
   `icon: lambda x: ''` — поле `ImageField(blank=True)`, файла нет.
   `course: lambda x: course` — привязка к только что созданному курсу
   (замыкание на локальную переменную).

5. **Модули**  
   `order` не передаём — `OrderField` сам проставит 0, 1, 2, …

6. **`_seed_module_content(...)`**  
   Наполняет каждый модуль текстом, видео и квизом (следующий блок).

---

## 12. Контент модуля (текст / видео / квиз)

### Задача

В каждом модуле сделать три блока контента и связать их через `Content` (GFK).

### Код

```python
    def _seed_module_content(
            self, fake, owner, module, text_ct, video_ct, quiz_ct):
        text = Text.objects.create(
            owner=owner,
            title=fake.sentence(nb_words=4).rstrip('.'),
            content='\n\n'.join(fake.paragraphs(nb=3)),
        )
        Content.objects.create(
            module=module, content_type=text_ct, object_id=text.id)

        video = Video.objects.create(
            owner=owner,
            title=fake.sentence(nb_words=3).rstrip('.'),
            url=random.choice(YOUTUBE_URLS),
        )
        Content.objects.create(
            module=module, content_type=video_ct, object_id=video.id)

        quiz = Quiz.objects.create(
            owner=owner,
            title=f'Тест: {module.title}',
            description=fake.sentence(),
            pass_percent=70,
        )
        Content.objects.create(
            module=module, content_type=quiz_ct, object_id=quiz.id)
        self._seed_quiz_questions(fake, quiz)
```

### Разбор

Схема связи:

```text
Module
  └── Content (module, content_type, object_id)
          │
          ├── content_type=Text  + object_id → Text
          ├── content_type=Video + object_id → Video
          └── content_type=Quiz  + object_id → Quiz
```

- Сначала создаём сам item (`Text` / `Video` / `Quiz`) — получаем `id`.
- Потом создаём обёртку `Content` с парой `(content_type, object_id)`.
- В шаблоне курса Django достаёт `content.item` через GenericForeignKey.
- `pass_percent=70` — порог сдачи, как в модели по умолчанию.
- `File` / `Image` намеренно не создаём: нужны реальные файлы на диске.

---

## 13. Вопросы и ответы квиза

### Задача

На каждый квиз — 3–5 вопросов, у каждого 4 варианта и **ровно один** верный.

### Код

```python
    def _seed_quiz_questions(self, fake, quiz):
        for _ in range(random.randint(3, 5)):
            question = Question.objects.create(
                quiz=quiz,
                text=fake.sentence(nb_words=8).rstrip('.') + '?',
            )
            correct_idx = random.randint(0, 3)
            for j in range(4):
                Answer.objects.create(
                    question=question,
                    text=fake.word().capitalize(),
                    is_correct=(j == correct_idx),
                )
```

### Разбор

- `correct_idx` выбирается один раз на вопрос.
- В цикле `j in range(4)` флаг `is_correct=(j == correct_idx)` —
  `True` только у одного ответа.
- Если бы все ответы были `False` или несколько `True`, проверка квиза
  в `QuizTakeView` работала бы некорректно.
- `order` у вопроса снова выставит `OrderField` сам.

---

## 14. Запись студентов на курсы

### Задача

Привязать случайных студентов к каждому курсу (M2M `Course.students`).

### Код

```python
    def _enroll_students(self, fake, courses, students):
        for course in courses:
            count = random.randint(3, len(students))
            enrolled = random.sample(students, count)
            course.students.add(*enrolled)
```

### Разбор

- `random.sample(list, k)` — `k` **уникальных** элементов (без повторов).
- `course.students.add(*enrolled)` — распаковка списка в аргументы M2M.
- После этого у студента работает
  `student.courses_joined.all()` (related_name с модели `Course`).

---

## 15. Прогресс, сертификаты, бейджи

### Задача

Сымитировать, что часть студентов уже прошла часть модулей (и тесты),
а кто прошёл всё — получил сертификат и бейдж.

### Код

```python
    def _seed_progress(self, seeder, fake, students):
        now = timezone.now()
        for student in students:
            for course in student.courses_joined.all():
                modules = list(course.modules.all())
                if not modules:
                    continue

                done_count = random.randint(0, len(modules))
                for module in modules[:done_count]:
                    ModuleProgress.objects.get_or_create(
                        user=student,
                        module=module,
                        defaults={
                            'completed': True,
                            'completed_at': now,
                        },
                    )
                    for content in module.contents.filter(
                            content_type__model='quiz'):
                        quiz = Quiz.objects.filter(
                            pk=content.object_id).first()
                        if not quiz:
                            continue
                        QuizResult.objects.update_or_create(
                            user=student,
                            quiz=quiz,
                            defaults={
                                'score': random.randint(70, 100),
                                'passed': True,
                            },
                        )

                if done_count == len(modules):
                    CourseProgress.objects.get_or_create(
                        user=student,
                        course=course,
                        defaults={
                            'completed': True,
                            'completed_at': now,
                        },
                    )
                    Certificate.objects.get_or_create(
                        user=student, course=course)
                    for badge in course.badges.all():
                        UserBadge.objects.get_or_create(
                            user=student, badge=badge)
```

### Разбор

```text
студент записан на курс
        │
        ▼
done_count = случайно от 0 до N модулей
        │
        ├─ первые done_count модулей → ModuleProgress(completed=True)
        │         └─ квизы модуля → QuizResult(passed=True, score≥70)
        │
        └─ если done_count == N → CourseProgress + Certificate + UserBadge
```

- Берём только курсы, на которые студент **уже записан**
  (`courses_joined`) — иначе прогресс без enrollment бессмысленен.
- `modules[:done_count]` — «пройдены первые K модулей» (как будто шли по порядку).
- Для каждого пройденного модуля сразу ставим успешный `QuizResult` —
  иначе `mark_module_complete` / проверка «все квизы сданы» не сойдётся
  с реальностью UI.
- `update_or_create` / `get_or_create` — идемпотентность при повторном сиде.
- Сертификат и бейдж выдаём **только** при 100% модулей — как в
  `on_course_completed` в `students/services.py`.

> Параметры `seeder` и `fake` в сигнатуре оставлены для единообразия /
> возможных расширений; в текущей версии прогресс строится через `random`.

---

## 16. Запуск и логины

### Команды

```bash
# проверить, что команда видна
python manage.py help seed_db

# базовый прогон (3 преподавателя, 10 студентов, 5 курсов)
python manage.py seed_db

# очистить сид-данные и создать заново
python manage.py seed_db --clear

# свои объёмы
python manage.py seed_db --clear --teachers 2 --students 5 --courses 3
```

### Учётные данные

| Логин | Пароль | Роль |
|---|---|---|
| `admin` | `password123` | superuser + преподаватель |
| `teacher1` … | `password123` | staff / преподаватель |
| `student1` … | `password123` | студент |

### Встроенная команда пакета

```bash
python manage.py seed courses --number=5
python manage.py seed students --number=10
```

Она **не** знает структуру Educa (модули, GFK, один верный ответ).
Для связных демо-данных используйте `seed_db` из этого гайда.

---

## 17. Важные детали

### Повторный запуск без `--clear`

- Юзеры — `get_or_create` → безопасно.
- Курсы — каждый раз **добавляются** новые.
- Для чистого состояния всегда: `seed_db --clear`.

### OrderField

У `Module`, `Content`, `Question` поле `order` заполняется само при
`create()`, если не передавать значение (`courses.fields.OrderField`).

### Видео YouTube (Error 153)

Если эмбед показывает *Error 153*, в `educa/settings.py`:

```python
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
```

В шаблоне iframe — `referrerpolicy="strict-origin-when-cross-origin"`.

### Минимальный пример только django-seed

В `python manage.py shell`:

```python
from django_seed import Seed
from courses.models import Subject

seeder = Seed.seeder(locale='ru_RU')
seeder.add_entity(Subject, 5, {
    'title': lambda x: seeder.faker.word().capitalize(),
    'slug': lambda x: seeder.faker.unique.lexify(text='subj-????'),
})
print(seeder.execute())
```

Так можно быстро понять цикл `add_entity` → `execute` без всей LMS-структуры.
