# 2. Display views: шаблоны, списки и объекты

[← Основа](01-base-lifecycle.md) · [Оглавление](README.md) · [Далее: формы и CRUD →](03-forms-and-editing.md)

Display views отвечают за чтение данных. Они не должны менять БД по GET.

## 2.1. `TemplateView`

`TemplateView` — view для статичной или почти статичной страницы. Наследует
`TemplateResponseMixin` и `ContextMixin`.

```python
from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = "pages/about.html"
```

### Поток GET

```text
setup → dispatch → TemplateView.get
      → get_context_data
      → render_to_response
      → TemplateResponse
```

Добавление контекста:

```python
class AboutView(TemplateView):
    template_name = "pages/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["platform_name"] = "Educa"
        context["features"] = ["Курсы", "Квизы", "Сертификаты"]
        return context
```

Не заменяйте `context` новым словарём: `super()` уже мог добавить URL args и
данные другого mixin.

## 2.2. `RedirectView`

`RedirectView` возвращает redirect вместо шаблона.

```python
from django.views.generic import RedirectView


class LegacyCoursesView(RedirectView):
    pattern_name = "course_list"
    permanent = True
```

- `url` — фиксированный URL, например `"/courses/"`.
- `pattern_name` — имя URL, предпочительнее жёсткой строки.
- `permanent=False` — HTTP 302; `True` — HTTP 301.
- `query_string=True` — переносит query parameters.

Динамический URL:

```python
class CourseRedirectView(RedirectView):
    pattern_name = "course_detail"

    def get_redirect_url(self, *args, **kwargs):
        return super().get_redirect_url(slug=kwargs["slug"])
```

## 2.3. `ListView`

`ListView` отображает коллекцию. В Educa это естественный выбор для:

- списка курсов студента;
- списка курсов преподавателя;
- списка объявлений;
- списка сертификатов или результатов.

```python
from django.views.generic import ListView
from courses.models import Course


class CourseListView(ListView):
    model = Course
    template_name = "courses/course/list.html"
```

### Автоматические соглашения

Если задать только `model = Course`, Django использует:

| Что | Значение по умолчанию |
|---|---|
| queryset | `Course.objects.all()` |
| template | `courses/course_list.html` |
| контекст | `object_list`, `course_list` |
| object context | `False` |

Явно задавать `template_name` обычно понятнее.

### Поток GET у `ListView`

```text
setup
→ dispatch
→ BaseListView.get
  → get_queryset()
  → allow_empty проверка
  → get_context_data(object_list=...)
    → добавляет object_list
    → добавляет page_obj/paginator при pagination
  → render_to_response(context)
```

### `get_queryset()` — главный метод списка

Никогда не фильтруйте список в шаблоне. Фильтрация должна быть на уровне SQL:
безопаснее и быстрее.

```python
class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "students/course/list.html"

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)
```

Вариант с query parameter:

```python
class CourseListView(ListView):
    model = Course
    paginate_by = 12

    def get_queryset(self):
        queryset = Course.objects.select_related("subject", "owner")
        subject = self.request.GET.get("subject")
        if subject:
            queryset = queryset.filter(subject__slug=subject)
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset
```

`select_related()` загружает ForeignKey одним SQL JOIN и избегает N+1 в
шаблоне при `course.subject.title`. Для M2M/обратных связей используйте
`prefetch_related()`.

### `queryset` как атрибут: осторожно

Можно написать:

```python
queryset = Course.objects.filter(...)
```

Но QuerySet как атрибут класса может быть вычислен и закеширован неожиданно
при прямом использовании. Если queryset зависит от request/user/URL — всегда
используйте `get_queryset()`.

## 2.4. Контекст и `context_object_name`

По умолчанию шаблон получает `object_list`. Можно дать понятное имя:

```python
class AnnouncementListView(ListView):
    model = Announcement
    context_object_name = "announcements"
```

Шаблон:

```django
{% for announcement in announcements %}
  <h2>{{ announcement.title }}</h2>
{% empty %}
  <p>Пока ничего нет.</p>
{% endfor %}
```

Но `object_list` тоже остаётся доступен. В больших командах полезно выбрать
единый стиль: либо везде `object_list`, либо понятные имена.

## 2.5. `DetailView`

`DetailView` получает **один** объект по URL. В Educa: публичная страница
курса, сертификат, объявление, результат квиза.

```python
from django.views.generic import DetailView
from courses.models import Course


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course/detail.html"
    slug_field = "slug"
```

URL:

```python
path("course/<slug:slug>/", CourseDetailView.as_view(), name="course_detail")
```

### `pk`, `slug`, `pk_url_kwarg`, `slug_url_kwarg`

`SingleObjectMixin.get_object()` ищет объект по параметрам URL:

| URL | Настройка |
|---|---|
| `<int:pk>` | ничего, `pk` распознаётся автоматически |
| `<int:course_id>` | `pk_url_kwarg = "course_id"` |
| `<slug:slug>` + поле `slug` | обычно достаточно `slug_field = "slug"` |
| `<slug:code>` + поле `code` | `slug_field = "code"` и `slug_url_kwarg = "code"` |

