# 8. URLconf и интеграция generic views

[← Шпаргалка](07-reference-cheatsheet.md) · [Оглавление](README.md) · [Далее: реальные рецепты →](09-real-world-recipes.md)

Generic view не существует отдельно от URL. URLconf:

1. извлекает параметры из адреса;
2. передаёт их в `as_view()`;
3. `as_view()` создаёт экземпляр CBV;
4. view использует `self.kwargs` для queryset, формы и redirect.

### Теория: URL — публичный контракт приложения

URL связывает три разных слоя: действие пользователя в template, параметры
предметной области и Python view. Название маршрута (`name="quiz_take"`)
делает этот контракт устойчивым: templates и redirects говорят не «какая
сейчас строка адреса», а «какое действие требуется».

Параметры пути также выражают отношения данных. В
`/students/course/7/module/3/` число 7 не просто украшение: оно задаёт
границу, внутри которой module 3 должен быть найден. Корректная view
проверяет обе части адреса, иначе URL позволяет пересечь границу между
курсами.

Официальная документация: [URL dispatcher](https://docs.djangoproject.com/en/6.0/topics/http/urls/) и [base CBV](https://docs.djangoproject.com/en/6.0/ref/class-based-views/base/).

## 8.1. Базовая связка URL → CBV

```python
# courses/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.CourseListView.as_view(), name="course_list"),
    path("<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
]
```

```python
# educa/urls.py
from django.urls import include, path

urlpatterns = [
    path("course/", include("courses.urls")),
]
```

Итог:

| Адрес | View | URL kwargs |
|---|---|---|
| `/course/` | `CourseListView` | `{}` |
| `/course/12/` | `CourseDetailView` | `{"pk": 12}` |

Внутри `CourseDetailView`:

```python
self.kwargs["pk"]  # 12
```

`DetailView` ожидает `pk` по умолчанию, поэтому дополнительная настройка не
нужна.

## 8.2. Path converters

Встроенные converters:

| Converter | Пример | Подходит для |
|---|---|---|
| `<str:name>` | `python-basics` | короткие строки без `/` |
| `<int:pk>` | `42` | primary key |
| `<slug:slug>` | `python-basics-2026` | SEO URL |
| `<uuid:code>` | `2c219a40-...` | публичные UUID |
| `<path:path>` | `folder/file.pdf` | остаток URL, включая `/` |

### `pk` с другим именем

URL:

```python
path("course/<int:course_id>/", CourseDetailView.as_view())
```

`DetailView` не найдёт `pk`, пока не указать:

```python
class CourseDetailView(DetailView):
    model = Course
    pk_url_kwarg = "course_id"
```

Альтернатива: оставить URL параметр как `<int:pk>`. Это проще, если
предметный смысл имени не важен.

### Slug

```python
path("<slug:slug>/", CourseDetailView.as_view(), name="course_detail")
```

```python
class CourseDetailView(DetailView):
    model = Course
    slug_field = "slug"       # поле модели
    slug_url_kwarg = "slug"   # URL parameter
```

Если имена одинаковы, `slug_url_kwarg` можно не задавать.

## 8.3. URL-паттерны для CRUD

Реальный пример — курс или Announcement:

```python
urlpatterns = [
    path("mine/", CourseListView.as_view(), name="manage_course_list"),
    path("create/", CourseCreateView.as_view(), name="course_create"),
    path("<int:pk>/edit/", CourseUpdateView.as_view(), name="course_edit"),
    path("<int:pk>/delete/", CourseDeleteView.as_view(), name="course_delete"),
]
```

| CRUD | HTTP | URL | CBV | Зачем |
|---|---|---|---|---|
| List | GET | `/course/mine/` | `ListView` | список своих курсов |
| Create form | GET | `/course/create/` | `CreateView` | показать форму |
| Create submit | POST | `/course/create/` | `CreateView` | создать |
| Update form | GET | `/course/12/edit/` | `UpdateView` | показать данные |
| Update submit | POST | `/course/12/edit/` | `UpdateView` | сохранить |
| Delete confirm | GET | `/course/12/delete/` | `DeleteView` | подтвердить |
| Delete submit | POST | `/course/12/delete/` | `DeleteView` | удалить |

Не используйте URL `GET /course/12/delete-now/`: это нарушает безопасную
семантику GET и позволяет поисковым роботам/превью-сервисам вызвать удаление.

## 8.4. Родительский объект в URL

Частая структура: `Course` → `Announcement`, `Course` → `Module`,
`Project` → `Task`, `Organization` → `Member`.

```python
urlpatterns = [
    path(
        "<int:course_id>/announcements/",
        AnnouncementListView.as_view(),
        name="announcement_list",
    ),
    path(
        "<int:course_id>/announcements/create/",
        AnnouncementCreateView.as_view(),
        name="announcement_create",
    ),
    path(
        "announcements/<int:pk>/edit/",
        AnnouncementUpdateView.as_view(),
        name="announcement_edit",
    ),
]
```

### Почему list/create получают `course_id`, а update — `pk`

У list/create Announcement ещё не обязательно существует:

- list должен знать, **какой курс** фильтровать;
- create должен знать, **к какому курсу** привязать объект.

У update/delete объект Announcement уже содержит `announcement.course`, поэтому
достаточно его `pk`. Безопасность обеспечивается:

```python
def get_queryset(self):
    return Announcement.objects.filter(course__owner=self.request.user)
```

### Получение родителя в view

```python
class AnnouncementCreateView(LoginRequiredMixin, CreateView):
    model = Announcement
    fields = ["title", "body", "is_published"]

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course,
            pk=kwargs["course_id"],
            owner=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        form.instance.author = self.request.user
        return super().form_valid(form)
```

`dispatch()` выполняется и для GET формы, и для POST сохранения — нельзя
обойти проверку, отправив POST напрямую.

## 8.5. `reverse()`, `reverse_lazy()` и `{% url %}`

Никогда не собирайте адресы строками:

```python
# Плохо
return redirect(f"/course/{course.id}/")
```

Имя URL — стабильный контракт:

```python
from django.urls import reverse, reverse_lazy

# внутри метода, когда URLconf уже загружен
reverse("course_detail", args=[course.pk])
reverse("course_detail", kwargs={"slug": course.slug})

# при импорте класса
success_url = reverse_lazy("manage_course_list")
```

В шаблоне:

```django
<a href="{% url 'course_detail' course.slug %}">{{ course.title }}</a>
<a href="{% url 'announcement_edit' pk=announcement.pk %}">Изменить</a>
```

### Когда `reverse_lazy`

| Место | Использовать |
|---|---|
| `success_url = ...` как class attribute | `reverse_lazy()` |
| `get_success_url()` | `reverse()` |
| обычный метод `form_valid()` | `reverse()` / `redirect("url_name", ...)` |
| template | `{% url %}` |

## 8.6. Namespaces

Когда приложений много, одинаковые имена (`detail`, `list`, `create`) быстро
конфликтуют. Подключайте namespace.

```python
# courses/urls.py
app_name = "courses"

urlpatterns = [
    path("", CourseListView.as_view(), name="list"),
    path("<slug:slug>/", CourseDetailView.as_view(), name="detail"),
]
```

```python
# root urls.py
path("course/", include("courses.urls")),
```

Использование:

```python
reverse("courses:detail", kwargs={"slug": "python-basics"})
```

```django
{% url 'courses:detail' slug=course.slug %}
```

Если проект уже использует ненеймспейсные `course_detail`, не меняйте всё
одним коммитом без плана: это breaking change для templates, redirect и tests.

## 8.7. `as_view()` с настройками

```python
path(
    "popular/",
    CourseListView.as_view(
        paginate_by=20,
        template_name="courses/course/popular_list.html",
    ),
    name="course_popular",
)
```

Уместно для разных представлений одной и той же простой view. Не передавайте
через `as_view()` бизнес-параметры, зависящие от request/user: такие значения
надо вычислять в методах класса.

## 8.8. URL порядок

Django проверяет `urlpatterns` сверху вниз. Более специфичный путь должен быть
выше общего:

```python
# Правильно
path("create/", CourseCreateView.as_view(), name="course_create"),
path("<slug:slug>/", CourseDetailView.as_view(), name="course_detail"),
```

Иначе `/course/create/` попадёт в slug detail view как `slug="create"`.

## 8.9. Query parameters не становятся `kwargs`

Для:

```text
GET /course/?q=django&page=2
```

данные доступны через:

```python
self.request.GET["q"]
self.request.GET.get("page")
```

Не через `self.kwargs`: kwargs существуют только для path parameters.

## 8.10. Реальный маршрут: доступ студента к материалам

```python
path(
    "course/<int:pk>/module/<int:module_id>/",
    StudentCourseDetailView.as_view(),
    name="student_course_detail_module",
)
```

`pk` — курс, `module_id` — выбранный модуль. View должен проверить обе связи:

```python
def get_queryset(self):
    return Course.objects.filter(students=self.request.user)

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["module"] = get_object_or_404(
        self.object.modules,
        pk=self.kwargs["module_id"],
    )
    return context
```

Важно не делать `Module.objects.get(pk=module_id)` без связи к `self.object`:
так пользователь может передать module другого курса.

## 8.11. Тестирование маршрутов

```python
from django.test import TestCase
from django.urls import resolve, reverse


class UrlTests(TestCase):
    def test_course_detail_url(self):
        url = reverse("course_detail", kwargs={"slug": "python"})
        self.assertEqual(url, "/course/python/")

    def test_course_detail_resolves(self):
        match = resolve("/course/python/")
        self.assertEqual(match.view_name, "course_detail")
```

Тестируйте не только `reverse`, но и фактический request, особенно для
permissions и scopes.

## 8.12. URL checklist

- В URL вызывается `MyView.as_view()`.
- Для DetailView имя URL parameter совпадает с `pk_url_kwarg`/`slug_url_kwarg`.
- Специфичные пути расположены выше динамических.
- Redirect строится через URL name, не через строку.
- При parent-child URL дочерний объект проверяется через родителя.
- Query parameters читаются из `request.GET`.
- Все формы используют POST, удаление — POST confirmation.

## 8.13. URLconf Educa: как найти каждую кнопку и следующий экран

В проекте URLconf разделён не случайно:

| Файл | Для кого | Что подключает |
|---|---|---|
| `educa/urls.py` | весь сайт | root prefixes и include |
| `courses/public_urls.py` | все посетители | каталог и публичные course details |
| `courses/urls.py` | преподаватели | CMS и управление content |
| `students/urls.py` | enrolled students | обучение, тесты, profile |

### Полный пример: кнопка «Пройти тест»

1. Template `students/templates/students/course/detail.html` содержит:

```django
<a href="{% url 'quiz_take' object.id content.object_id %}">
  Пройти тест
</a>
```

2. Django ищет имя `quiz_take` в URLconf:

```python
# students/urls.py
path(
    "course/<int:pk>/quiz/<int:quiz_id>/",
    views.QuizTakeView.as_view(),
    name="quiz_take",
)
```

3. `include("students.urls")` в root URLconf добавляет prefix `/students/`.
4. Итоговая ссылка в HTML: `/students/course/7/quiz/3/`.
5. После клика browser отправляет GET.
6. `QuizTakeView.get(request, pk=7, quiz_id=3)` рендерит quiz form.
7. Submit у template не указывает `action`, поэтому POST идёт **на тот же
   URL** и Django вызывает `QuizTakeView.post`.
8. `post()` redirect-ит на URL name `quiz_result`; browser открывает экран
   результата.

### Почему URL names важнее жёстких адресов

В template не написано:

```django
<a href="/students/course/{{ object.id }}/quiz/{{ content.object_id }}/">
```

Путь может измениться: например, `/students/` станет `/learn/`. При `{% url
'quiz_take' ... %}` вы измените только `path(...)`; все templates и redirects
останутся корректны.

### Локальный приём для проверки

В Django shell:

```bash
python manage.py shell -c "
from django.urls import reverse, resolve
print(reverse('quiz_take', args=[7, 3]))
print(resolve('/students/course/7/quiz/3/').func.view_class)
"
```

Первая строка проверяет generation URL, вторая — что incoming URL ведёт в
нужный CBV class. Это полезно, когда кнопка даёт `NoReverseMatch` или URL
открывает неожиданную view.
