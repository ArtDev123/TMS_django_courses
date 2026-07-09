# Вариант 2 — Платформа для онлайн-курсов

Пошаговый гайд по разработке LMS (Learning Management System) на **Django 6.0.7**.  
Материал основан на главах 12–14 книги *Django 4 by Example* (проект Educa), дополнен под задание TMS и переписан под **PostgreSQL**, **викторины**, **прогресс**, **сертификаты**. Кеширование Redis **не используется**.

## Как читать этот гайд

Каждый технический блок устроен одинаково:

1. **Задача** — что должно получиться и зачем этот шаг нужен в проекте.
2. **Код** — что именно пишем в файл.
3. **Разбор** — построчно или по логическим частям: *зачем* каждая строка/конструкция.
4. **✅ Проверка этапа** — команды и URL: что должно работать **прямо сейчас**, прежде чем идти дальше.

> **Навигация:** ссылки в оглавлении ведут на `#section-N` (разделы) и `#stage-N` (проверки этапов). Якоря заданы явно — работают в Cursor, GitHub и VS Code.

> **Правило:** не переходите к следующему разделу, пока текущий этап не пройден. Так вы сразу видите, где сломалось.

Любая страница сайта в Django — это цепочка:

```text
URL (urls.py)  →  View (views.py)  →  Template (templates/*.html)
     ↓                    ↓                      ↓
«какой адрес»      «что делать с запросом»   «что показать пользователю»
```

**Пример:** студент открывает `/students/courses/`

1. `students/urls.py` находит маршрут `student_course_list` → класс `StudentCourseListView`.
2. View проверяет: пользователь залогинен? → запрашивает из PostgreSQL только его курсы.
3. View передаёт список курсов в шаблон.
4. Шаблон рисует HTML с прогрессом.

---

## Оглавление

