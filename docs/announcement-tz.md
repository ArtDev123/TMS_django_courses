# ТЗ: Объявления курса (Announcement)


---

## 1. Цель

Преподаватель публикует организационные сообщения по курсу
(дедлайны, созвоны, обновления). Студент, записанный на курс, их читает.

Объявления **не** являются контентом модуля (`Text` / `Video` / `Quiz`) —
это отдельная сущность рядом с материалами.

---

## 2. Модель `Announcement` — список полей

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `course` | FK → `Course` | да | Курс, к которому относится объявление |
| `author` | FK → `User` | да | Автор (преподаватель). В форме **не показывать** — ставить во view |
| `title` | строка, до 200 символов | да | Заголовок |
| `body` | длинный текст | да | Текст объявления |
| `is_published` | да/нет, по умолчанию `True` | да | Черновик / опубликовано |
| `created` | дата-время, авто при создании | да | Дата создания (только чтение) |
| `updated` | дата-время, авто при сохранении | да | Дата изменения (только чтение) |

**Сортировка по умолчанию:** от новых к старым (`-created`).

**Права (логика, без кода):**

| Роль | Список / детали | Create / Update / Delete |
|------|-----------------|---------------------------|
| Преподаватель (владелец курса) | все объявления своего курса, включая черновики | да |
| Студент (записан на курс) | только `is_published=True` | нет |
| Чужой пользователь | 403 / 404 | нет |

Правило владельца (как у курсов): доступ к CMS-объявлениям только если  
`announcement.course.owner == request.user`.  
Поле `author` — кто написал; **фильтр доступа** строится по `course.owner`, не по `author`.

---

## 3. Миксины (по аналогии с `OwnerCourseMixin`)

В проекте для курсов уже есть цепочка:

`OwnerMixin` → `OwnerEditMixin` → `OwnerCourseMixin` → `OwnerCourseEditMixin`

Для объявлений нужна **такая же схема**, но фильтр не `owner=user`, а  
`course__owner=user` (владелец курса).

Миксины положить рядом с CMS views (например в `courses/views.py` или отдельный
`courses/mixins.py`) — без копипасты `get_queryset` / `form_valid` в каждый view.

### 3.1. Набор миксинов

| Миксин | Наследует | Что обязан делать |
|--------|-----------|-------------------|
| `CourseOwnerMixin` | — | В `get_queryset`: оставить только объекты, у которых `course.owner` = текущий user. База для list / detail / update / delete в CMS. |
| `AnnouncementAuthorMixin` | — | В `form_valid` (Create/Update): перед сохранением выставить `form.instance.author` = текущий user. Аналог `OwnerEditMixin`, но поле называется `author`, не `owner`. |
| `AnnouncementCourseMixin` | `CourseOwnerMixin` + `LoginRequiredMixin` + `PermissionRequiredMixin` | Общие настройки CMS CRUD: `model = Announcement`, `fields` формы (`title`, `body`, `is_published`). Аналог `OwnerCourseMixin`. |
| `AnnouncementEditMixin` | `AnnouncementCourseMixin` + `AnnouncementAuthorMixin` | Общий `template_name` для create/update (form.html). Аналог `OwnerCourseEditMixin`. |

### 3.2. Схема наследования (MRO)

```text
CourseOwnerMixin          AnnouncementAuthorMixin
        \                        /
         \                      /
    AnnouncementCourseMixin ----'
   (Login + Permission + model/fields)
                |
                +---- AnnouncementEditMixin  (template form.html)
                |
                +---- List / Detail / Delete напрямую
```

Views:

```text
AnnouncementListView    = AnnouncementCourseMixin + ListView
AnnouncementDetailView  = AnnouncementCourseMixin + DetailView   # только CMS-вариант
                                                          # либо отдельный student detail
AnnouncementCreateView  = AnnouncementEditMixin + CreateView
AnnouncementUpdateView  = AnnouncementEditMixin + UpdateView
AnnouncementDeleteView  = AnnouncementCourseMixin + DeleteView
```

Студенческие views **не** наследуют `CourseOwnerMixin` — у них другая логика
(запись на курс + `is_published`).

### 3.3. Permissions (как у Course)

Использовать стандартные permissions модели `Announcement`
(после миграции Django создаст их сам):

| View | `permission_required` |
|------|------------------------|
| List / Detail (CMS) | `courses.view_announcement` |
| Create | `courses.add_announcement` |
| Update | `courses.change_announcement` |
| Delete | `courses.delete_announcement` |

Группа **Instructors** должна получить эти permissions (как для `Course`) —
через admin или data-миграцию / фикстуру. Без этого `PermissionRequiredMixin`
вернёт 403 даже владельцу курса.

