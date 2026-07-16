# Шаг 1 — Настройки, media, каталог по slug

**Предыдущий:** [README](README.md) · **Следующий:** [step-02-fixtures.md](step-02-fixtures.md)

## Зачем

- **MEDIA** — загрузка PDF и картинок в CMS (шаг 4).
- **LOGIN_REDIRECT_URL** — после входа редирект в ЛК студента (URL появится на шаге 7).
- **slug_field** — URL `/course/python-basics/` ищет курс по slug, а не по pk.

## 1. `educa/settings.py` — в конец файла

```python
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_REDIRECT_URL = '/students/courses/'
LOGOUT_REDIRECT_URL = '/'
```

## 2. `courses/views.py` — добавить `slug_field`

```python
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'
    slug_field = 'slug'
```

## 3. `courses/templates/base.html` — меню для гостей (остальное — позже)

На этом шаге включаем только ссылки, которые **уже работают**. Пункты «Мои курсы», «Профиль», «Преподавание» добавим на шагах 4 и 7.

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
          <li>
            <form action="{% url 'logout' %}" method="post" class="logout-form">
              {% csrf_token %}
              <button type="submit">Выход</button>
            </form>
          </li>
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

---

## ✅ Ручная проверка (сделайте сейчас)

Перезапустите сервер, если он уже был запущен.

```bash
python manage.py check
python manage.py runserver
```

### Чеклист в браузере


| ☐   | Действие                                                                               | Ожидаемый результат                                                             |
| --- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| ☐   | Открыть [http://127.0.0.1:8000/](http://127.0.0.1:8000/)                               | Каталог (может быть пустым), тёмная шапка, CSS загружен                         |
| ☐   | Шапка: «Каталог», «Вход», «Регистрация»                                                | Ссылки видны (гость)                                                            |
| ☐   | [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/)         | Форма входа в карточке                                                          |
| ☐   | Войти под `admin` (если есть)                                                          | Редирект на `/students/courses/` — **404 нормально** (страница будет на шаге 7) |
| ☐   | После входа — только кнопка «Выход»                                                    | Нет ошибки `NoReverseMatch`                                                     |
| ☐   | Admin → Courses → создать курс: slug `test-course`, subject любой                      | Сохранено                                                                       |
| ☐   | [http://127.0.0.1:8000/course/test-course/](http://127.0.0.1:8000/course/test-course/) | Страница курса, **не** 404                                                      |


### Команды в терминале

```bash
python manage.py check
# System check identified no issues (0 silenced).
```

**Все пункты отмечены?** → [step-02-fixtures.md](step-02-fixtures.md)