1. [Этапы разработки с проверками](#section-0) ← **начните здесь при пошаговой сборке**
2. [Что мы строим](#section-1)
3. [Подготовка окружения](#section-2)
4. [PostgreSQL](#section-3)
5. [Создание проекта Django](#section-4)
6. [Модели данных](#section-5)
7. [Миграции, admin, фикстуры](#section-6)
8. [Аутентификация и базовые шаблоны](#section-7)
9. [CMS для преподавателей](#section-8)
10. [Публичный каталог курсов](#section-9)
11. [Регистрация и зачисление студентов](#section-10)
12. [Просмотр содержимого курса](#section-11)
13. [Отслеживание прогресса](#section-12)
14. [Викторины и тесты](#section-13)
15. [Сертификаты и награды](#section-14)
16. [Карта URL и сценарии пользователей](#section-15)
17. [Структура файлов проекта](#section-16)
18. [Чеклист и типичные ошибки](#section-17)

---

<a id="section-0"></a>
## 0. Этапы разработки с проверками

Дорожная карта: **14 этапов**, каждый завершается блоком «✅ Проверка» в соответствующем разделе. Выполняйте строго по порядку.


| Этап   | Раздел                                            | Что реализуете                   | Критерий «готово»                 |
| ------ | ------------------------------------------------- | -------------------------------- | --------------------------------- |
| **1**  | [§2](#stage-1)  | venv, pip, requirements          | Django 6.0.7 импортируется        |
| **2**  | [§3](#stage-2)  | PostgreSQL, `.env`               | `psql` + `SELECT 1` от educa_user |
| **3**  | [§4](#stage-3)  | startproject, settings, urls     | `manage.py check` без ошибок      |
| **4**  | [§5–6](#stage-4)  | models, migrate, admin, fixtures | Admin, subjects в БД              |
| **5**  | [§7](#stage-5)  | base.html, login, CSS            | Страница входа с дизайном         |
| **6**  | [§8.1–8.4](#stage-6)  | Instructors, CRUD курсов         | `/course/mine/` — список курсов   |
| **7**  | [§8.5–8.6](#stage-7)  | formset модулей, Text/File/…     | Модули + текст в CMS              |
| **8**  | [§8.7](#stage-8)  | Quiz + вопросы на сайте          | Вопросы викторины в CMS           |
| **9**  | [§9](#stage-9)  | CourseListView, detail           | Каталог `/`, предпросмотр курса   |
| **10** | [§10](#stage-10)  | register, enroll                 | Студент записан на курс           |
| **11** | [§11](#stage-11)  | StudentCourseDetailView          | Контент модуля у студента         |
| **12** | [§12](#stage-12)  | ModuleProgress, services         | Progress bar, галочки ✓           |
| **13** | [§13](#stage-13)  | QuizTakeView, result             | Тест сдан / не сдан               |
| **14** | [§14](#stage-14)  | Certificate, profile             | Сертификат при 100%               |


**Тестовые пользователи** (создайте на этапе 4–6 и используйте дальше):


| Логин     | Роль              | Как создать                            |
| --------- | ----------------- | -------------------------------------- |
| `admin`   | суперпользователь | `createsuperuser`                      |
| `teacher` | преподаватель     | Admin → Users + группа **Instructors** |
| `student` | студент           | `/students/register/` или Admin        |


**Команда для каждого этапа с сервером:**

```bash
source env/educa/bin/activate
python manage.py runserver
# Откройте URL из блока «✅ Проверка» в браузере
```

---

## Быстрый старт (end-to-end)

> Если собираете **пошагово** — используйте [§0 Этапы](#section-0) и проверяйте каждый этап.  
> Блок ниже — для тех, кто поднимает уже готовый код из репозитория одним заходом.

```bash
# 1. Клонировать / перейти в папку проекта
cd TMS_django_courses

# 2. PostgreSQL (один раз, через Unix-сокет)
sudo -u postgres psql -v ON_ERROR_STOP=1 -f scripts/init_postgres.sql

# 3. Python-окружение
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Переменные окружения (скопировать и при необходимости изменить пароль)
cp .env.example .env   # или создайте .env вручную — см. раздел 3.4

# 5. База Django
python manage.py migrate
python manage.py loaddata subjects
python manage.py createsuperuser

# 6. Группа преподавателей (в admin: Groups → Instructors + права courses.*)
#    Создайте пользователя teacher и добавьте в Instructors

# 7. Запуск
python manage.py runserver
```

**Проверка сценария:**


| Шаг         | URL                                                                                  | Ожидание             |
| ----------- | ------------------------------------------------------------------------------------ | -------------------- |
| Каталог     | [http://127.0.0.1:8000/](http://127.0.0.1:8000/)                                     | Список курсов        |
| CMS         | [http://127.0.0.1:8000/course/mine/](http://127.0.0.1:8000/course/mine/)             | Курсы преподавателя  |
| Регистрация | [http://127.0.0.1:8000/students/register/](http://127.0.0.1:8000/students/register/) | Форма                |
| Мои курсы   | [http://127.0.0.1:8000/students/courses/](http://127.0.0.1:8000/students/courses/)   | После входа студента |


**Итоговая структура репозитория** (проект в **корне**, не во вложенной папке):

```text
TMS_django_courses/
├── manage.py                 # DJANGO_SETTINGS_MODULE=educa.settings
├── .env                      # секреты (не в git)
├── requirements.txt
├── educa/                    # настройки Django (settings, urls, wsgi)
├── courses/                  # модели, CMS, каталог, static, templates
├── students/                 # регистрация, прогресс, викторины, сертификаты
├── scripts/init_postgres.sql
├── media/                    # загрузки (gitignore)
└── guide.md
```

---

<a id="section-1"></a>
## 1. Что мы строим

### 1.1. Задача из ТЗ

Нужна платформа, где:


| Функционал из задания                           | Кто использует  | Где в проекте               |
| ----------------------------------------------- | --------------- | --------------------------- |
| Регистрация и прогресс                          | Студент         | приложение `students`       |
| Создание курсов (текст, файлы, викторины)       | Преподаватель   | приложение `courses`, CMS   |
| Главная со списком **активных** курсов студента | Студент         | `/students/courses/`        |
| Предпросмотр курса + форма записи               | Гость / студент | `/course/<slug>/`           |
| Просмотр модулей, ответы на вопросы, тесты      | Студент         | `/students/course/<id>/...` |
| Сертификаты и награды                           | Студент         | выдаются при 100% прогресса |


### 1.2. Два типа пользователей

Оба типа — обычные записи в таблице `auth_user` (модель `User` из Django):

- **Преподаватель (Instructor)** — состоит в группе `Instructors`, имеет права на CRUD курсов. Заходит в CMS по адресу `/course/mine/`.
- **Студент** — регистрируется сам, записывается на курсы. После входа попадает на `/students/courses/`.

Один пользователь теоретически может быть и преподавателем, и студентом — это разные роли, не разные таблицы.

### 1.3. Структура данных (упрощённо)

```text
Subject (Предмет: «Python», «Математика»)
  └── Course (Курс: «Django для начинающих»)
        ├── owner → User (преподаватель)
        ├── students → User[] (записанные студенты)
        └── Module (Модуль 1, Модуль 2, ...)
              └── Content (обёртка с порядком)
                    └── item → Text | File | Image | Video | Quiz
```

**Почему так сложно с Content?**  
В одном модуле могут быть и текст, и PDF, и видео, и тест. Вместо одной таблицы «всё подряд» используется **полиморфная связь** (GenericForeignKey): одна таблица `Content` указывает на разные таблицы контента.

### 1.4. Как студент проходит курс

```text
1. Регистрация          → /students/register/
2. Каталог курсов       → /
3. Предпросмотр         → /course/django-basics/
4. «Записаться»         → POST /students/enroll-course/
5. Мои курсы (главная)  → /students/courses/     ← список активных курсов + %
6. Материалы модуля     → /students/course/3/12/
7. Викторина            → /students/course/3/quiz/5/
8. «Модуль пройден»     → POST → прогресс +1
9. 100% модулей         → сертификат + награды
```

---

<a id="section-2"></a>
## 2. Подготовка окружения

### 2.1. Что должно быть установлено


| Компонент  | Версия           | Зачем                           |
| ---------- | ---------------- | ------------------------------- |
| Python     | 3.12+            | Django 6 требует Python ≥ 3.12  |
| PostgreSQL | любая актуальная | база данных на `localhost:5432` |
| pip        | актуальный       | установка пакетов               |


Проверка:

```bash
python3 --version    # Python 3.12.x или выше
psql --version
```

### 2.2. Виртуальная среда

Изолированная среда, чтобы пакеты проекта не смешивались с системными:

```bash
cd TMS_django_courses   # или ваш каталог проекта
python3 -m venv env/educa
source env/educa/bin/activate    # Linux/macOS
```

После активации в начале строки терминала появится `(educa)`.

Windows:

```powershell
.\env\educa\Scripts\activate
```

### 2.3. Установка зависимостей

**Задача:** установить все Python-библиотеки, без которых проект не запустится.

```bash
pip install Django==6.0.7
pip install Pillow
pip install psycopg2-binary
pip install django-embed-video
pip install django-braces
```

**Разбор — зачем каждый пакет:**


| Пакет                | Зачем нужен                                                                                                      |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `Django==6.0.7`      | Сам фреймворк: ORM, admin, auth, шаблоны, URL                                                                    |
| `Pillow`             | Django не умеет обрабатывать картинки сам — нужна эта библиотека для `ImageField` / загрузки изображений в курсы |
| `psycopg2-binary`    | «Переводчик» между Python и PostgreSQL. Без него Django не подключится к вашей БД                                |
| `django-embed-video` | Вставка YouTube/Vimeo в шаблон одной строкой `{% video url %}`                                                   |
| `django-braces`      | Готовые mixins (например `CsrfExemptMixin` для AJAX-сортировки модулей). Можно обойтись без него на первом этапе |


Создайте файл `requirements.txt` в корне рабочей папки — чтобы на другой машине установить всё одной командой `pip install -r requirements.txt`:

```text
Django==6.0.7
Pillow
psycopg2-binary
django-embed-video
django-braces
```

> **Django 6.0.7** — последняя стабильная версия на момент написания гайда. Документация: [https://docs.djangoproject.com/en/6.0/](https://docs.djangoproject.com/en/6.0/)

Проверка:

```bash
python -c "import django; print(django.get_version())"
# 6.0.7
```

<a id="stage-1"></a>
### ✅ Проверка этапа 1 — окружение


| #   | Действие                                                 | Ожидание           |
| --- | -------------------------------------------------------- | ------------------ |
| 1   | `python3 --version`                                      | Python 3.12+       |
| 2   | `source env/educa/bin/activate`                          | В prompt `(educa)` |
| 3   | `pip install -r requirements.txt`                        | Без ошибок         |
| 4   | `python -c "import django; print(django.get_version())"` | `6.0.7`            |
| 5   | `python -c "import PIL, psycopg2, embed_video, braces"`  | Без ImportError    |


**Не работает?** → раздел [17.2](#section-17-errors), строка про psycopg2.

---

<a id="section-3"></a>
## 3. PostgreSQL

### 3.1. Зачем PostgreSQL, а не SQLite

В задании указан PostgreSQL на хосте. Для production LMS это правильный выбор: надёжнее при множестве пользователей, лучше работает с файлами и связями many-to-many (зачисление студентов).

### 3.2. Создание базы и пользователя

На машине должен быть запущен PostgreSQL на порту **5432**. Выполните скрипт из репозитория **через Unix-сокет** (без `-h localhost` — иначе потребуется пароль суперпользователя postgres):

```bash
sudo -u postgres psql -v ON_ERROR_STOP=1 -f scripts/init_postgres.sql
```

Скрипт **идемпотентный**: при повторном запуске сбрасывает пароль `educa_user`, не падает если пользователь уже есть.


| Объект          | Значение                                                     |
| --------------- | ------------------------------------------------------------ |
| Пользователь БД | `educa_user`                                                 |
| Пароль          | `educa_secret_change_me` ← **смените в `.env` перед сдачей** |
| База данных     | `educa`                                                      |
| Права           | CREATE, SELECT, INSERT, UPDATE, DELETE на schema `public`    |


> **Не используйте** `psql -U postgres -h localhost ...` на Linux без настроенного пароля — получите `password authentication failed`.

### 3.3. Проверка подключения

```bash
PGPASSWORD=educa_secret_change_me psql -U educa_user -h localhost -p 5432 -d educa -c "SELECT 1;"
```

Ожидаемый результат:

```text
 ?column?
----------
        1
```

Если ошибка «password authentication failed» — перезапустите `init_postgres.sql` или проверьте `DB_PASSWORD` в `.env`.

### 3.4. Файл `.env`

**Задача:** хранить секреты вне кода. Django читает `.env` при старте (см. `educa/settings.py`).

Создайте `.env` в **корне** проекта (рядом с `manage.py`):

```env
# Django
SECRET_KEY=django-insecure-tms-educa-dev-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (должно совпадать с init_postgres.sql)
DB_NAME=educa
DB_USER=educa_user
DB_PASSWORD=educa_secret_change_me
DB_HOST=localhost
DB_PORT=5432
```

**Разбор загрузки в `educa/settings.py`:**

```python
def _load_env():
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip())

_load_env()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'educa'),
        'USER': os.environ.get('DB_USER', 'educa_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'educa_secret_change_me'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```


| Строка                       | Зачем                                                 |
| ---------------------------- | ----------------------------------------------------- |
| `setdefault`                 | Не перезаписывает переменные, уже заданные в shell/CI |
| `BASE_DIR / '.env'`          | Файл лежит в корне репозитория                        |
| `.gitignore` содержит `.env` | Секреты не попадают в git                             |


### 3.5. Как Django подключается к PostgreSQL

Django использует адаптер `psycopg2` (пакет `psycopg2-binary`). В `settings.py` блок `DATABASES` говорит Django, куда писать таблицы. Команда `migrate` создаст в PostgreSQL все таблицы (`auth_user`, `courses_course` и т.д.).

<a id="stage-2"></a>
### ✅ Проверка этапа 2 — PostgreSQL и .env


| #   | Действие                                                                | Ожидание                 |
| --- | ----------------------------------------------------------------------- | ------------------------ |
| 1   | `sudo -u postgres psql -v ON_ERROR_STOP=1 -f scripts/init_postgres.sql` | `GRANT` без ошибок       |
| 2   | `PGPASSWORD=... psql -U educa_user -h localhost -d educa -c "SELECT 1"` | Одна строка `1`          |
| 3   | Файл `.env` в корне рядом с `manage.py`                                 | Переменные `DB_*` заданы |
| 4   | Пароль в `.env` = пароль в init script                                  | Совпадают                |


**Не работает?**

- `connection refused` → PostgreSQL не запущен: `sudo systemctl start postgresql`
- `password authentication failed` для postgres → не используйте `-h localhost`, см. §3.2

---

<a id="section-4"></a>
## 4. Создание проекта Django

### 4.1. Команды

**Задача:** создать каркас проекта в **корне рабочей папки** (не во вложенной `educa/educa/`).

```bash
cd TMS_django_courses          # корень репозитория
django-admin startproject educa .
django-admin startapp courses
django-admin startapp students
```

**Разбор команд:**

- `startproject educa .` — точка в конце: конфиг `educa/` и `manage.py` в **текущей** папке.
- `startapp courses` — приложение курсов, CMS, моделей контента.
- `startapp students` — регистрация, прогресс, сертификаты.

Что получилось:


| Путь                | Назначение                                      |
| ------------------- | ----------------------------------------------- |
| `manage.py`         | CLI: `migrate`, `runserver`, `shell`            |
| `educa/settings.py` | БД, приложения, `.env`, media/static            |
| `educa/urls.py`     | корневой маршрутизатор                          |
| `courses/`          | модели Course/Module/Content, CMS, каталог, CSS |
| `students/`         | регистрация, прогресс, викторины, сертификаты   |


### 4.2. Полная настройка `educa/settings.py`

**Задача:** сообщить Django, какие приложения включены, к какой БД подключаться, где хранить файлы и куда перенаправлять после входа.

Откройте `educa/settings.py`. Ниже — ключевые блоки (полный файл — в репозитории).

#### INSTALLED_APPS — какие приложения активны

```python
INSTALLED_APPS = [
    'courses.apps.CoursesConfig',
    'students.apps.StudentsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',  # нужен для GenericForeignKey
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'embed_video',  # встраивание YouTube/Vimeo
]
```

**Разбор:**

- `'courses.apps.CoursesConfig'` — Django загрузит models, admin, templates из `courses/`.
- `'students.apps.StudentsConfig'` — то же для `students/`.
- `'django.contrib.admin'` — панель `/admin/`.
- `'django.contrib.auth'` — пользователи, группы, права, login/logout.
- `'django.contrib.contenttypes'` — **обязателен** для полиморфного контента (`GenericForeignKey`). Без него `Content.item` не заработает.
- `'django.contrib.sessions'` — хранит «кто залогинен» между запросами (cookie + таблица `django_session`).
- `'django.contrib.messages'` — flash-сообщения «Курс сохранён».
- `'django.contrib.staticfiles'` — раздача CSS/JS.
- `'embed_video'` — стороннее приложение для видео.

> **Порядок важен частично:** ваши приложения обычно ставят **выше** contrib, чтобы при необходимости переопределять шаблоны.

#### DATABASES — подключение к PostgreSQL через `.env`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'educa'),
        'USER': os.environ.get('DB_USER', 'educa_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'educa_secret_change_me'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

**Разбор каждого ключа:**

- `ENGINE` — драйвер `postgresql` + пакет `psycopg2-binary`.
- `NAME` / `USER` / `PASSWORD` — из `.env`, совпадают с `init_postgres.sql`.
- `HOST` / `PORT` — PostgreSQL на `localhost:5432`.

#### MEDIA и STATIC — два разных типа файлов

```python
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATIC_URL = 'static/'
```

**Разбор:**

- **MEDIA** — файлы, которые **загружает пользователь** (PDF, картинки курсов). Лежат в `media/files/`, `media/images/`. URL: `/media/files/lecture.pdf`.
- **STATIC** — файлы **разработчика** (CSS, JS). Лежат в `courses/static/css/base.css`. URL: `/static/css/base.css`.

Путаница между ними — частая ошибка новичков.

#### LOGIN_REDIRECT_URL — куда идти после входа

```python
LOGIN_REDIRECT_URL = '/students/courses/'
LOGOUT_REDIRECT_URL = '/'
```

**Разбор:**

- После успешного login Django перенаправит на `/students/courses/` — **главная ЛК студента** из ТЗ.
- После logout — на каталог `/`.

#### TEMPLATES — где искать HTML-шаблоны

```python
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]
```

**Разбор:**

- `APP_DIRS = True` — искать шаблоны в `*/templates/` каждого приложения.
- `context_processors` — автоматически добавляют в **каждый** шаблон:
  - `request` — текущий HTTP-запрос;
  - `user` — залогиненный пользователь (`request.user`);
  - `messages` — уведомления.

Без `auth` context processor в шаблоне не было бы `request.user.is_authenticated`.

### 4.3. Главный файл URL — `educa/urls.py`

**Задача:** связать адреса в браузере с view-классами. Без этого любой URL даст 404.

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('course/', include('courses.urls')),
    path('students/', include('students.urls')),
    path('', include('courses.public_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Разбор построчно:**


| Строка                                        | Зачем                                                                                                                     |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `path('accounts/login/', LoginView...)`       | Готовая форма входа. `name='login'` — чтобы в шаблоне писать `{% url 'login' %}`, а не hardcode `/accounts/login/`        |
| `path('accounts/logout/', LogoutView...)`     | Выход из системы, удаление сессии                                                                                         |
| `path('admin/', admin.site.urls)`             | Подключает **все** URL админки одной строкой                                                                              |
| `path('course/', include('courses.urls'))`    | Всё CMS преподавателя: `/course/mine/`, `/course/create/` и т.д. — файлы в `courses/urls.py`                              |
| `path('students/', include('students.urls'))` | Регистрация, мои курсы, викторины — в `students/urls.py`                                                                  |
| `path('', include('courses.public_urls'))`    | **Пустой префикс** = главная `/` — публичный каталог                                                                      |
| `if settings.DEBUG: ... static(...)`          | В режиме разработки Django сам отдаёт загруженные файлы из `media/`. **В production это отключают** — медиа раздаёт nginx |


**Почему `include()`?**  
Каждое приложение хранит свои URL. Главный `urls.py` только «собирает» их. Так проще поддерживать: студенты — в `students/`, курсы — в `courses/`.

**Проверка на этом этапе:**

```bash
python manage.py check
# System check identified no issues (0 silenced).
```

<a id="stage-3"></a>
### ✅ Проверка этапа 3 — каркас Django


| #   | Действие                                                     | Ожидание                                                |
| --- | ------------------------------------------------------------ | ------------------------------------------------------- |
| 1   | `python manage.py check`                                     | 0 issues                                                |
| 2   | `python manage.py runserver`                                 | Сервер на `:8000`                                       |
| 3   | [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) | Страница входа admin (ещё без суперпользователя — норм) |
| 4   | Структура: `manage.py`, `educa/`, `courses/`, `students/`    | В **корне**, не `educa/educa/`                          |


**Файлы, которые должны существовать:** `educa/settings.py`, `educa/urls.py`, `courses/apps.py`, `students/apps.py`.

---

<a id="section-5"></a>
## 5. Модели данных

Все модели курсов — в `courses/models.py`.  
Модели прогресса, сертификатов — в `students/models.py` (разделы 12–14).

### 5.1. OrderField — автоматический порядок

**Задача:** модули и элементы контента должны иметь порядок (1, 2, 3…). Преподаватель не должен вручную считать номера — поле заполняется само.

**Почему не обычный `IntegerField`?**  
Можно, но тогда при каждом добавлении модуля нужно вручную искать max(order)+1. `OrderField` делает это в момент `save()`.

Создайте файл `courses/fields.py`:

```python
from django.db import models
from django.core.exceptions import ObjectDoesNotExist


class OrderField(models.PositiveIntegerField):
    def __init__(self, for_fields=None, *args, **kwargs):
        self.for_fields = for_fields
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        if getattr(model_instance, self.attname) is None:
            try:
                qs = self.model.objects.all()
                if self.for_fields:
                    query = {
                        field: getattr(model_instance, field)
                        for field in self.for_fields
                    }
                    qs = qs.filter(**query)
                last_item = qs.latest(self.attname)
                value = last_item.order + 1
            except ObjectDoesNotExist:
                value = 0
            setattr(model_instance, self.attname, value)
            return value
        return super().pre_save(model_instance, add)
```

**Разбор метода `pre_save` — вызывается Django перед записью в БД:**

1. `getattr(model_instance, self.attname) is None` — если order **не задан** (None/пусто):
2. Берём все объекты этой модели (`Module` или `Content`).
3. `for_fields=['course']` — **фильтруем только модули этого курса**. Модуль в курсе A не влияет на порядок в курсе B.
4. `qs.latest('order')` — объект с максимальным order.
5. `value = last_item.order + 1` — следующий номер.
6. Если объектов ещё нет (`ObjectDoesNotExist`) → order = 0 (первый элемент).
7. `setattr(...)` — записываем вычисленное значение в объект.
8. Если order **уже указан** (например drag-and-drop поставил 5) — используем его как есть, `super().pre_save(...)`.

**Пример:** в курсе уже есть модули с order 0 и 1. Создаёте третий без указания order → получит order=2.

### 5.2. Subject, Course, Module

`courses/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.template.loader import render_to_string
from .fields import OrderField


class Subject(models.Model):
    """Предмет / категория: Programming, Math, ..."""
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Course(models.Model):
    """Курс. owner — преподаватель, students — записавшиеся."""
    owner = models.ForeignKey(
        User, related_name='courses_created', on_delete=models.CASCADE)
    subject = models.ForeignKey(
        Subject, related_name='courses', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    overview = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    students = models.ManyToManyField(
        User, related_name='courses_joined', blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.title


class Module(models.Model):
    """Раздел курса: «Введение», «Модели Django», ..."""
    course = models.ForeignKey(
        Course, related_name='modules', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = OrderField(blank=True, for_fields=['course'])

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.order + 1}. {self.title}'
```

**Разбор полей моделей:**


| Поле              | Тип                        | Зачем                                                                  |
| ----------------- | -------------------------- | ---------------------------------------------------------------------- |
| `Subject.title`   | CharField                  | Название категории «Programming»                                       |
| `Subject.slug`    | SlugField, unique          | URL-безопасное имя: `programming` → `/subject/programming/`            |
| `Course.owner`    | ForeignKey → User          | **Кто создал курс.** CMS показывает только `owner=request.user`        |
| `Course.subject`  | ForeignKey → Subject       | К какому предмету относится                                            |
| `Course.slug`     | SlugField, unique          | Человекочитаемый URL: `/course/django-basics/`                         |
| `Course.overview` | TextField                  | Текст на странице **предпросмотра** (до записи)                        |
| `Course.created`  | DateTimeField auto_now_add | Когда создан; сортировка «новые первые»                                |
| `Course.students` | ManyToManyField            | **Кто записан.** Промежуточная таблица Django создаст сама             |
| `Module.course`   | ForeignKey                 | Модуль принадлежит одному курсу                                        |
| `Module.order`    | OrderField                 | Порядок внутри курса                                                   |
| `Meta.ordering`   | —                          | По умолчанию ORM сортирует `Module` по `order`, `Course` по `-created` |
| `__str_`_         | метод                      | Что показывать в admin и shell: `"1. Введение"`                        |


**Как пользоваться связями в коде:**

```python
course = Course.objects.get(pk=1)
course.modules.all()          # все модули курса, уже отсортированы
course.students.all()         # все записанные студенты
user.courses_created.all()    # курсы, где user — преподаватель (related_name)
user.courses_joined.all()     # курсы, куда user записан как студент
```

### 5.3. Полиморфный контент

**Задача:** в одном модуле хранить текст, PDF, видео и тест — **разные таблицы**, но **единый интерфейс** «элементы модуля».

**Почему не одна таблица `Content` с полями text, file, video?**  
Большинство полей были бы пустыми (у текста нет file, у файла нет url). Полиморфизм чище: отдельная таблица на тип + связующая `Content`.

```python
class Content(models.Model):
    module = models.ForeignKey(
        Module, related_name='contents', on_delete=models.CASCADE)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': (
            'text', 'video', 'image', 'file', 'quiz')})
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    order = OrderField(blank=True, for_fields=['module'])

    class Meta:
        ordering = ['order']
```

**Разбор — три части GenericForeignKey:**


| Поле           | Что хранит                                                      | Пример      |
| -------------- | --------------------------------------------------------------- | ----------- |
| `content_type` | **Тип** объекта (строка в таблице django_content_type)          | «это Text»  |
| `object_id`    | **ID** объекта в своей таблице                                  | 12          |
| `item`         | Виртуальное поле — Django сам достаёт `Text.objects.get(pk=12)` | объект Text |


- `limit_choices_to` — в admin нельзя привязать Content к модели User, только к нашим 5 типам.
- `on_delete=CASCADE` — удалили модуль → удалились все Content внутри.

**Жизненный цикл:**

1. Преподаватель создаёт `Text(id=12, title="Введение", content="...")`.
2. Создаётся `Content(module=M1, content_type=Text, object_id=12)`.
3. В шаблоне студента: `{% for content in module.contents.all %}{{ content.item.render }}{% endfor %}`.

### 5.4. Типы контента

**Задача:** общие поля (title, owner, даты) не дублировать в каждой модели — вынести в абстрактный `ItemBase`.

```python
class ItemBase(models.Model):
    owner = models.ForeignKey(
        User, related_name='%(class)s_related', on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def render(self):
        return render_to_string(
            f'courses/content/{self._meta.model_name}.html',
            {'item': self})
```

**Разбор ItemBase:**

- `abstract = True` — **таблица не создаётся**. Это только «шаблон полей» для наследников.
- `related_name='%(class)s_related'` — Django подставит имя класса: у Text будет `text_related`, у File — `file_related`. Иначе конфликт имён.
- `render()` — **единый интерфейс**: шаблон студента не знает тип контента, просто вызывает `item.render`. Метод сам выберет `courses/content/text.html` или `file.html` по имени модели.

**Наследники — только специфичные поля:**

```python
class Text(ItemBase):
    content = models.TextField()      # сам текст лекции

class File(ItemBase):
    file = models.FileField(upload_to='files')   # PDF → media/files/

class Image(ItemBase):
    file = models.FileField(upload_to='images')   # PNG → media/images/

class Video(ItemBase):
    url = models.URLField()             # ссылка YouTube, не файл
```


| Модель | Поле данных | Зачем отдельная модель                      |
| ------ | ----------- | ------------------------------------------- |
| Text   | `content`   | HTML/текст прямо в БД                       |
| File   | `file`      | Бинарный файл на диске                      |
| Image  | `file`      | То же, но другой upload_to и шаблон `<img>` |
| Video  | `url`       | Видео на YouTube — храним только ссылку     |


> Модели Quiz, Question, Answer — раздел 13. Модели прогресса — раздел 12.  
> На этапе 4 достаточно `courses/models.py` (Subject → Video). `students/models.py` — после этапа 11.

---

<a id="section-6"></a>
## 6. Миграции, admin, фикстуры

### 6.1. Миграции

**Задача:** Python-модели → реальные таблицы в PostgreSQL.

**Почему не SQL руками?**  
Django генерирует SQL из моделей. При изменении модели — новая миграция, история в git.

```bash
python manage.py makemigrations courses
python manage.py makemigrations students
python manage.py migrate
```

**Разбор команд:**


| Команда                   | Что делает                                                                  |
| ------------------------- | --------------------------------------------------------------------------- |
| `makemigrations courses`  | Сравнивает models.py с последней миграцией → создаёт файл `0001_initial.py` |
| `makemigrations students` | То же для приложения students                                               |
| `migrate`                 | Применяет **все** неприменённые миграции (включая auth, admin) к PostgreSQL |


```bash
psql -U educa_user -h localhost -p 5432 -d educa -c "\dt"
```

Должны появиться таблицы `courses_course`, `courses_module`, `auth_user`.

### 6.2. Суперпользователь

**Задача:** доступ к `/admin/` для создания Subject и группы Instructors.

```bash
python manage.py createsuperuser
```

Django создаст запись в `auth_user` с `is_superuser=True` — все permissions автоматически.

### 6.3. Admin

**Задача:** удобный UI для Subject и начальной настройки без написания view.

`courses/admin.py`:

```python
from django.contrib import admin
from .models import Subject, Course, Module


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}


class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'created']
    list_filter = ['created', 'subject']
    search_fields = ['title', 'overview']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]
```

**Разбор admin:**


| Настройка                                    | Зачем                                                                 |
| -------------------------------------------- | --------------------------------------------------------------------- |
| `@admin.register(Subject)`                   | Модель появляется в admin без `admin.site.register()`                 |
| `list_display`                               | Какие колонки в списке                                                |
| `prepopulated_fields = {'slug': ('title',)}` | slug автозаполняется из title при вводе                               |
| `ModuleInline`                               | Редактировать модули **на странице курса** — не заходя отдельно       |
| `StackedInline` vs `TabularInline`           | Stacked — поля друг под другом; Tabular — таблица (удобно для Answer) |


### 6.4. Фикстуры — начальные данные

**Задача:** одинаковые Subject (Programming, Math) на всех машинах команды — без ручного ввода в admin.

**Зачем dumpdata/loaddata, а не SQL?**  
Фикстура — JSON через ORM, переносится между SQLite/PostgreSQL, версионируется в git.

```bash
mkdir -p courses/fixtures
python manage.py dumpdata courses.Subject --indent=2 \
    --output=courses/fixtures/subjects.json
```

Загрузка на другой машине:

```bash
python manage.py loaddata subjects
```

<a id="stage-4"></a>
### ✅ Проверка этапа 4 — модели и admin

**Команды:**

```bash
python manage.py makemigrations courses
python manage.py migrate
python manage.py loaddata subjects
python manage.py createsuperuser    # логин: admin
```

> Модели `students` (прогресс, сертификаты) — на этапах 12 и 14. Сейчас мигрируем только `courses`.


| #   | Действие                                                     | Ожидание                                               |
| --- | ------------------------------------------------------------ | ------------------------------------------------------ |
| 1   | `migrate`                                                    | Applying courses.0001_initial … OK                     |
| 2   | [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) | Вход под `admin`                                       |
| 3   | Admin → Subjects                                             | 3 записи (Programming, Mathematics, Music)             |
| 4   | Admin → Groups → создать **Instructors**                     | Группа с правами `courses | course/module/content/...` |
| 5   | Admin → Users → создать `teacher`, добавить в Instructors    | Пользователь готов для CMS                             |
| 6   | `psql ... -c "\dt courses_*"`                                | Таблицы `courses_course`, `courses_module`, …          |


**Подготовка к этапу 6:** войдите как `teacher` на `/accounts/login/` — пока CMS может дать 403, это норм до §8.

---

<a id="section-7"></a>
## 7. Аутентификация и базовые шаблоны

### 7.1. Как Django обрабатывает вход

**Задача:** преподаватели и студенты должны входить на сайт под своим логином.

**Почему не пишем login с нуля?**  
Django уже реализовал: проверку пароля, сессии, CSRF, форму. Мы только подключаем URL и шаблон.

Цепочка:

1. POST `/accounts/login/` с username + password
2. Django ищет User в `auth_user`, проверяет хеш пароля
3. Создаётся запись в `django_session`, браузер получает cookie `sessionid`
4. На каждый следующий запрос middleware подставляет `request.user`
5. В шаблоне: `{% if request.user.is_authenticated %}`

### 7.2. Структура шаблонов

**Задача:** общий каркас страницы (шапка, меню) + отдельные страницы контента.

```text
courses/templates/
  base.html              ← родитель: шапка, CSS, блоки
  registration/
    login.html           ← extends base, только форма входа
    logged_out.html
```

`**courses/templates/base.html` — разбор:**


| Элемент                           | Зачем                                                 |
| --------------------------------- | ----------------------------------------------------- |
| `{% load static %}`               | Подключение CSS через `{% static 'css/base.css' %}`   |
| `{% block title %}`               | Дочерние шаблоны задают свой `<title>`                |
| `{% block content %}`             | Сюда вставляется содержимое login, list, detail...    |
| `request.user.is_authenticated`   | Context processor auth — доступен **везде**           |
| `{% url 'student_course_list' %}` | Именованный URL — не ломается при смене пути          |
| Меню «Преподавание»               | Ссылка на CMS; студент тоже может быть преподавателем |


`**login.html` — разбор:**


| Элемент                                  | Зачем                                                                |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `{% extends "base.html" %}`              | Наследование — не копируем шапку в каждый файл                       |
| `{{ form.as_p }}`                        | Django рисует поля формы LoginView как `<p><label>...`               |
| `{% csrf_token %}`                       | **Обязателен** в каждой POST-форме                                   |
| `<input name="next" value="{{ next }}">` | После входа вернуть на страницу, куда шли (например `/course/mine/`) |
| `form.errors`                            | Показать «неверный пароль» без отдельного view                       |


`**courses/templates/base.html` — каркас сайта:**

```html
{% load static %}
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{% block title %}Educa{% endblock %} — Educa</title>
  <link href="{% static 'css/base.css' %}" rel="stylesheet">
</head>
<body>
  <header id="header" class="site-header">
    <div class="header-inner container">
      <a href="/" class="logo">Edu<span>ca</span></a>
      <ul class="menu nav-menu">
        {% if request.user.is_authenticated %}
          <li><a href="{% url 'student_course_list' %}">Мои курсы</a></li>
          <li><a href="{% url 'student_profile' %}">Профиль</a></li>
          <li><a href="{% url 'manage_course_list' %}">Преподавание</a></li>
          <li><a href="{% url 'logout' %}">Выход</a></li>
        {% else %}
          <li><a href="{% url 'course_list' %}">Каталог</a></li>
          <li><a href="{% url 'login' %}">Вход</a></li>
          <li><a href="{% url 'student_registration' %}">Регистрация</a></li>
        {% endif %}
      </ul>
    </div>
  </header>
  <main id="content" class="site-main">
    <div class="container">{% block content %}{% endblock %}</div>
  </main>
  <footer class="site-footer">
    <div class="container">© Educa — платформа онлайн-курсов</div>
  </footer>
</body>
</html>
```

`**courses/templates/registration/login.html`:**

```html
{% extends "base.html" %}
{% block title %}Вход{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Вход</h1>
</div>
<div class="card form-card">
  {% if form.errors %}<div class="alert alert-error">Неверный логин или пароль.</div>{% endif %}
  <form method="post" action="{% url 'login' %}">
    {{ form.as_p }}
    {% csrf_token %}
    <input type="hidden" name="next" value="{{ next }}" />
    <div class="actions-row">
      <input type="submit" value="Войти" class="button">
      <a href="{% url 'student_registration' %}" class="btn btn-secondary">Регистрация</a>
    </div>
  </form>
</div>
{% endblock %}
```

### 7.3. Дизайн и CSS

**Задача:** единый современный UI для каталога, ЛК студента и CMS.

Файл `courses/static/css/base.css` содержит:


| Класс                            | Назначение                                  |
| -------------------------------- | ------------------------------------------- |
| `.container`                     | Центрированная колонка max-width 1120px     |
| `.layout-sidebar`                | Две колонки: sidebar + контент              |
| `.sidebar` / `.contents`         | Тёмная боковая навигация (модули, предметы) |
| `.card`, `.course-card`          | Карточки курсов и блоков                    |
| `.progress-bar`                  | Полоса прогресса на странице курса          |
| `.button`, `.btn-secondary`      | Кнопки действий                             |
| `.quiz-question`, `.quiz-option` | Оформление викторины                        |
| `.form-card`                     | Формы login/регистрации/CMS                 |


**Паттерн страницы:**

```html
<div class="page-header">
  <h1>Заголовок</h1>
  <p class="page-meta">Подзаголовок</p>
</div>
<div class="card">...</div>
```

Старые классы `.module` и `.course-info` сохранены как алиасы к `.card` — шаблоны из книги продолжают работать.

**Проверка:** [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/) — форма в карточке, тёмная шапка.

<a id="stage-5"></a>
### ✅ Проверка этапа 5 — шаблоны и вход


| #   | Действие                                                                       | Ожидание                                              |
| --- | ------------------------------------------------------------------------------ | ----------------------------------------------------- |
| 1   | [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/) | Форма в `.card`, шапка Educa                          |
| 2   | CSS загружается (не «голый» HTML)                                              | Шрифт Plus Jakarta Sans, синие кнопки                 |
| 3   | Вход под `admin`                                                               | Редирект на `/students/courses/` (пустой список — OK) |
| 4   | Шапка: «Мои курсы», «Профиль», «Преподавание», «Выход»                         | Меню для авторизованного                              |
| 5   | «Выход» → [http://127.0.0.1:8000/](http://127.0.0.1:8000/)                     | Logout, ссылка «Войти снова»                          |


**Не работает CSS?** → Ctrl+F5; проверьте `courses/static/css/base.css` и `{% load static %}`.

---

<a id="section-8"></a>
## 8. CMS для преподавателей

CMS (Content Management System) — интерфейс, где преподаватель создаёт и редактирует курсы **без** admin-панели.

### 8.1. Группа Instructors

1. [http://127.0.0.1:8000/admin/auth/group/add/](http://127.0.0.1:8000/admin/auth/group/add/)
2. Name: `Instructors`
3. Permissions: все из `courses | course`, `courses | module`, `courses | content`, `courses | text`, ... — **кроме** `courses | subject`
4. Создайте пользователя `teacher1`, добавьте в группу Instructors

### 8.2. Примеси (mixins) — зачем они нужны

**Задача:** четыре view (список, создать, редактировать, удалить) должны вести себя одинаково:

- показывать только **свои** курсы (`owner = request.user`);
- требовать **вход** (`LoginRequiredMixin`);
- требовать **разрешение** (`PermissionRequiredMixin`);
- при создании автоматически ставить `owner`.

Без mixins пришлось бы копировать одну и ту же логику в 4 класса.

```python
# courses/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Course


class OwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin, PermissionRequiredMixin):
    model = Course
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    template_name = 'courses/manage/course/form.html'


class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = 'courses/manage/course/list.html'
    permission_required = 'courses.view_course'


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = 'courses.add_course'


class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required = 'courses.change_course'


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    permission_required = 'courses.delete_course'
```

**Разбор каждого класса:**


| Класс                                         | Зачем                                                                                                                                                   |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OwnerMixin.get_queryset`                     | Перехватывает запрос к БД и добавляет `.filter(owner=request.user)`. Преподаватель A не увидит курсы преподавателя B даже если подставит чужой id в URL |
| `OwnerEditMixin.form_valid`                   | Вызывается когда форма валидна, **перед** save. Ставит owner автоматически — преподаватель не может создать курс «от имени» другого                     |
| `LoginRequiredMixin`                          | Если не залогинен → редирект на `/accounts/login/?next=...`                                                                                             |
| `PermissionRequiredMixin`                     | Проверяет Django-permission. Без `courses.add_course` → 403 Forbidden                                                                                   |
| `ListView`                                    | Generic view: сам делает `Course.objects.filter(...)` и передаёт в шаблон как `object_list`                                                             |
| `CreateView` / `UpdateView`                   | Generic view: сам строит ModelForm из `fields`, обрабатывает GET (показать форму) и POST (сохранить)                                                    |
| `DeleteView`                                  | GET — «вы уверены?», POST — удалить                                                                                                                     |
| `reverse_lazy('manage_course_list')`          | Куда редирект после успеха. `lazy` — потому что urls ещё могут не быть загружены при импорте                                                            |
| `permission_required = 'courses.view_course'` | Строка формата `app_label.codename`. Django создаёт их автоматически для каждой модели                                                                  |


### 8.3. URL CMS — `courses/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    path('mine/', views.ManageCourseListView.as_view(), name='manage_course_list'),
    path('create/', views.CourseCreateView.as_view(), name='course_create'),
    path('<pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('<pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('<pk>/modules/', views.CourseModuleUpdateView.as_view(), name='course_module_update'),
    path('module/<module_id>/content/<model_name>/',
         views.ContentCreateUpdateView.as_view(), name='module_content_create'),
    path('module/<module_id>/content/<model_name>/<id>/',
         views.ContentCreateUpdateView.as_view(), name='module_content_update'),
    path('module/order/', views.ModuleOrderView.as_view(), name='module_order'),
    path('content/order/', views.ContentOrderView.as_view(), name='content_order'),
]
```

### 8.4. Шаблон списка курсов преподавателя

`courses/templates/courses/manage/course/list.html`:

```html
{% extends "base.html" %}
{% block title %}Мои курсы{% endblock %}
{% block content %}
<h1>Мои курсы (преподавание)</h1>
<div class="module">
  {% for course in object_list %}
  <div class="course-info">
    <h3>{{ course.title }}</h3>
    <p>
      <a href="{% url 'course_edit' course.id %}">Редактировать</a>
      <a href="{% url 'course_module_update' course.id %}">Модули</a>
      <a href="{% url 'course_delete' course.id %}">Удалить</a>
    </p>
  </div>
  {% empty %}
  <p>Вы ещё не создали ни одного курса.</p>
  {% endfor %}
  <p><a href="{% url 'course_create' %}" class="button">Создать курс</a></p>
</div>
{% endblock %}
```

**Проверка:** войдите как `teacher1` → [http://127.0.0.1:8000/course/mine/](http://127.0.0.1:8000/course/mine/)

<a id="stage-6"></a>
### ✅ Проверка этапа 6 — CMS курсы

**Подготовка:** пользователь `teacher` в группе Instructors (этап 4).


| #   | Действие                                                                 | Ожидание                              |
| --- | ------------------------------------------------------------------------ | ------------------------------------- |
| 1   | Вход как `teacher`                                                       | Успешный login                        |
| 2   | [http://127.0.0.1:8000/course/mine/](http://127.0.0.1:8000/course/mine/) | «Преподавание», кнопка «Создать курс» |
| 3   | «Создать курс» → заполнить subject, title, slug, overview                | Редирект на список                    |
| 4   | Курс в списке с кнопками Редактировать / Модули / Удалить                | CRUD виден                            |
| 5   | Студент `student` на `/course/mine/`                                     | **403 Forbidden** (нет прав)          |


**Тестовые данные для следующих этапов:**

```text
Курс: «Python Basics», slug: python-basics, subject: Programming
```

### 8.5. Редактирование модулей (formset)

**Задача:** на одной странице редактировать сразу несколько модулей курса — добавить, изменить название, удалить.

**Почему не отдельная форма на каждый модуль?**  
Преподавателю неудобно: 5 модулей = 5 страниц. **Formset** — стандартный Django-механизм «N форм одной модели на одной странице».

`courses/forms.py`:

```python
from django.forms.models import inlineformset_factory
from .models import Course, Module

ModuleFormSet = inlineformset_factory(
    Course,
    Module,
    fields=['title', 'description'],
    extra=2,
    can_delete=True,
)
```

**Разбор параметров `inlineformset_factory`:**


| Параметр          | Зачем                                                                 |
| ----------------- | --------------------------------------------------------------------- |
| `Course, Module`  | Parent → Child. Formset знает: Module всегда привязан к одному Course |
| `fields=[...]`    | Какие поля Module показывать в каждой форме                           |
| `extra=2`         | Сколько **пустых** форм для новых модулей нарисовать                  |
| `can_delete=True` | Галочка «Delete» — при save() Django удалит отмеченные модули         |


`courses/views.py` — view **не наследует CreateView**, потому что formset — не одна форма:

```python
from django.shortcuts import redirect, get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from .forms import ModuleFormSet


class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'

    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, pk=pk, owner=request.user)
        return super().dispatch(request, pk)

    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)

    def get(self, request, pk):
        formset = self.get_formset()
        return self.render_to_response({'course': self.course, 'formset': formset})

    def post(self, request, pk):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({'course': self.course, 'formset': formset})
```

**Разбор методов view:**


| Метод                    | Когда вызывается             | Что делает                                                                                    |
| ------------------------ | ---------------------------- | --------------------------------------------------------------------------------------------- |
| `dispatch`               | Любой запрос (GET/POST)      | **До всего остального.** Достаёт курс и проверяет `owner=request.user`. Если чужой курс → 404 |
| `get_formset(data=None)` | Внутренний helper            | `data=None` → пустые/существующие формы. `data=request.POST` → заполненные пользователем      |
| `get`                    | Пользователь открыл страницу | Показать formset                                                                              |
| `post`                   | Нажал «Сохранить»            | Валидация всех форм сразу → `formset.save()` создаёт/обновляет/удаляет модули                 |


`courses/templates/courses/manage/module/formset.html`:

```html
{% extends "base.html" %}
{% block title %}Модули — {{ course.title }}{% endblock %}
{% block content %}
<h1>Модули курса «{{ course.title }}»</h1>
<div class="module">
  <form method="post">
    {{ formset }}
    {{ formset.management_form }}
    {% csrf_token %}
    <input type="submit" value="Сохранить модули">
  </form>
</div>
{% endblock %}
```

**Разбор шаблона:**

- `{{ formset }}` — все формы модулей (Django рисует их автоматически).
- `{{ formset.management_form }}` — **обязательно!** Скрытые поля: сколько форм, сколько новых, сколько удалить. Без них POST не разберётся.
- `{% csrf_token %}` — защита от подделки запроса. Django отклонит POST без токена.

### 8.6. Добавление контента в модуль

**Задача:** один view создаёт/редактирует Text, File, Image, Video, Quiz — не пять отдельных view.

**Идея:** в URL передаём `model_name=text|file|...`, view динамически находит модель и строит форму через `modelform_factory`.

```python
from django.forms.models import modelform_factory
from django.apps import apps
from .models import Module, Content


class ContentCreateUpdateView(TemplateResponseMixin, View):
    template_name = 'courses/manage/content/form.html'
    module = None
    model = None
    obj = None

    def get_model(self, model_name):
        allowed = ['text', 'video', 'image', 'file', 'quiz']
        if model_name in allowed:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(model, exclude=['owner', 'created', 'updated'])
        return Form(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(
            Module, pk=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)
        if id:
            self.obj = get_object_or_404(self.model, pk=id, owner=request.user)
        return super().dispatch(request, module_id, model_name, id)

    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({
            'form': form, 'object': self.obj, 'module': self.module})

    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj,
                             data=request.POST, files=request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                Content.objects.create(module=self.module, item=obj)
            if model_name == 'quiz':
                return redirect('quiz_manage', module_id=self.module.id, quiz_id=obj.id)
            return redirect('course_module_update', pk=self.module.course.id)
        return self.render_to_response({
            'form': form, 'object': self.obj, 'module': self.module})
```

**Разбор ключевых моментов:**


| Строка                                          | Зачем                                                                                     |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `get_model(model_name)`                         | Белый список типов — нельзя подставить `model_name=user` и получить доступ к чужим данным |
| `modelform_factory(..., exclude=[...])`         | Форма **автоматически** включает все поля модели (content, file, url), кроме служебных    |
| `course__owner=request.user`                    | Двойная проверка: модуль принадлежит курсу, курс — текущему преподавателю                 |
| `id=None` vs `id=5`                             | Без id — **создание**, с id — **редактирование** существующего Text/File/...              |
| `save(commit=False)`                            | Сначала сохраняем объект без БД, ставим owner, потом `save()`                             |
| `if not id: Content.objects.create(...)`        | При **создании** связать объект с модулем. При редактировании связь уже есть              |
| `if model_name == 'quiz': redirect quiz_manage` | После создания викторины сразу открыть страницу **вопросов**                              |
| `files=request.FILES`                           | **Обязательно** для FileField/ImageField                                                  |


**Как преподаватель добавляет PDF:**

1. `/course/mine/` → «Модули» → создал «Модуль 1»
2. URL `/course/module/5/content/file/` → форма с title + file
3. POST → создаётся `File` + `Content(module=5, item=file)`

### 8.7. CMS викторин — вопросы и ответы на сайте

**Задача:** преподаватель создаёт викторину и **вопросы** без Django Admin.

**Цепочка:**

1. CMS → модуль → «Викторина» → title, description, pass_percent
2. Редирект на `/course/module/<id>/content/quiz/<quiz_id>/questions/`
3. «Добавить вопрос» → текст + formset вариантов ответов (отметить `is_correct`)

**Formset в `courses/forms.py`:**

```python
AnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    fields=['text', 'is_correct'],
    extra=3,
    can_delete=True,
)
```

**URL в `courses/urls.py`:**

```python
path('module/<int:module_id>/content/quiz/<int:quiz_id>/questions/',
     views.QuizManageView.as_view(), name='quiz_manage'),
path('module/<int:module_id>/content/quiz/<int:quiz_id>/questions/create/',
     views.QuestionCreateUpdateView.as_view(), name='question_create'),
path('module/<int:module_id>/content/quiz/<int:quiz_id>/questions/<int:question_id>/',
     views.QuestionCreateUpdateView.as_view(), name='question_update'),
path('module/<int:module_id>/content/quiz/<int:quiz_id>/questions/<int:question_id>/delete/',
     views.QuestionDeleteView.as_view(), name='question_delete'),
```

**Views (сокращённо):**

```python
def _get_quiz_in_module(request, module_id, quiz_id):
    module = get_object_or_404(Module, pk=module_id, course__owner=request.user)
    quiz = get_object_or_404(Quiz, pk=quiz_id, owner=request.user)
    get_object_or_404(Content, module=module, content_type__model='quiz', object_id=quiz.id)
    return module, quiz


class QuizManageView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/quiz/manage.html'
    # GET: список вопросов + ответов


class QuestionCreateUpdateView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/quiz/question_form.html'
    # GET/POST: Question + AnswerFormSet
    # POST: сначала save question, потом formset с instance=question


class QuestionDeleteView(LoginRequiredMixin, View):
    def post(self, request, module_id, quiz_id, question_id):
        # POST-only удаление вопроса
```

**Разбор безопасности `_get_quiz_in_module`:**


| Проверка                       | Зачем                                                            |
| ------------------------------ | ---------------------------------------------------------------- |
| `course__owner=request.user`   | Чужой модуль → 404                                               |
| `Quiz.owner=request.user`      | Чужая викторина → 404                                            |
| `Content` с quiz в этом module | Нельзя редактировать quiz из другого модуля по подставленному id |


**Шаблон `formset.html` — ссылка «Вопросы» у quiz-контента:**

```html
{% if content.content_type.model == 'quiz' %}
| <a href="{% url 'quiz_manage' module.id content.object_id %}">Вопросы</a>
{% endif %}
```

Admin для Quiz (раздел 13.2) остаётся **опциональным** — для быстрой правки через `/admin/`.

<a id="stage-7"></a>
### ✅ Проверка этапа 7 — модули и контент


| #   | Действие                                     | Ожидание                            |
| --- | -------------------------------------------- | ----------------------------------- |
| 1   | `/course/mine/` → «Модули» у курса           | Formset с полями title, description |
| 2   | Добавить 2 модуля, «Сохранить модули»        | Модули в списке ниже                |
| 3   | Chip «Текст» → title + content → Сохранить   | Контент в списке модуля             |
| 4   | Chip «Файл» / «Изображение» → загрузить файл | Файл в `media/`                     |
| 5   | Chip «Видео» → URL YouTube                   | Контент типа video                  |
| 6   | «Изменить» у контента                        | Форма редактирования открывается    |


**Пока не проверяем:** викторину (этап 8), каталог для студента (этап 9).

### 8.8. Drag-and-drop сортировка (опционально)

Для переупорядочивания модулей и контента — JavaScript-библиотека [html5sortable](https://github.com/lukasoppermann/html5sortable) + AJAX POST на `module_order` / `content_order`. Подробная реализация — в [Chapter 13 репозитория](https://github.com/PacktPublishing/Django-4-by-Example/tree/main/Chapter13). Для сдачи достаточно ручного поля `order` или formset.

<a id="stage-8"></a>
### ✅ Проверка этапа 8 — CMS викторин

**Перед проверкой:** добавьте в `courses/models.py` модели `Quiz`, `Question`, `Answer`, `QuizResult` (§13.1), затем `makemigrations courses && migrate`.


| #   | Действие                                                  | Ожидание                                             |
| --- | --------------------------------------------------------- | ---------------------------------------------------- |
| 1   | Chip «Викторина» → title, pass_percent=70                 | Редирект на `/course/module/.../quiz/.../questions/` |
| 2   | «Добавить вопрос» → текст + 2–3 ответа, один `is_correct` | Вопрос в списке                                      |
| 3   | В списке модулей ссылка «Вопросы» у quiz                  | Открывает quiz manage                                |
| 4   | «Изменить» вопрос → сохранить                             | Ответы обновлены                                     |
| 5   | Admin → Quiz (опционально)                                | Те же данные видны                                   |


**Тестовые данные:** викторина «Module 1 Quiz», 2 вопроса, porог 70%.

---

<a id="section-9"></a>
## 9. Публичный каталог курсов

### 9.1. CourseListView — главная страница `/`

**Задача:** публичный каталог — любой посетитель видит курсы, может фильтровать по предмету.

**Почему отдельный `public_urls.py`?**  
URL главной `/` без префикса. CMS живёт под `/course/`. Разделение файлов — чище, чем смешивать в одном urls.py.

`courses/public_urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.CourseListView.as_view(), name='course_list'),
    path('subject/<slug:subject>/', views.CourseListView.as_view(),
         name='course_list_subject'),
    path('course/<slug:slug>/', views.CourseDetailView.as_view(),
         name='course_detail'),
]
```

**Разбор URL:**


| path                      | Зачем                                                    |
| ------------------------- | -------------------------------------------------------- |
| `''`                      | Главная `/` — список всех курсов                         |
| `subject/<slug:subject>/` | Тот же view, но в URL имя предмета — фильтрация          |
| `course/<slug:slug>/`     | Предпросмотр одного курса по slug (не pk — красивые URL) |


`courses/views.py`:

```python
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from .models import Subject, Course


class CourseListView(TemplateResponseMixin, View):
    template_name = 'courses/course/list.html'

    def get(self, request, subject=None):
        subjects = Subject.objects.annotate(
            total_courses=Count('courses'))
        courses = Course.objects.annotate(
            total_modules=Count('modules'))
        current_subject = None
        if subject:
            current_subject = get_object_or_404(Subject, slug=subject)
            courses = courses.filter(subject=current_subject)
        return self.render_to_response({
            'subjects': subjects,
            'subject': current_subject,
            'courses': courses,
        })


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.forms import CourseEnrollForm
        context['enroll_form'] = CourseEnrollForm(
            initial={'course': self.object})
        return context
```

**Разбор CourseListView и CourseDetailView:**


| View / строка                             | Зачем                                                                        |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| `CourseListView` + `annotate(Count(...))` | Один SQL-запрос для счётчиков — без N+1                                      |
| `CourseDetailView` + slug                 | Красивый URL `/course/django-basics/`; объект в шаблоне как `object`         |
| `get_context_data` + `enroll_form`        | DetailView не знает про зачисление — добавляем форму для кнопки «Записаться» |
| `initial={'course': self.object}`         | Hidden field получит id текущего курса                                       |


### 9.2. Шаблон каталога

`courses/templates/courses/course/list.html` — sidebar предметов + сетка карточек `.course-card`:

```html
{% extends "base.html" %}
{% block content %}
<div class="page-header">
  <h1>{% if subject %}{{ subject.title }}{% else %}Каталог курсов{% endif %}</h1>
</div>
<div class="layout-sidebar">
  <aside class="contents sidebar">...</aside>
  <section>
    <div class="card-grid">
      {% for course in courses %}
      <article class="course-card">...</article>
      {% endfor %}
    </div>
  </section>
</div>
{% endblock %}
```

Полный код — в репозитории `courses/templates/courses/course/list.html`.

### 9.3. Страница предпросмотра + запись

`courses/templates/courses/course/detail.html`:

```html
{% extends "base.html" %}
{% block title %}{{ object.title }}{% endblock %}
{% block content %}
<h1>{{ object.title }}</h1>
<div class="module">
  <h2>Описание</h2>
  <p>
    Предмет: <a href="{% url 'course_list_subject' object.subject.slug %}">
      {{ object.subject.title }}</a>.
    Модулей: {{ object.modules.count }}.
    Преподаватель: {{ object.owner.get_full_name|default:object.owner.username }}
  </p>
  {{ object.overview|linebreaks }}

  {% if request.user.is_authenticated %}
    <form action="{% url 'student_enroll_course' %}" method="post">
      {{ enroll_form }}
      {% csrf_token %}
      <input type="submit" value="Записаться на курс" class="button">
    </form>
  {% else %}
    <a href="{% url 'student_registration' %}" class="button">
      Зарегистрироваться, чтобы записаться
    </a>
  {% endif %}
</div>
{% endblock %}
```

**Проверка:** откройте `/` → кликните на курс → видите описание и кнопку записи.

<a id="stage-9"></a>
### ✅ Проверка этапа 9 — каталог


| #   | Действие                                                 | Ожидание                                             |
| --- | -------------------------------------------------------- | ---------------------------------------------------- |
| 1   | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (гость) | Каталог, sidebar предметов, карточка «Python Basics» |
| 2   | Фильтр по subject (Programming)                          | Только курсы этого предмета                          |
| 3   | Клик на курс → `/course/python-basics/`                  | Overview, кнопка «Записаться» / «Зарегистрироваться» |
| 4   | Гость видит курс                                         | Контент модулей **не** виден (только overview)       |
| 5   | `teacher` на `/`                                         | Тот же каталог — CMS отдельно в «Преподавание»       |


---

<a id="section-10"></a>
## 10. Регистрация и зачисление студентов

### 10.1. Форма зачисления

**Задача:** на странице предпросмотра курса — одна кнопка «Записаться». Студент не выбирает курс из списка (он уже на странице этого курса), но нам нужно **передать id курса** на сервер при POST.

**Решение:** скрытое поле `HiddenInput` — в HTML есть `<input type="hidden" name="course" value="3">`, пользователь видит только кнопку.

`students/forms.py`:

```python
from django import forms
from courses.models import Course


class CourseEnrollForm(forms.Form):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=forms.HiddenInput)
```

**Разбор:**

- `forms.Form` — **не ModelForm**, потому что мы не создаём новую модель, а добавляем связь many-to-many.
- `ModelChoiceField` — Django проверит, что переданный id **существует** в таблице Course (защита от подделки).
- `HiddenInput` — поле не рисуется на экране.

### 10.2. Регистрация

**Задача:** гость создаёт аккаунт и **сразу** попадает в систему (без повторного ввода пароля).

`students/views.py`:

```python
class StudentRegistrationView(CreateView):
    template_name = 'students/student/registration.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('student_course_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        cd = form.cleaned_data
        user = authenticate(username=cd['username'], password=cd['password1'])
        login(self.request, user)
        return response
```

**Разбор `form_valid` — вызывается когда форма прошла валидацию:**

1. `super().form_valid(form)` — `CreateView` **создаёт User в БД** (хеширует пароль).
2. `authenticate(...)` — Django проверяет логин/пароль (как при обычном входе).
3. `login(self.request, user)` — создаёт **сессию**, пользователь считается залогиненным.
4. Редирект на `success_url` = `/students/courses/`.

**Почему не просто `login` без `authenticate`?**  
`authenticate` — стандартный безопасный путь: убеждаемся, что пароль действительно подошёл к только что созданному пользователю.

`UserCreationForm` — **встроенная** форма Django: username, password1, password2 с проверкой совпадения и сложности.

### 10.3. Зачисление на курс

**Задача:** залогиненный студент нажимает «Записаться» → попадает в `course.students`.

```python
class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    form_class = CourseEnrollForm

    def form_valid(self, form):
        self.course = form.cleaned_data['course']
        self.course.students.add(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('student_course_detail', args=[self.course.id])
```

**Разбор:**


| Часть                         | Зачем                                                                                              |
| ----------------------------- | -------------------------------------------------------------------------------------------------- |
| `LoginRequiredMixin`          | Гость не может записаться через POST напрямую — сначала login                                      |
| `FormView`                    | Generic view для обычной Form (не ModelForm): GET не нужен, только POST с кнопки                   |
| `form.cleaned_data['course']` | Объект Course после валидации (id проверен)                                                        |
| `course.students.add(user)`   | Django INSERT в промежуточную таблицу `courses_course_students`. Повторный add не создаст дубликат |
| `get_success_url()`           | Динамический редирект — сразу на страницу материалов **этого** курса                               |


### 10.4. Главная страница студента — активные курсы

**Задача из ТЗ:** «главная страница со списком **активных** курсов пользователя». Активный = на который **записан**.

```python
class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'students/course/list.html'

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)
```

**Разбор:**

- `LoginRequiredMixin` — страница только для залогиненных.
- `ListView` — автоматически вызывает queryset и кладёт результат в шаблон как `object_list`.
- `.filter(students=self.request.user)` — **ключевая строка**: SQL `JOIN` через many-to-many, только курсы где текущий user в списке students.
- Без этого фильтра студент увидел бы все курсы платформы — нарушение ТЗ.

`students/templates/students/course/list.html`:

```html
{% extends "base.html" %}
{% load course_tags %}
{% block title %}Мои курсы{% endblock %}
{% block content %}
<h1>Мои курсы</h1>
<div class="module">
  {% for course in object_list %}
  <div class="course-info">
    <h3>{{ course.title }}</h3>
    <p>Прогресс: {{ course|course_progress:request.user }}%</p>
    <p><a href="{% url 'student_course_detail' course.id %}">Перейти к материалам</a></p>
  </div>
  {% empty %}
  <p>Вы не записаны ни на один курс.
    <a href="{% url 'course_list' %}">Посмотреть каталог</a>
  </p>
  {% endfor %}
</div>
{% endblock %}
```

### 10.5. URL студентов — `students/urls.py`

**Задача:** все маршруты студента под префиксом `/students/`.

**Разбор каждого path:**


| URL                               | name                         | Зачем                                                                         |
| --------------------------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| `register/`                       | student_registration         | Создание аккаунта                                                             |
| `enroll-course/`                  | student_enroll_course        | POST с hidden course id — **не** RESTful id в URL, потому что id в теле формы |
| `courses/`                        | student_course_list          | **Главная ЛК** — активные курсы                                               |
| `course/<pk>/`                    | student_course_detail        | Материалы, первый модуль                                                      |
| `course/<pk>/module/<module_id>/` | student_course_detail_module | Тот же view, другой module в контексте                                        |
| `.../complete/`                   | module_complete              | POST-only: отметить прогресс                                                  |
| `.../quiz/<quiz_id>/`             | quiz_take                    | GET — форма, POST — проверка ответов                                          |
| `.../result/`                     | quiz_result                  | Показ score после POST викторины                                              |
| `certificate/<uuid:code>/`        | certificate_detail           | UUID — не угадаешь чужой сертификат                                           |
| `profile/`                        | student_profile              | Список сертификатов и badges                                                  |


`<int:pk>` — Django проверит, что pk — число. `<uuid:code>` — только валидный UUID.

<a id="stage-10"></a>
### ✅ Проверка этапа 10 — регистрация и запись


| #   | Действие                                                                             | Ожидание                             |
| --- | ------------------------------------------------------------------------------------ | ------------------------------------ |
| 1   | [http://127.0.0.1:8000/students/register/](http://127.0.0.1:8000/students/register/) | Форма UserCreationForm               |
| 2   | Создать `student` / пароль                                                           | Автовход → `/students/courses/`      |
| 3   | `/students/courses/`                                                                 | Пусто + ссылка на каталог            |
| 4   | `/course/python-basics/` → «Записаться»                                              | Редирект на `/students/course/<id>/` |
| 5   | `/students/courses/`                                                                 | Курс в списке, прогресс 0%           |
| 6   | Повторная запись на тот же курс                                                      | Без дубликата (M2M)                  |


**Два браузера / режим инкогнito:** `teacher` и `student` одновременно — удобно для проверки.

---

<a id="section-11"></a>
## 11. Просмотр содержимого курса

### 11.1. StudentCourseDetailView

**Задача:** студент читает материалы курса — модули слева, контент справа. Доступ **только** если записан.

```python
class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'students/course/detail.html'

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        module_id = self.kwargs.get('module_id')
        if module_id:
            context['module'] = course.modules.get(pk=module_id)
        else:
            context['module'] = course.modules.first()
        from .services import get_course_progress
        context['progress'] = get_course_progress(self.request.user, course)
        return context
```

**Разбор:**


| Метод / строка                        | Зачем                                                                                     |
| ------------------------------------- | ----------------------------------------------------------------------------------------- |
| `get_queryset().filter(students=...)` | Если студент не записан — объект Course не найдётся → **404**. Нельзя подставить чужой pk |
| `self.object`                         | DetailView положил сюда один Course после queryset                                        |
| `module_id` из URL                    | `/course/3/module/12/` → показать модуль 12. Без module_id — первый модуль                |
| `course.modules.get(pk=module_id)`    | `.get()` — ошибка если модуль не из этого курса (защита от подмены id)                    |
| `get_context_data`                    | DetailView передаёт в шаблон только `object`. Мы **добавляем** `module` и `progress`      |


### 11.2. Шаблон — модули + контент

**Задача:** навигация по модулям + вывод полиморфного контента + кнопка «пройдено».

`students/templates/students/course/detail.html` — **разбор тегов:**


| Тег / конструкция                                         | Зачем                                                                 |
| --------------------------------------------------------- | --------------------------------------------------------------------- |
| `{% load course_tags %}`                                  | Подключаем фильтры `course_progress`, `module_completed`              |
| `{% for m in object.modules.all %}`                       | `object` = Course; `modules` — related_name из ForeignKey             |
| `{% url 'student_course_detail_module' object.id m.id %}` | Ссылка на тот же view, но с module_id в URL                           |
| `{{ m.order|add:1 }}`                                     | order хранится с 0, пользователю показываем «Модуль 1»                |
| `{% if m|module_completed:request.user %} ✓`              | Галочка у пройденных модулей                                          |
| `{% for content in module.contents.all %}`                | Content-обёртки в порядке order                                       |
| `{% with item=content.item %}`                            | GenericForeignKey → реальный Text/File/Quiz                           |
| `{{ item.render|safe }}`                                  | `render()` возвращает HTML-строку; `safe` — Django не экранирует теги |
| `{% if content.content_type.model == 'quiz' %}`           | Для викторины лучше ссылка, а не render (нужен URL с course id)       |
| `<form method="post">` + `module_complete`                | POST — потому что **меняем данные** (прогресс). GET для этого нельзя  |


| `{% if m == module %}class="selected"` | **Пробелы обязательны:** `m == module`, не `m==module` — иначе TemplateSyntaxError |
| `style="width: {{ progress }}%"` | Progress bar в `.page-header` |
| `{% if content.content_type.model == 'quiz' %}` | Ссылка «Пройти тест», не `item.render` |
| `.content-block` | Обёртка каждого элемента контента |

```html
{% extends "base.html" %}
{% load course_tags %}
{% block content %}
<div class="page-header">
  <h1>{{ object.title }}</h1>
  <div class="progress-wrap">
    <div class="progress-label"><span>Общий прогресс</span><span>{{ progress }}%</span></div>
    <div class="progress-bar">
      <div class="progress-bar-fill" style="width: {{ progress }}%"></div>
    </div>
  </div>
</div>

<div class="layout-sidebar">
  <aside class="contents sidebar">
    <ul class="sidebar-list">
      {% for m in object.modules.all %}
      <li{% if m == module %} class="selected"{% endif %}>
        <a href="{% url 'student_course_detail_module' object.id m.id %}">
          {{ m.order|add:1 }}. {{ m.title }}
          {% if m|module_completed:request.user %}<span class="sidebar-badge">✓</span>{% endif %}
        </a>
      </li>
      {% endfor %}
    </ul>
  </aside>

  {% if module %}
  <section class="card">
    {% for content in module.contents.all %}
    {% with item=content.item %}
    {% if item %}
    <div class="content-block{% if content.content_type.model == 'quiz' %} content-block--quiz{% endif %}">
      <h3>{{ item.title }}</h3>
      {% if content.content_type.model == 'quiz' %}
        <a href="{% url 'quiz_take' object.id content.object_id %}" class="button">Пройти тест</a>
      {% else %}
        {{ item.render|safe }}
      {% endif %}
    </div>
    {% endif %}
    {% endwith %}
    {% endfor %}
    <form action="{% url 'module_complete' object.id module.id %}" method="post" class="actions-row">
      {% csrf_token %}
      <input type="submit" value="Отметить модуль пройденным" class="button">
    </form>
  </section>
  {% endif %}
</div>
{% endblock %}
```

### 11.3. Шаблоны отображения контента

`courses/templates/courses/content/text.html`:

```html
{{ item.content|linebreaks }}
```

`courses/templates/courses/content/file.html`:

```html
<p><a href="{{ item.file.url }}" class="button" download>Скачать файл</a></p>
```

`courses/templates/courses/content/image.html`:

```html
<p><img src="{{ item.file.url }}" alt="{{ item.title }}"></p>
```

`courses/templates/courses/content/video.html`:

```html
{% load embed_video_tags %}
{% video item.url '640x360' %}
```

<a id="stage-11"></a>
### ✅ Проверка этапа 11 — материалы курса


| #   | Действие                                            | Ожидание                                        |
| --- | --------------------------------------------------- | ----------------------------------------------- |
| 1   | Вход как `student`, `/students/course/<id>/`        | Sidebar модулей + progress bar                  |
| 2   | Клик по модулю 2                                    | URL `/students/course/<id>/module/<mid>/`       |
| 3   | Текстовый контент                                   | Отображается через `item.render`                |
| 4   | Файл / изображение / видео                          | Скачивание, `<img>`, embed                      |
| 5   | Викторина                                           | Кнопка «Пройти тест» (ещё без логики — этап 13) |
| 6   | Студент **не** записан на курс, подставить чужой id | **404**                                         |


---

<a id="section-12"></a>
## 12. Отслеживание прогресса

### 12.1. Логика

**Задача из ТЗ:** «отслеживание прогресса». В базовом Educa есть только зачисление — мы добавляем **явный учёт**.

**Формула:** прогресс = (пройденные модули / всего модулей) × 100%.

Пример: 4 модуля, студент нажал «Модуль пройден» дважды → 50%.

**Почему отдельные модели, а не поле в Course?**  
Прогресс **индивидуален** для каждого студента. 100 студентов на одном курсе — 100 разных прогрессов.

### 12.2. Модели — `students/models.py`

```python
class ModuleProgress(models.Model):
    user = models.ForeignKey(User, related_name='module_progress', ...)
    module = models.ForeignKey(Module, related_name='student_progress', ...)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'module'], name='unique_user_module_progress')
        ]
```

**Разбор:**


| Поле                             | Зачем                                                                       |
| -------------------------------- | --------------------------------------------------------------------------- |
| `user` + `module`                | Одна запись = «этот студент прошёл этот модуль»                             |
| `completed`                      | False → ещё не нажал кнопку; True → прошёл                                  |
| `completed_at`                   | Когда именно отметил (для отчётов, сертификата)                             |
| `UniqueConstraint(user, module)` | **Один прогресс на пару.** Без этого повторное нажатие создало бы дубликаты |


`CourseProgress` — то же для **всего курса** (completed=True когда 100% модулей).

### 12.3. Сервисный слой — `students/services.py`

**Задача:** логика прогресса в одном месте. View остаются тонкими, шаблоны не лезут в БД.

**Почему не методы на модели `Course`?**  
`Course` в приложении `courses`, а `ModuleProgress` — в `students`. Импорт `Course` → `students` → `courses` дал бы **циклический импорт**. Сервис в `students/services.py` импортирует Course — это нормально (односторонняя зависимость).

```python
def get_course_progress(user, course):
    total = course.modules.count()
    if total == 0:
        return 0
    done = ModuleProgress.objects.filter(
        user=user, module__course=course, completed=True).count()
    return int(done / total * 100)
```

**Разбор:**

- `module__course=course` — lookup через ForeignKey: «модули, принадлежащие этому курсу».
- `if total == 0: return 0` — защита от деления на ноль (курс без модулей).

```python
def mark_module_complete(user, module):
    progress, _ = ModuleProgress.objects.get_or_create(user=user, module=module)
    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

    course = module.course
    if get_course_progress(user, course) == 100:
        cp, _ = CourseProgress.objects.get_or_create(user=user, course=course)
        if not cp.completed:
            cp.completed = True
            cp.completed_at = timezone.now()
            cp.save()
            on_course_completed(user, course)


def is_module_completed(user, module):
    return ModuleProgress.objects.filter(
        user=user, module=module, completed=True).exists()


def issue_certificate(user, course):
    return Certificate.objects.get_or_create(user=user, course=course)


def award_course_badges(user, course):
    for badge in Badge.objects.filter(course=course):
        UserBadge.objects.get_or_create(user=user, badge=badge)


def on_course_completed(user, course):
    issue_certificate(user, course)
    award_course_badges(user, course)
```

**Разбор `mark_module_complete` (продолжение):**

- `if get_course_progress(...) == 100` — все модули отмечены.
- `CourseProgress` — фиксируем факт завершения **курса целиком** (один раз).
- `on_course_completed` — сертификат + badges. Вызывается только при первом достижении 100%.

### 12.4. Шаблонные теги — `students/templatetags/course_tags.py`

**Задача:** в шаблоне писать `{{ course|course_progress:user }}`, а не вызывать Python из HTML.

**Почему filter, а не функция в view?**  
Filter переиспользуется в `list.html` и `detail.html` без дублирования кода в каждом view.

```python
from django import template
from students.services import get_course_progress, is_module_completed

register = template.Library()


@register.filter
def course_progress(course, user):
    return get_course_progress(user, course)


@register.filter
def module_completed(module, user):
    return is_module_completed(user, module)
```

**Разбор:**

- `register = template.Library()` — регистрация тегов Django.
- `@register.filter` — синтаксис `value|filter:arg` → `course_progress(course, user)`.
- Логика **только** в `services.py` — filter тонкий, тестируемый.

Не забудьте пустой `students/templatetags/__init__.py` — без него Python не видит пакет.

### 12.5. View «модуль пройден»

**Задача:** кнопка «Отметить модуль пройденным» → POST → обновить прогресс.

**Почему отдельный View, а не GET-ссылка?**  
Изменение данных (запись в БД) по стандартам HTTP — только **POST**. GET-ссылка опасна: поисковик или prefetch мог бы «пройти» модуль без намерения пользователя.

```python
class ModuleCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk, module_id):
        course = get_object_or_404(Course, pk=pk, students=request.user)
        module = get_object_or_404(Module, pk=module_id, course=course)
        mark_module_complete(request.user, module)
        return redirect('student_course_detail_module', pk, module_id)
```

**Разбор:**


| Строка                                               | Зачем                                                 |
| ---------------------------------------------------- | ----------------------------------------------------- |
| `students=request.user`                              | Только записанный студент                             |
| `module__course=course` (в get_object_or_404 Module) | Модуль 99 не относится к курсу 3 → 404                |
| Только `def post`                                    | GET на этот URL ничего не делает (можно добавить 405) |
| `redirect(...)`                                      | Обратно на страницу модуля — студент видит галочку ✓  |


<a id="stage-12"></a>
### ✅ Проверка этапа 12 — прогресс

**Перед проверкой:** выполните `makemigrations students` + `migrate` (модели ModuleProgress, CourseProgress).


| #   | Действие                                                                | Ожидание                                       |
| --- | ----------------------------------------------------------------------- | ---------------------------------------------- |
| 1   | `/students/courses/`                                                    | Progress bar у каждого курса                   |
| 2   | `/students/course/<id>/`                                                | «Общий прогресс: 0%» (если ничего не пройдено) |
| 3   | «Отметить модуль пройденным»                                            | POST, галочка ✓ у модуля в sidebar             |
| 4   | Прогресс обновился                                                      | 1 из N модулей → ~33% (если 3 модуля)          |
| 5   | Повторное нажатие «пройден»                                             | Прогресс не «перепрыгивает» некорректно        |
| 6   | Django shell: `ModuleProgress.objects.filter(user__username='student')` | Запись с `completed=True`                      |


```bash
python manage.py shell -c "
from django.contrib.auth.models import User
from students.services import get_course_progress
from courses.models import Course
u = User.objects.get(username='student')
c = u.courses_joined.first()
print(get_course_progress(u, c), '%')
"
```

---

<a id="section-13"></a>
## 13. Викторины и тесты

**Задача из ТЗ:** «викторины», «ответы на вопросы», «прохождение тестов». Quiz — пятый тип контента в модуле.

### 13.1. Модели — добавить в `courses/models.py`

**Структура:** Quiz → Question → Answer. QuizResult хранит итог для каждого студента.

```python
class Quiz(ItemBase):
    description = models.TextField(blank=True)
    pass_percent = models.PositiveIntegerField(default=70, ...)


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', ...)
    text = models.TextField()
    order = OrderField(blank=True, for_fields=['quiz'])


class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', ...)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)


class QuizResult(models.Model):
    user = models.ForeignKey(User, ...)
    quiz = models.ForeignKey(Quiz, ...)
    score = models.PositiveIntegerField()
    passed = models.BooleanField(default=False)
```

**Разбор моделей:**


| Модель                                    | Зачем                                                                                     |
| ----------------------------------------- | ----------------------------------------------------------------------------------------- |
| `Quiz` наследует `ItemBase`               | Попадает в полиморфный контент как Text/File — единый CMS-путь                            |
| `pass_percent`                            | Порог зачёта: 70% правильных → passed=True                                                |
| `Question` отдельно от Quiz               | Один тест — много вопросов (1:N)                                                          |
| `Answer`                                  | Варианты ответа; несколько могут быть `is_correct=True` (если нужно)                      |
| `QuizResult` UniqueConstraint(user, quiz) | Один итог на студента; повторное прохождение **обновляет** score через `update_or_create` |


Не забудьте добавить `'quiz'` в `limit_choices_to` модели `Content`.

### 13.2. Admin для викторин (опционально)

Admin дублирует CMS — удобен для массового редактирования. Основной путь для преподавателя — **раздел 8.7**.

```python
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
```

**Как создать тест (рекомендуемый путь):**

1. CMS → модуль → «Викторина» (title, pass_percent)
2. Страница «Вопросы» → «Добавить вопрос»
3. Заполнить варианты, отметить `is_correct` у верных
4. Студент видит ссылку «Пройти тест» в материалах курса

**Альтернатива:** Admin → Quiz → Questions → Answers.

### 13.3. Шаблон ссылки на тест

`courses/templates/courses/content/quiz.html`:

```html
{% if item.description %}
<p>{{ item.description|linebreaks }}</p>
{% endif %}
<p>
  <a href="{% url 'quiz_take' course_id=course.id quiz_id=item.id %}"
     class="button">Пройти тест «{{ item.title }}»</a>
</p>
```

> В `render()` для Quiz переопределите контекст, если нужен `course` — или передавайте через session/request.

Упрощение: в шаблоне студента вместо `item.render` для quiz выводите ссылку напрямую:

```html
{% if content.content_type.model == 'quiz' %}
  <a href="{% url 'quiz_take' object.id content.object_id %}">Пройти тест</a>
{% else %}
  {{ item.render|safe }}
{% endif %}
```

### 13.4. Прохождение теста

**Задача:** GET — показать вопросы; POST — проверить ответы, сохранить результат, редирект.

**Шаблон `take.html` — разбор формы:**


| Элемент                             | Зачем                                 |
| ----------------------------------- | ------------------------------------- |
| `name="question_{{ question.id }}"` | Уникальное имя поля на каждый вопрос  |
| `value="{{ answer.id }}"`           | На сервер уходит id выбранного Answer |
| `type="radio"`                      | Один ответ на вопрос                  |
| `required`                          | Браузер не отправит форму без выбора  |


**View `QuizTakeView.post` — разбор логики:**

```python
selected_id = request.POST.get(f'question_{question.id}')
if selected_id and question.answers.filter(pk=selected_id, is_correct=True).exists():
    correct += 1
score = int(correct / len(questions) * 100)
passed = score >= quiz.pass_percent
QuizResult.objects.update_or_create(...)
```


| Строка                                              | Зачем                                                                         |
| --------------------------------------------------- | ----------------------------------------------------------------------------- |
| `request.POST.get(...)`                             | Достаём выбранный answer id (или None если пропустил)                         |
| `.filter(pk=selected_id, is_correct=True).exists()` | Проверяем **на сервере** — нельзя доверять hidden field «я ответил правильно» |
| `update_or_create`                                  | Первое прохождение — INSERT; повторное — UPDATE score                         |
| `redirect('quiz_result', ...)`                      | PRG-паттерн: после POST редирект, чтобы F5 не отправил форму снова            |


**Безопасность:** `get_object_or_404(Course, pk=pk, students=request.user)` — чужой курс → 404. Студент не может проходить тест курса, на который не записан.

```html
{% extends "base.html" %}
{% block title %}{{ quiz.title }}{% endblock %}
{% block content %}
<h1>{{ quiz.title }}</h1>
<form method="post">
  {% csrf_token %}
  {% for question in questions %}
  <div class="module">
    <p><strong>{{ forloop.counter }}. {{ question.text }}</strong></p>
    {% for answer in question.answers.all %}
    <label>
      <input type="radio" name="question_{{ question.id }}"
             value="{{ answer.id }}" required>
      {{ answer.text }}
    </label><br>
    {% endfor %}
  </div>
  {% endfor %}
  <input type="submit" value="Отправить ответы" class="button">
</form>
{% endblock %}
```

`students/views.py`:

```python
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from courses.models import Quiz, QuizResult


class QuizTakeView(LoginRequiredMixin, View):
    template_name = 'students/quiz/take.html'

    def get(self, request, pk, quiz_id):
        course = get_object_or_404(Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        return render(request, self.template_name, {
            'course': course,
            'quiz': quiz,
            'questions': quiz.questions.prefetch_related('answers'),
        })

    def post(self, request, pk, quiz_id):
        course = get_object_or_404(Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        questions = list(quiz.questions.all())
        if not questions:
            return redirect('student_course_detail', pk)

        correct = 0
        for question in questions:
            selected_id = request.POST.get(f'question_{question.id}')
            if selected_id and question.answers.filter(
                    pk=selected_id, is_correct=True).exists():
                correct += 1

        score = int(correct / len(questions) * 100)
        passed = score >= quiz.pass_percent

        QuizResult.objects.update_or_create(
            user=request.user, quiz=quiz,
            defaults={'score': score, 'passed': passed})

        return redirect('quiz_result', pk=pk, quiz_id=quiz_id)


class QuizResultView(LoginRequiredMixin, View):
    template_name = 'students/quiz/result.html'

    def get(self, request, pk, quiz_id):
        course = get_object_or_404(Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        result = get_object_or_404(QuizResult, user=request.user, quiz=quiz)
        return render(request, self.template_name, {
            'course': course, 'quiz': quiz, 'result': result,
        })
```

`students/templates/students/quiz/result.html`:

```html
{% extends "base.html" %}
{% block title %}Результат — {{ quiz.title }}{% endblock %}
{% block content %}
<h1>Результат теста «{{ quiz.title }}»</h1>
<div class="module">
  <p>Ваш результат: <strong>{{ result.score }}%</strong></p>
  {% if result.passed %}
    <p class="success">Тест сдан! (минимум {{ quiz.pass_percent }}%)</p>
  {% else %}
    <p class="error">Тест не сдан. Нужно минимум {{ quiz.pass_percent }}%.</p>
  {% endif %}
  <p><a href="{% url 'student_course_detail' course.id %}">Вернуться к курсу</a></p>
</div>
{% endblock %}
```

<a id="stage-13"></a>
### ✅ Проверка этапа 13 — прохождение викторины

**Перед проверкой:** модели Quiz/Question/Answer/QuizResult в `courses`, migrate.


| #   | Действие                                                             | Ожидание                                   |
| --- | -------------------------------------------------------------------- | ------------------------------------------ |
| 1   | Студент → модуль с викториной → «Пройти тест»                        | Форма с radio-кнопками                     |
| 2   | Ответить правильно на все вопросы → Отправить                        | `/students/course/<id>/quiz/<qid>/result/` |
| 3   | Результат ≥ pass_percent                                             | «Тест сдан!» зелёным                       |
| 4   | Ответить неверно → снова пройти                                      | «Тест не сдан», score обновляется          |
| 5   | Admin / shell: `QuizResult.objects.filter(user__username='student')` | Запись score, passed                       |
| 6   | Чужой курс `/students/course/999/quiz/1/`                            | **404**                                    |


---

<a id="section-14"></a>
## 14. Сертификаты и награды

**Задача из ТЗ:** «система наград и сертификатов по завершении курсов».

**Когда выдаётся:** `mark_module_complete()` → прогресс 100% → `on_course_completed()`.

### 14.1. Модели — `students/models.py`

**Зачем три модели, а не одна Certificate?**


| Модель        | Зачем отдельно                                                    |
| ------------- | ----------------------------------------------------------------- |
| `Certificate` | Официальный документ: user + course + UUID для проверки           |
| `Badge`       | Награда может быть привязана к курсу или быть общей (course=null) |
| `UserBadge`   | Many-to-many «кто какую награду получил» с датой                  |


```python
class Certificate(models.Model):
    user = models.ForeignKey(User, related_name='certificates', ...)
    course = models.ForeignKey(Course, related_name='certificates', ...)
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
```

**Разбор Certificate:**


| Поле                      | Зачем                                                                         |
| ------------------------- | ----------------------------------------------------------------------------- |
| `code` UUID               | Публичная ссылка `/students/certificate/a1b2c3d4-.../` — нельзя угадать чужой |
| `unique (user, course)`   | Один сертификат на пару — повторная выдача не создаёт дубликат                |
| `get_or_create` в сервисе | Идempotent: повторный вызов при 100% не ломает данные                         |


### 14.2. Автовыдача — уже в `students/services.py`

Функция `on_course_completed(user, course)` вызывается из `mark_module_complete()` — см. раздел 12.3.

**Почему не signal `post_save`?**  
Явный вызов из сервиса проще читать и отлаживать: видна цепочка «модуль → прогресс → сертификат».

### 14.3. Страница сертификата

**Задача:** студент открывает ссылку с UUID — видит ФИО, курс, дату.

```python
class CertificateDetailView(LoginRequiredMixin, DetailView):
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)
```

**Разбор:** `get_queryset().filter(user=...)` — даже зная UUID, **чужой** сертификат не откроешь (404).

Модели Badge и UserBadge (добавить в тот же `students/models.py`):

```python
class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='badges/', blank=True)
    course = models.ForeignKey(
        Course, related_name='badges', null=True, blank=True,
        on_delete=models.CASCADE)

class UserBadge(models.Model):
    user = models.ForeignKey(User, related_name='user_badges', on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, related_name='awarded_to', on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)
```

**Разбор Badge:** `course=null` — глобальная награда; `course=5` — только за этот курс. Создайте badge в admin заранее — при 100% прогресса `award_course_badges()` выдаст автоматически.

### 14.4. Профиль с наградами

**Задача:** страница со списком всех сертификатов и badges студента.

```python
class StudentProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'students/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['certificates'] = user.certificates.select_related('course')
        ctx['badges'] = user.user_badges.select_related('badge')
        return ctx
```

**Разбор:** `select_related('course')` — JOIN в одном SQL-запросе вместо N+1 (отдельный запрос на каждый сертификат).

<a id="stage-14"></a>
### ✅ Проверка этапа 14 — сертификаты (финал)

**Перед проверкой:**

1. `makemigrations students` + `migrate` (Certificate, Badge, UserBadge)
2. Admin → Badge → создать награду с `course` = ваш тестовый курс


| #   | Действие                                                                           | Ожидание                            |
| --- | ---------------------------------------------------------------------------------- | ----------------------------------- |
| 1   | Студент отмечает **все** модули пройденными                                        | Прогресс 100%                       |
| 2   | [http://127.0.0.1:8000/students/profile/](http://127.0.0.1:8000/students/profile/) | Сертификат «Python Basics» в списке |
| 3   | Клик по сертификату                                                                | Страница с UUID, ФИО, дата          |
| 4   | Награда (Badge) в профиле                                                          | Если создан badge для курса         |
| 5   | Shell: `Certificate.objects.filter(user__username='student').count()`              | ≥ 1                                 |
| 6   | **Финальный прогон** — таблица ниже                                                | Все пункты ✓                        |


**Финальная таблица «всё работает»:**


| Функция                   | URL                       | ✓   |
| ------------------------- | ------------------------- | --- |
| Каталог                   | `/`                       | ☐   |
| CMS курсов                | `/course/mine/`           | ☐   |
| Модули + 5 типов контента | `/course/.../modules/`    | ☐   |
| CMS викторин              | `.../quiz/.../questions/` | ☐   |
| Регистрация               | `/students/register/`     | ☐   |
| Мои курсы + %             | `/students/courses/`      | ☐   |
| Материалы + progress bar  | `/students/course/<id>/`  | ☐   |
| Прохождение теста         | `.../quiz/<id>/`          | ☐   |
| Сертификат                | `/students/profile/`      | ☐   |


---

<a id="section-15"></a>
## 15. Карта URL и сценарии пользователей

### 15.1. Все URL


| URL                                          | Кто           | Что делает                       |
| -------------------------------------------- | ------------- | -------------------------------- |
| `/`                                          | все           | Каталог курсов                   |
| `/subject/python/`                           | все           | Курсы по предмету                |
| `/course/django-basics/`                     | все           | Предпросмотр + запись            |
| `/accounts/login/`                           | все           | Вход                             |
| `/students/register/`                        | гость         | Регистрация                      |
| `/students/courses/`                         | студент       | **Главная ЛК** — мои курсы + %   |
| `/students/course/3/`                        | студент       | Материалы (1-й модуль)           |
| `/students/course/3/module/12/`              | студент       | Конкретный модуль                |
| `/students/course/3/quiz/5/`                 | студент       | Прохождение теста                |
| `/students/certificate/<uuid>/`              | студент       | Сертификат                       |
| `/course/mine/`                              | преподаватель | CMS: мои курсы                   |
| `/course/<pk>/modules/`                      | преподаватель | Редактор модулей + контент       |
| `/course/module/N/content/quiz/Q/questions/` | преподаватель | CMS: вопросы викторины           |
| `/students/profile/`                         | студент       | Сертификаты и награды            |
| `/admin/`                                    | admin         | Subject, Badge, опционально Quiz |


### 15.2. Сценарий «студент с нуля»

1. `/students/register/` — создаёт аккаунт, автоматически входит
2. Попадает на `/students/courses/` — пусто
3. `/` — выбирает курс → «Записаться»
4. Снова `/students/courses/` — курс появился, прогресс 0%
5. Открывает материалы → читает → «Модуль пройден»
6. Проходит викторину → видит %
7. После последнего модуля → сертификат в профиле

### 15.3. Сценарий «преподаватель»

1. Admin: пользователь в группе **Instructors** (права `courses.`*)
2. `/course/mine/` → «Создать курс»
3. «Модули» → добавить разделы, сохранить formset
4. Chips «Текст / Файл / … / Викторина» — наполнить каждый модуль
5. Для викторины: «Вопросы» → добавить Q&A с `is_correct`
6. Студенты видят курс в каталоге `/` и записываются

---

<a id="section-16"></a>
## 16. Структура файлов проекта

Полное дерево для сверки при end-to-end разработке:

```text
TMS_django_courses/
├── manage.py
├── .env                          # секреты (gitignore)
├── requirements.txt
├── README.md
├── guide.md
├── educa/
│   ├── settings.py               # .env, DATABASES, INSTALLED_APPS
│   ├── urls.py                   # login, admin, course/, students/, /
│   ├── wsgi.py
│   └── asgi.py
├── scripts/
│   └── init_postgres.sql
├── courses/
│   ├── models.py                 # Subject, Course, Module, Content, Quiz...
│   ├── fields.py                 # OrderField
│   ├── views.py                  # CMS, каталог, QuizManageView...
│   ├── forms.py                  # ModuleFormSet, AnswerFormSet
│   ├── urls.py                   # /course/...
│   ├── public_urls.py            # /, /subject/, /course/<slug>/
│   ├── admin.py
│   ├── fixtures/subjects.json
│   ├── migrations/
│   ├── static/css/base.css
│   └── templates/
│       ├── base.html
│       ├── registration/
│       ├── courses/course/       # list, detail (каталог)
│       ├── courses/manage/       # CMS
│       │   ├── course/
│       │   ├── module/
│       │   ├── content/
│       │   └── quiz/             # manage.html, question_form.html
│       └── courses/content/      # text, file, image, video, quiz
└── students/
    ├── models.py                 # ModuleProgress, Certificate, Badge...
    ├── views.py                  # registration, enroll, quiz take...
    ├── services.py               # progress, certificate logic
    ├── forms.py                  # CourseEnrollForm
    ├── urls.py
    ├── admin.py
    ├── templatetags/course_tags.py
    ├── migrations/
    └── templates/students/
        ├── student/registration.html
        ├── course/list.html, detail.html
        ├── quiz/take.html, result.html
        ├── certificate/detail.html
        └── profile.html
```

---

<a id="section-17"></a>
## 17. Чеклист и типичные ошибки

### 17.1. Чеклист перед сдачей

Пройдите все **14 этапов** из [§0](#section-0) и финальную таблицу в [§14](#stage-14).

- [ ] Этапы 1–14: каждый блок «✅ Проверка» пройден
- [ ] `.env` создан, `DB_PASSWORD` совпадает с PostgreSQL
- [ ] Преподаватель: курс → модули → контент всех 5 типов + CMS викторин
- [ ] Студент: регистрация → запись → прогресс → тест → сертификат
- [ ] Redis **не** используется

### 17.2. Типичные ошибки

<a id="section-17-errors"></a>

| Ошибка | Причина | Решение |
|---|---|---|
| `connection refused` на 5432 | PostgreSQL не запущен | `sudo systemctl start postgresql` |
| `password authentication failed` (postgres) | `-h localhost` без пароля | `sudo -u postgres psql -f scripts/init_postgres.sql` |
| `password authentication failed` (educa_user) | пароль не совпадает | перезапустить init script, проверить `.env` |
| `Could not parse 'm==module'` | нет пробелов в `{% if %}` | писать `{% if m == module %}` |
| `No module named 'psycopg2'` | не установлен адаптер | `pip install psycopg2-binary` |
| `TemplateDoesNotExist` | неверный путь шаблона | `app/templates/`, `APP_DIRS=True` |
| `NoReverseMatch` | URL не подключён | проверить `include('students.urls')` |
| Студент видит чужой курс | нет фильтра | `filter(students=request.user)` |
| Ссылки в гайде не работают | кириллические auto-anchors | используйте `#section-N` и `#stage-N` |

### 17.3. Порядок разработки

Следуйте [таблице этапов §0](#section-0). После каждого этапа — блок «✅ Проверка» (`#stage-1` … `#stage-14`).

---

## Дополнительные ресурсы

- [Django 6.0 Documentation](https://docs.djangoproject.com/en/6.0/)
- [PostgreSQL notes for Django](https://docs.djangoproject.com/en/6.0/ref/databases/#postgresql-notes)
- [Django 4 by Example — Chapter 12](https://github.com/PacktPublishing/Django-4-by-Example/tree/main/Chapter12)
- [Generic relations](https://docs.djangoproject.com/en/6.0/ref/contrib/contenttypes/)

