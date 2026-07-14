# Educa LMS — пошаговая доработка

Дополнение к [guide.md](../guide.md). Каждый файл — **один этап**: код + **ручная проверка в браузере** в конце.

> **Правило:** не открывайте следующий шаг, пока не отметили все пункты «✅ Готово» в текущем.

## Порядок шагов

| # | Файл | Что делаете |
|---|------|-------------|
| 0 | *(этот файл)* | Аудит: что уже есть |
| 1 | [step-01-config.md](step-01-config.md) | MEDIA, редиректы, slug каталога |
| 2 | [step-02-fixtures.md](step-02-fixtures.md) | Subject + группа Instructors |
| 3 | [step-03-quiz-models.md](step-03-quiz-models.md) | Модели Quiz + миграция |
| 4 | [step-04-cms.md](step-04-cms.md) | CMS преподавателя (`/course/`) |
| 5 | [step-05-student-models.md](step-05-student-models.md) | Прогресс, сертификаты, badges |
| 6 | [step-06-services.md](step-06-services.md) | services + template tags |
| 7 | [step-07-student-views.md](step-07-student-views.md) | ЛК студента, enroll, quiz |
| 8 | [step-08-progress-test.md](step-08-progress-test.md) | **Только тест:** progress bar |
| 9 | [step-09-quiz-test.md](step-09-quiz-test.md) | **Только тест:** прохождение теста |
| 10 | [step-10-certificates.md](step-10-certificates.md) | Admin badges + сертификаты |
| 11 | [step-11-final.md](step-11-final.md) | Финальный прогон |

## Что уже сделано в репозитории

| Компонент | Статус |
|-----------|--------|
| Django 6, venv, PostgreSQL, `.env` | ✅ |
| Модели Subject → Video | ✅ |
| Миграция `courses.0001_initial` | ✅ |
| Каталог `/` (CourseListView) | ✅ |
| Регистрация `/students/register/` | ✅ |
| Все HTML-шаблоны (24 шт.) + CSS | ✅ |
| `courses/urls.py` (маршруты CMS) | ✅ файл есть, **views нет** |
| Quiz, students models, CMS views | ❌ шаги 3–7 |
| `courses/forms.py`, `students/services.py` | ❌ |

## Тестовые пользователи (создадите по ходу)

| Логин | Роль | Когда создать |
|-------|------|---------------|
| `admin` | superuser | шаг 2 |
| `teacher` | Instructors | шаг 2 |
| `student` | студент | шаг 7 |

## Папка `code/`

Большие файлы (views) лежат отдельно — копируйте в проект:

```bash
cp docs/remaining/code/courses_views.py courses/views.py      # шаг 4
cp docs/remaining/code/students_views.py students/views.py  # шаг 7
```

| Файл | Куда |
|------|------|
| `code/courses_views.py` | `courses/views.py` |
| `code/students_views.py` | `students/views.py` |
| `code/students_models.py` | `students/models.py` |
| `code/students_services.py` | `students/services.py` |

## Быстрые команды

```bash
source .venv/bin/activate
python manage.py runserver
```

Сервер: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