### 3.4. Курс из URL + проверка владельца

У list/create в URL есть `course_id`. Миксин/view должен:

1. Достать курс: только если `Course.pk == course_id` **и** `owner == request.user`
   (иначе 404) — тот же приём, что `CourseModuleUpdateView.dispatch`.
2. Положить `course` в атрибут view и в `get_context_data` (шаблонам нужен
   `{{ course }}`).
3. В `get_queryset` для list дополнительно фильтровать
   `course=self.course` (уже среди «своих» курсов).
4. В Create: в `form_valid` выставить `form.instance.course = self.course`
   (плюс `author` из `AnnouncementAuthorMixin`).

`success_url` после create/update/delete — список объявлений **этого** курса
(`announcement_list` с `course.id`), не общий manage list.

### 3.5. Зачем так

| Без миксинов | С миксинами (как у Course) |
|--------------|----------------------------|
| В каждом view свой `filter(course__owner=…)` | Один `CourseOwnerMixin` |
| В Create и Update дублируется `author = request.user` | Один `AnnouncementAuthorMixin` |
| Легко забыть permission на одном из CRUD | `permission_required` на каждой view, общие настройки в `AnnouncementCourseMixin` |

---

## 4. Вьюшки

Наследование — generic CBV Django **через миксины из §3**, не «голые»
`CreateView` без фильтра владельца.

| Имя view | Цепочка наследования | Назначение |
|----------|----------------------|------------|
| `AnnouncementListView` | `AnnouncementCourseMixin` + `ListView` | Список объявлений курса (CMS) |
| `AnnouncementDetailView` | `AnnouncementCourseMixin` + `DetailView` | Детали в CMS (и черновики) |
| `AnnouncementCreateView` | `AnnouncementEditMixin` + `CreateView` | Создать |
| `AnnouncementUpdateView` | `AnnouncementEditMixin` + `UpdateView` | Редактировать |
| `AnnouncementDeleteView` | `AnnouncementCourseMixin` + `DeleteView` | Удалить |
| `StudentAnnouncementListView` | `LoginRequiredMixin` + `ListView` | Опубликованные для студента |
| `StudentAnnouncementDetailView` *(или общий detail с ветвлением)* | `LoginRequiredMixin` + `DetailView` | Чтение студентом |

**Create (через миксины):**

- курс из URL, проверка `owner`;
- `author` и `course` проставляются в `form_valid` миксинами / view;
- редирект → `announcement_list`.

**Update / Delete:**

- объект попадает в queryset только через `CourseOwnerMixin`
  (`course__owner=request.user`) → чужое объявление = 404;
- редирект → `announcement_list` того же курса.

**Student list / detail:**

- студент в `course.students`;
- только `is_published=True`;
- **без** `CourseOwnerMixin` / `PermissionRequiredMixin` на add/change/delete.

**Форма (поля в UI):** `title`, `body`, `is_published`.  
`course`, `author`, `created`, `updated` в форме не редактируются.

---

## 5. URL (имена и пути)

Префикс CMS — как у остальных manage-маршрутов курса (`courses/urls.py`).  
Студенческие — в `students/urls.py`.

| name | Метод | Путь (пример) | Кто |
|------|-------|---------------|-----|
| `announcement_list` | GET | `/course/<course_id>/announcements/` | преподаватель |
| `announcement_create` | GET, POST | `/course/<course_id>/announcements/create/` | преподаватель |
| `announcement_detail` | GET | `/announcements/<pk>/` | преподаватель / студент* |
| `announcement_edit` | GET, POST | `/announcements/<pk>/edit/` | преподаватель |
| `announcement_delete` | GET, POST | `/announcements/<pk>/delete/` | преподаватель |
| `student_announcement_list` | GET | `/students/course/<course_id>/announcements/` | студент |

\* На `announcement_detail` студент видит только опубликованные; преподаватель — любые своего курса.

---

## 6. Куда интегрировать в UI

### 6.1. CMS — список курсов преподавателя

Файл: `courses/templates/courses/manage/course/list.html`

В блок действий карточки курса добавить ссылку:

- текст: «Объявления»
- url name: `announcement_list`
- аргумент: `course.id`

Рядом с «Редактировать» / «Модули» / «Удалить».

### 6.2. CMS — модули курса (опционально)

Файл: `courses/templates/courses/manage/module/formset.html`

В `page-header` или `actions-row` — ссылка «Объявления курса» → `announcement_list`.

### 6.3. Страница студента — материалы курса

Файл: `students/templates/students/course/detail.html`

Над сайдбаром модулей или в сайдбаре:

- заголовок «Объявления»;
- до 3 последних опубликованных (заголовок + дата);
- ссылка «Все объявления» → `student_announcement_list`;
- клик по заголовку → `announcement_detail`.

Контекст view курса нужно будет дополнить queryset'ом объявлений (это уже Python — в ТЗ только требование).

### 6.4. Шапка сайта

**Не** добавлять отдельный пункт в глобальное меню — объявления живут в контексте курса.

---

## 7. Файлы шаблонов (создать)

```text
courses/templates/courses/manage/announcement/
  list.html      # ListView (CMS)
  form.html      # CreateView + UpdateView
  detail.html    # DetailView (можно общий и для студента)
  delete.html    # DeleteView

students/templates/students/announcement/
  list.html      # StudentAnnouncementListView
```

Ниже — готовая разметка в стиле Educa (`base.html`, классы `page-header`, `card`, `button`, …).

Имена url уже проставлены — после подключения маршрутов шаблоны заработают как есть.

---

## 8. Готовые шаблоны

### 8.1. `courses/templates/courses/manage/announcement/list.html`

```django
{% extends "base.html" %}
{% block title %}Объявления — {{ course.title }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Объявления</h1>
  <p class="page-meta">{{ course.title }}</p>
</div>

<div class="actions-row">
  <a href="{% url 'announcement_create' course.id %}" class="button">Новое объявление</a>
  <a href="{% url 'course_module_update' course.id %}" class="btn btn-secondary">К модулям</a>
  <a href="{% url 'manage_course_list' %}" class="btn btn-secondary">Мои курсы</a>
</div>

{% if object_list %}
<div class="card-grid">
  {% for item in object_list %}
  <article class="course-card">
    <h3>
      <a href="{% url 'announcement_detail' item.id %}">{{ item.title }}</a>
    </h3>
    <p class="course-card-meta">
      {{ item.created|date:"d.m.Y H:i" }}
      {% if not item.is_published %} · <span class="page-meta">черновик</span>{% endif %}
    </p>
    <p>{{ item.body|truncatewords:20 }}</p>
    <div class="course-card-actions">
      <a href="{% url 'announcement_edit' item.id %}" class="btn btn-secondary btn-sm">Редактировать</a>
      <a href="{% url 'announcement_delete' item.id %}" class="btn btn-danger btn-sm">Удалить</a>
    </div>
  </article>
  {% endfor %}
</div>
{% else %}
<div class="card empty-state">
  <p>Объявлений пока нет.</p>
</div>
{% endif %}
{% endblock %}
```

**Контекст:** `object_list` (или `announcement_list`), `course`.

---

### 8.2. `courses/templates/courses/manage/announcement/form.html`

Один шаблон на create и update.

```django
{% extends "base.html" %}
{% block title %}{% if object %}Редактировать объявление{% else %}Новое объявление{% endif %}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{% if object %}Редактировать объявление{% else %}Новое объявление{% endif %}</h1>
  <p class="page-meta">{{ course.title }}</p>
</div>
<div class="card form-card">
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <div class="actions-row">
      <input type="submit" value="Сохранить" class="button">
      <a href="{% url 'announcement_list' course.id %}" class="btn btn-secondary">Отмена</a>
    </div>
  </form>
</div>
{% endblock %}
```

**Контекст:** `form`, `course`, при update ещё `object`.

---

### 8.3. `courses/templates/courses/manage/announcement/detail.html`

```django
{% extends "base.html" %}
{% block title %}{{ object.title }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>{{ object.title }}</h1>
  <p class="page-meta">
    {{ object.course.title }} · {{ object.created|date:"d.m.Y H:i" }}
    {% if object.updated != object.created %}
    · обновлено {{ object.updated|date:"d.m.Y H:i" }}
    {% endif %}
    {% if not object.is_published %} · черновик{% endif %}
  </p>
</div>

<div class="card">
  <div class="content-block">
    {{ object.body|linebreaks }}
  </div>
  <p class="page-meta">Автор: {{ object.author.get_full_name|default:object.author.username }}</p>
</div>

<div class="actions-row">
  {% if request.user == object.course.owner %}
  <a href="{% url 'announcement_edit' object.id %}" class="button">Редактировать</a>
  <a href="{% url 'announcement_delete' object.id %}" class="btn btn-danger">Удалить</a>
  <a href="{% url 'announcement_list' object.course.id %}" class="btn btn-secondary">К списку</a>
  {% else %}
  <a href="{% url 'student_announcement_list' object.course.id %}" class="btn btn-secondary">К списку</a>
  <a href="{% url 'student_course_detail' object.course.id %}" class="btn btn-secondary">К курсу</a>
  {% endif %}
</div>
{% endblock %}
```

---