Пример сертификата из Educa:

```python
class CertificateDetailView(LoginRequiredMixin, DetailView):
    model = Certificate
    slug_field = "code"
    slug_url_kwarg = "code"

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)
```

Даже зная UUID чужого сертификата, пользователь получит 404: ограничение
выполняется **до** поиска объекта.

### Поток GET у `DetailView`

```text
setup → dispatch → BaseDetailView.get
      → self.object = get_object()
        → get_queryset()
        → фильтр pk/slug
        → get_object_or_404
      → get_context_data(object=self.object)
      → render_to_response
```

После `super().get_context_data()` доступно `self.object`.

```python
class CourseDetailView(DetailView):
    model = Course

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modules_count"] = self.object.modules.count()
        context["related_courses"] = Course.objects.filter(
            subject=self.object.subject
        ).exclude(pk=self.object.pk)[:3]
        return context
```

## 2.6. Безопасность: ограничивайте queryset, а не только шаблон

Плохой вариант:

```python
class CourseDetailView(DetailView):
    model = Course

    def get_context_data(self, **kwargs):
        if self.object.owner != self.request.user:
            # поздно: объект уже найден; логика сложная
            ...
```

Правильный вариант:

```python
class MyCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course

    def get_queryset(self):
        return Course.objects.filter(owner=self.request.user)
```

Так `get_object()` не сможет найти чужой объект. Для приватного ресурса это
обычно предпочтительнее 403: не раскрывается факт существования объекта.

## 2.7. Pagination

Добавьте:

```python
class CourseListView(ListView):
    model = Course
    paginate_by = 10
    page_kwarg = "page"  # это default; можно изменить
```

Запрос `?page=2` добавит в контекст:

| Переменная | Содержимое |
|---|---|
| `paginator` | объект `Paginator` |
| `page_obj` | текущая страница |
| `is_paginated` | есть ли пагинация |
| `object_list` | объекты только текущей страницы |

Шаблон:

```django
{% for course in object_list %}
  <article>{{ course.title }}</article>
{% endfor %}

{% if is_paginated %}
  <nav aria-label="Страницы">
    {% if page_obj.has_previous %}
      <a href="?page={{ page_obj.previous_page_number }}">Назад</a>
    {% endif %}
    <span>Страница {{ page_obj.number }} из {{ paginator.num_pages }}</span>
    {% if page_obj.has_next %}
      <a href="?page={{ page_obj.next_page_number }}">Вперёд</a>
    {% endif %}
  </nav>
{% endif %}
```

### Сохранить фильтры в ссылках

Если есть `?q=django&page=2`, ссылки без `q` потеряют поиск. В контекст
добавьте параметры либо соберите query string в шаблоне/тегах:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["query"] = self.request.GET.get("q", "")
    return context
```

## 2.8. `allow_empty`

По умолчанию пустой список — нормальная страница. Для архива, который не
должен существовать без объектов, можно:

```python
allow_empty = False
```

Тогда `ListView` вернёт 404, когда queryset пуст. Не включайте это для
«Моих курсов»: пустой аккаунт — ожидаемая ситуация.

## 2.9. `get_template_names()`

Используйте, когда шаблон выбирается по типу объекта:

```python
class AnnouncementDetailView(DetailView):
    model = Announcement

    def get_template_names(self):
        if self.request.user == self.object.course.owner:
            return ["courses/manage/announcement/detail.html"]
        return ["students/announcement/detail.html"]
```

Это допустимо, но иногда проще использовать две view с разными queryset и
template_name: так правила доступа виднее.

## 2.10. Частые ошибки display views

| Симптом | Причина | Исправление |
|---|---|---|
| Все курсы видны студенту | нет фильтра `students=request.user` | переопределить `get_queryset()` |
| `DoesNotExist` вместо 404 | ручной `.get()` | использовать `DetailView` / `get_object_or_404` |
| В шаблоне сотни SQL запросов | связанные объекты не оптимизированы | `select_related` / `prefetch_related` |
| Пагинация пропала | перебили `get_context_data` без `super()` | вызвать `super()` |
| URL `course_id` не работает | DetailView ждёт `pk` | указать `pk_url_kwarg` |

## Практика

1. Превратите публичный список курсов в `ListView` с `paginate_by = 6`.
2. Добавьте фильтр `?subject=<slug>`.
3. Добавьте `select_related("subject", "owner")`.
4. Создайте detail view сертификата, доступную только его владельцу.
5. Проверьте URL чужого сертификата в другом браузере: ожидается 404.

## Документация Django

- [Generic display views: `DetailView` и `ListView`](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-display/)
- [Display mixins: `SingleObjectMixin`, multiple object mixins](https://docs.djangoproject.com/en/6.0/ref/class-based-views/mixins-single-object/)
- [Pagination](https://docs.djangoproject.com/en/6.0/topics/pagination/)
- [Оптимизация запросов: `select_related()` и `prefetch_related()`](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#select-related)
