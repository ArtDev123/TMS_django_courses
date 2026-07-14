# Шаг 5 — Модели студента (прогресс, сертификаты, badges)

**Предыдущий:** [step-04-cms.md](step-04-cms.md) · **Следующий:** [step-06-services.md](step-06-services.md)

## Зачем

- **ModuleProgress** — галочки ✓ в sidebar и progress bar.
- **CourseProgress** — курс полностью пройден (100%).
- **Certificate** — выдаётся при завершении курса.
- **Badge / UserBadge** — награды за курс.

## 1. Заменить `students/models.py` целиком

Скопируйте из [`code/students_models.py`](code/students_models.py) или вставьте код ниже:

```python
import uuid

from django.db import models
from django.contrib.auth.models import User

from courses.models import Course, Module


class ModuleProgress(models.Model):
    user = models.ForeignKey(
        User, related_name='module_progress', on_delete=models.CASCADE)
    module = models.ForeignKey(
        Module, related_name='student_progress', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'module'],
                name='unique_user_module_progress',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.module}'


class CourseProgress(models.Model):
    user = models.ForeignKey(
        User, related_name='course_progress', on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course, related_name='student_progress', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_progress',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.course}'


class Certificate(models.Model):
    user = models.ForeignKey(
        User, related_name='certificates', on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course, related_name='certificates', on_delete=models.CASCADE)
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_certificate',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.course}'


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='badges/', blank=True)
    course = models.ForeignKey(
        Course, related_name='badges', null=True, blank=True,
        on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        User, related_name='user_badges', on_delete=models.CASCADE)
    badge = models.ForeignKey(
        Badge, related_name='awarded_to', on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'badge'],
                name='unique_user_badge',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.badge}'
```

## 2. Миграция

```bash
python manage.py makemigrations students
python manage.py migrate
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
| ☐ | `python manage.py makemigrations students` | Создана миграция `students.0001_...` |
| ☐ | `python manage.py migrate` | `Applying students.0001_... OK` |
| ☐ | Shell — импорт моделей | Без ошибок (см. команду ниже) |
| ☐ | `python manage.py showmigrations students` | `[X] 0001_initial` |
| ☐ | Admin → обновить страницу | Появились модели ModuleProgress, CourseProgress, Certificate, Badge (admin настроим на шаге 10) |
| ☐ | Сервер запускается | `runserver` без ошибок импорта |

### Команды

```bash
python manage.py shell -c "
from students.models import ModuleProgress, CourseProgress, Certificate, Badge, UserBadge
print('students models OK')
"

python manage.py showmigrations students
```

**Все пункты отмечены?** → [step-06-services.md](step-06-services.md)