### 8.4. `courses/templates/courses/manage/announcement/delete.html`

```django
{% extends "base.html" %}
{% block title %}Удалить объявление{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Удалить объявление</h1>
  <p class="page-meta">Это действие нельзя отменить</p>
</div>
<div class="card form-card">
  <p>Удалить объявление «<strong>{{ object.title }}</strong>» курса «{{ object.course.title }}»?</p>
  <form method="post">
    {% csrf_token %}
    <div class="actions-row">
      <input type="submit" value="Да, удалить" class="button btn-danger">
      <a href="{% url 'announcement_list' object.course.id %}" class="btn btn-secondary">Отмена</a>
    </div>
  </form>
</div>
{% endblock %}
```

---

### 8.5. `students/templates/students/announcement/list.html`

```django
{% extends "base.html" %}
{% block title %}Объявления — {{ course.title }}{% endblock %}
{% block content %}
<div class="page-header">
  <h1>Объявления</h1>
  <p class="page-meta">{{ course.title }}</p>
</div>

<div class="actions-row">
  <a href="{% url 'student_course_detail' course.id %}" class="btn btn-secondary">К материалам курса</a>
</div>

{% if object_list %}
{% for item in object_list %}
<div class="card" style="margin-bottom: 1rem;">
  <h3>
    <a href="{% url 'announcement_detail' item.id %}">{{ item.title }}</a>
  </h3>
  <p class="page-meta">{{ item.created|date:"d.m.Y H:i" }}</p>
  <p>{{ item.body|truncatewords:40 }}</p>
  <a href="{% url 'announcement_detail' item.id %}" class="btn btn-secondary btn-sm">Читать</a>
</div>
{% endfor %}
{% else %}
<div class="card empty-state">
  <p>Пока нет объявлений.</p>
</div>
{% endif %}
{% endblock %}
```

---

### 8.6. Фрагмент для вставки в `students/course/detail.html`

Вставить **перед** `<div class="layout-sidebar">` (или внутрь сайдбара — на выбор).

Ожидается переменная контекста `announcements` (queryset опубликованных, например `[:3]`).

```django
{% if announcements %}
<section class="card" style="margin-bottom: 1.25rem;">
  <h2>Объявления</h2>
  <ul class="sidebar-list">
    {% for item in announcements %}
    <li>
      <a href="{% url 'announcement_detail' item.id %}">
        {{ item.title }}
        <span class="page-meta">{{ item.created|date:"d.m.Y" }}</span>
      </a>
    </li>
    {% endfor %}
  </ul>
  <div class="actions-row">
    <a href="{% url 'student_announcement_list' object.id %}" class="btn btn-secondary btn-sm">Все объявления</a>
  </div>
</section>
{% endif %}
```

---

### 8.7. Фрагмент для `courses/manage/course/list.html`

В `course-card-actions` добавить:

```django
<a href="{% url 'announcement_list' course.id %}" class="btn btn-secondary btn-sm">Объявления</a>
```

---

## 9. Критерии приёмки

| ☐ | Проверка |
|---|----------|
| ☐ | Модель с полями из §2, миграция применена |
| ☐ | Есть миксины из §3 (`CourseOwnerMixin`, `AnnouncementAuthorMixin`, `AnnouncementCourseMixin`, `AnnouncementEditMixin`) |
| ☐ | CMS CRUD-views наследуют эти миксины, а не дублируют фильтр владельца |
| ☐ | Instructors имеют permissions `view/add/change/delete_announcement` |
| ☐ | Чужой owner / без login → 404 или 403 на CMS |
| ☐ | Преподаватель: create / list / detail / update / delete работают |
| ☐ | После create/update/delete — редирект на список объявлений курса |
| ☐ | Черновик (`is_published=False`) не виден студенту |
| ☐ | Студент видит список и detail только по курсам, на которые записан |
| ☐ | В CMS list курсов есть ссылка «Объявления» |
| ☐ | На странице материалов студента есть блок объявлений (если есть данные) |
| ☐ | Все шаблоны из §7 существуют и подключены через `template_name` |
| ☐ | Используются generic CBV + миксины, не сырой `View` + ручной CRUD |

---

## 10. Порядок реализации (чеклист)

1. Модель + миграция + выдача permissions группе Instructors.  
2. Миксины §3 (`CourseOwnerMixin` → … → `AnnouncementEditMixin`).  
3. Form / `fields` (`title`, `body`, `is_published`).  
4. CMS views на миксинах + urls + шаблоны list/form/detail/delete.  
5. Ссылка в `manage/course/list.html`.  
6. Student list + detail (без owner-миксинов).  
7. Блок на `students/course/detail.html` + контекст.  
8. Прогнать критерии §9.
