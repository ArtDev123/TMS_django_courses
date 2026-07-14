# Шаг 2 — Subject + группа Instructors

**Предыдущий:** [step-01-config.md](step-01-config.md) · **Следующий:** [step-03-quiz-models.md](step-03-quiz-models.md)

## Зачем

Курсы привязаны к **Subject** (Programming, Math). Преподаватель работает в CMS через группу **Instructors** — без прав superuser.

## 1. Создать `courses/fixtures/subjects.json`

```json
[
  {
    "model": "courses.subject",
    "pk": 1,
    "fields": {
      "title": "Programming",
      "slug": "programming"
    }
  },
  {
    "model": "courses.subject",
    "pk": 2,
    "fields": {
      "title": "Mathematics",
      "slug": "mathematics"
    }
  },
  {
    "model": "courses.subject",
    "pk": 3,
    "fields": {
      "title": "Music",
      "slug": "music"
    }
  }
]
```

## 2. Загрузить

```bash
python manage.py loaddata subjects
```

## 3. Admin — один раз вручную

1. [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/) — если нет superuser:
   ```bash
   python manage.py createsuperuser
   ```
   Логин: `admin`

2. **Groups → Add** → Name: `Instructors`

3. **Permissions** — отметить все из:
   - `courses | course` (add, change, delete, view)
   - `courses | module`, `content`, `text`, `file`, `image`, `video`, `quiz`
   - **Не** отмечать `courses | subject`

4. **Users → Add** → Username: `teacher`, пароль на ваш выбор → Groups: Instructors

---

## проверка

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | Admin → Subjects | 3 записи: Programming, Mathematics, Music |
| ☐ | Admin → Groups | Есть группа Instructors с правами courses |
| ☐ | Admin → Users | Пользователь `teacher` в группе Instructors |
| ☐ | [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/) → вход `teacher` | Успешный вход |
| ☐ | `teacher` → `/admin/` | Admin открывается (не superuser, но staff если включили — иначе только CMS на шаге 4) |

### Команда

```bash
python manage.py shell -c "from courses.models import Subject; print(Subject.objects.count())"
# 3
```

**Все пункты отмечены?** → [step-03-quiz-models.md](step-03-quiz-models.md)
