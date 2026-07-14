# Шаг 10 — Сертификаты, профиль, admin

**Предыдущий:** [step-09-quiz-test.md](step-09-quiz-test.md) · **Следующий:** [step-11-final.md](step-11-final.md)

## Зачем

При 100% прогресса `on_course_completed()` создаёт **Certificate** и выдаёт **Badge**. Профиль показывает награды. Admin позволяет управлять badges.

## 1. Заменить `students/admin.py` целиком

```python
from django.contrib import admin

from .models import Badge, Certificate, ModuleProgress, CourseProgress


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'course']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'issued_at']
    list_filter = ['issued_at']


@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'module', 'completed', 'completed_at']


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'completed', 'completed_at']
```

## 2. Admin — создать Badge (один раз)

1. Войти как **admin** → [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
2. **Badges → Add**
3. Name: **Python Master**
4. Course: **Python Basics** (ваш тестовый курс)
5. Description — по желанию
6. Icon — по желанию (можно оставить пустым)
7. Save

---

## ✅ Ручная проверка (сделайте сейчас)

```bash
python manage.py check
python manage.py runserver
```

### Admin

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | Admin → Badges | Badge **Python Master** привязан к курсу |
| ☐ | Admin → Certificates | Список (может быть пуст до прохождения) |
| ☐ | Admin → Module progress / Course progress | Записи появляются после отметки модулей |

### Завершение курса (100%)

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | Войти как **`student`** | — |
| ☐ | `/students/course/<id>/` | Если не 100% — отметить **все** модули «пройденными» |
| ☐ | Progress bar | **100%** |
| ☐ | Shell — Certificate создан | count ≥ 1 |

```bash
python manage.py shell -c "
from students.models import Certificate
from django.contrib.auth.models import User
u = User.objects.get(username='student')
print(Certificate.objects.filter(user=u).count())
"
```

### Профиль и сертификат

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | [http://127.0.0.1:8000/students/profile/](http://127.0.0.1:8000/students/profile/) | Сертификат **Python Basics** в списке |
| ☐ | Клик по сертификату | URL `/students/certificate/<uuid>/` |
| ☐ | Страница сертификата | UUID (code), имя пользователя, название курса, дата выдачи |
| ☐ | Badge в профиле | **Python Master** (если badge создан в admin) |
| ☐ | Чужой UUID сертификата (другой user) | **404** |

### Повторное завершение

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | Снова отметить уже пройденный модуль | Нет дубликата Certificate |
| ☐ | Admin → Certificates для `student` | Одна запись на курс |

**Все пункты отмечены?** → [step-11-final.md](step-11-final.md)
