# Шаг 6 — Сервисы + template tags

**Предыдущий:** [step-05-student-models.md](step-05-student-models.md) · **Следующий:** [step-07-student-views.md](step-07-student-views.md)

## Зачем

Логика прогресса и сертификатов — в одном месте. Шаблоны используют фильтры `course_progress` и `module_completed` без дублирования кода в views.

## 1. Создать `students/services.py`

Скопируйте из [`code/students_services.py`](code/students_services.py) или вставьте код ниже:

```python
from django.utils import timezone

from students.models import (
    ModuleProgress, CourseProgress, Certificate, Badge, UserBadge,
)


def get_course_progress(user, course):
    total = course.modules.count()
    if total == 0:
        return 0
    done = ModuleProgress.objects.filter(
        user=user, module__course=course, completed=True,
    ).count()
    return int(done / total * 100)


def mark_module_complete(user, module):
    progress, _ = ModuleProgress.objects.get_or_create(
        user=user, module=module)
    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

    course = module.course
    if get_course_progress(user, course) == 100:
        cp, _ = CourseProgress.objects.get_or_create(
            user=user, course=course)
        if not cp.completed:
            cp.completed = True
            cp.completed_at = timezone.now()
            cp.save()
            on_course_completed(user, course)


def is_module_completed(user, module):
    return ModuleProgress.objects.filter(
        user=user, module=module, completed=True,
    ).exists()


def issue_certificate(user, course):
    return Certificate.objects.get_or_create(user=user, course=course)


def award_course_badges(user, course):
    for badge in Badge.objects.filter(course=course):
        UserBadge.objects.get_or_create(user=user, badge=badge)


def on_course_completed(user, course):
    issue_certificate(user, course)
    award_course_badges(user, course)
```

## 2. Создать `students/templatetags/__init__.py`

Пустой файл.

## 3. Создать `students/templatetags/course_tags.py`

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

---

## ✅ Ручная проверка (сделайте сейчас)

```bash
python manage.py check
python manage.py runserver
```

### Чеклист в браузере и терминале

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | `python manage.py check` | 0 issues |
| ☐ | Shell — вызов `get_course_progress` | Число 0–100 или 0 (см. команду) |
| ☐ | Shell — импорт template tags | Без ошибок |
| ☐ | Сервер запускается | Нет ошибок при старте |

### Команды

```bash
python manage.py shell -c "
from students.services import get_course_progress
from django.contrib.auth.models import User
from courses.models import Course
u = User.objects.first()
c = Course.objects.first()
if u and c:
    print('progress:', get_course_progress(u, c))
else:
    print('Нет user или course — создайте на шагах 2 и 4')
"

python manage.py shell -c "
from students.templatetags.course_tags import course_progress, module_completed
print('course_tags OK')
"
```

**Все пункты отмечены?** → [step-07-student-views.md](step-07-student-views.md)
