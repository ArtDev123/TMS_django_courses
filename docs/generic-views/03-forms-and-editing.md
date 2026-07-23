# 3. Формы и editing views: `FormView`, Create, Update, Delete

[← Display views](02-display-views.md) · [Оглавление](README.md) · [Далее: mixins и доступы →](04-mixins-auth-permissions.md)

Editing views обрабатывают формы и должны следовать правилу **POST/Redirect/GET**:

```text
GET  → показать форму
POST → проверить и изменить БД
302  → redirect на итоговую страницу
GET  → пользователь видит результат
```

Redirect после успеха предотвращает повторную отправку формы при обновлении
страницы.

### Теория: форма — граница недоверенных данных

HTML form нельзя считать доверенным интерфейсом. Пользователь может изменить
hidden input, убрать `required`, отправить POST вручную или повторить старый
запрос. Поэтому generic editing view не просто «получает поля из template».
Она строит Form/ModelForm, приводит строки к Python-типам, запускает
валидацию, а затем решает, какие значения всё-таки назначает сервер.

`form.cleaned_data` содержит только значения, прошедшие validation. Однако
поля вроде `owner`, `author`, `course` и роли пользователя не должны даже
попадать в пользовательскую форму: они выводятся из request и URL в
`form_valid()`. Такой подход защищает не только конкретный template, но и
любой ручной POST-клиент.

## 3.1. Общая архитектура form views

Важные классы Django:

```text
FormMixin
  ├─ get_form_class()
  ├─ get_form()
  ├─ get_form_kwargs()
  ├─ form_valid()
  ├─ form_invalid()
  └─ get_success_url()

ProcessFormView
  ├─ get()  → render form
  ├─ post() → get_form().is_valid()
  └─ put()  → post()

ModelFormMixin
  ├─ добавляет model / queryset / object
  ├─ строит ModelForm
  └─ сохраняет form в form_valid()

DeletionMixin
  └─ удаляет object при POST
```

`ProcessFormView` сам по себе не предназначен для прямого наследования:
ему нужен `FormMixin` или `ModelFormMixin`.

## 3.2. `FormView`: форма без своей модели

Используйте `FormView`, если действие не создаёт/редактирует одну конкретную
модель:

- вход;
- отправка письма;
- запись на курс;
- фильтр/поиск;
- загрузка CSV;
- расчёт цены.

В Educa `StudentEnrollCourseView` — естественный пример: форма добавляет
пользователя в M2M `Course.students`, но не создаёт объект модели формы.

```python
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import CourseEnrollForm


class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    form_class = CourseEnrollForm
    template_name = "students/course/enroll.html"

    def form_valid(self, form):
        self.course = form.cleaned_data["course"]
        self.course.students.add(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "student_course_detail",
            args=[self.course.id],
        )
```

### Точный поток `FormView`

#### GET

```text
FormView.get
→ get_form()
  → get_form_class()
  → get_form_kwargs()     # initial, prefix; без POST data
  → FormClass(**kwargs)
→ get_context_data(form=form)
→ render_to_response()
```

#### POST

```text
FormView.post
→ get_form()
  → get_form_kwargs()     # data=request.POST, files=request.FILES
→ form.is_valid()
  ├─ True  → form_valid(form)
  └─ False → form_invalid(form)
```

Базовый `FormMixin.form_valid()` делает:

```python
return HttpResponseRedirect(self.get_success_url())
```

Поэтому собственная `form_valid()` обычно должна выполнить бизнес-действие,
затем вызвать `super()`.

## 3.3. `get_form_class()` и `get_form_kwargs()`

### Выбор формы

```python
class AnnouncementCreateView(CreateView):
    model = Announcement
    fields = ["title", "body", "is_published"]
```

Либо отдельный класс формы:

```python
class AnnouncementCreateView(CreateView):
    model = Announcement
    form_class = AnnouncementForm
```

Нельзя одновременно задать `fields` и `form_class`: Django сообщит ошибку,
потому что не ясно, какой источник формы использовать.

### Передача `request.user` в форму

```python
class AnnouncementCreateView(CreateView):
    model = Announcement
    form_class = AnnouncementForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["course"] = self.course
        return kwargs
```

Форма принимает дополнительные аргументы:

```python
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "body", "is_published"]

    def __init__(self, *args, user, course, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.course = course
```

Это нужно, когда выбор полей, их queryset или валидация зависят от текущего
пользователя. Не передавайте `request` в форму без причины: передавайте
конкретные данные, которые ей нужны.

## 3.4. `form_valid()` и `form_invalid()`

### `form_valid()`: изменить объект до save

У `CreateView` и `UpdateView` форма — ModelForm. До `super()` объект доступен
как `form.instance`, но ещё не сохранён.

```python
class CourseCreateView(CreateView):
    model = Course
    fields = ["subject", "title", "slug", "overview"]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
```

Внутри базового `ModelFormMixin.form_valid()`:

```python
self.object = form.save()
return super().form_valid(form)
```

То есть после `super().form_valid(form)` можно ожидать `self.object`, но
response уже создан. Если нужно отправить сигнал/создать связанные объекты
после сохранения, сделайте это до `return`:

```python
def form_valid(self, form):
    response = super().form_valid(form)
    AuditLog.objects.create(
        user=self.request.user,
        action="announcement_created",
        object_id=self.object.pk,
    )
    return response
```

Для нескольких зависимых записей используйте `transaction.atomic()`.

### `form_invalid()`: изменить ответ при ошибке

```python
def form_invalid(self, form):
    messages.error(self.request, "Исправьте ошибки в форме.")
    return super().form_invalid(form)
```

Базовый метод повторно рендерит тот же шаблон и передаёт bound form с
`form.errors`. Не редиректите при невалидной форме: иначе ошибки исчезнут.

## 3.5. `CreateView`

`CreateView` показывает пустую ModelForm на GET и создаёт объект на валидном
POST.

```python
class AnnouncementCreateView(LoginRequiredMixin, CreateView):
    model = Announcement
    fields = ["title", "body", "is_published"]
    template_name = "courses/manage/announcement/form.html"

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

    def get_success_url(self):
        return reverse("announcement_list", args=[self.course.id])
```

### Внутренний поток Create

```text
GET:
BaseCreateView.get
→ self.object = None
→ ProcessFormView.get
→ FormMixin.get_form
→ template

POST:
BaseCreateView.post
→ self.object = None
→ ProcessFormView.post
→ get_form().is_valid()
→ ваш form_valid
→ ModelFormMixin.form_valid
  → self.object = form.save()
  → redirect
```

`self.object = None` важен: CreateView не должен передать существующий объект
в форму, иначе получится update.

### URL и шаблон

```python
path(
    "course/<int:course_id>/announcements/create/",
    AnnouncementCreateView.as_view(),
    name="announcement_create",
)
```

В HTML обязательно CSRF:

```django
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Создать</button>
</form>
```

## 3.6. `UpdateView`

`UpdateView` получает существующий объект и строит форму с его начальными
значениями.

```python
class AnnouncementUpdateView(LoginRequiredMixin, UpdateView):
    model = Announcement
    fields = ["title", "body", "is_published"]
    template_name = "courses/manage/announcement/form.html"

    def get_queryset(self):
        return Announcement.objects.filter(course__owner=self.request.user)

    def get_success_url(self):
        return reverse("announcement_list", args=[self.object.course_id])
```

### Поток Update

```text
GET/POST:
BaseUpdateView.get or post
→ self.object = get_object()
  → get_queryset()        # здесь обязательна проверка owner
  → фильтр pk/slug
→ ProcessFormView.get/post
→ ModelForm(instance=self.object)
→ valid POST: form.save() обновляет тот же объект
```

На UpdateView `form.instance.author = request.user` почти всегда **не нужно**:
автор обычно должен остаться исходным. Если хотите вести редактора, добавьте
отдельное поле `updated_by`.

## 3.7. `success_url` и `get_success_url()`

Способы задать redirect:

```python
success_url = reverse_lazy("manage_course_list")
```

Это удобно, когда URL постоянен. `reverse_lazy()` необходим на уровне класса,
потому что URLconf может быть ещё не загружен при импорте модуля.

Если URL зависит от объекта:

```python
def get_success_url(self):
    return reverse("announcement_list", args=[self.object.course_id])
```

`DeletionMixin` также поддерживает форматирование полей объекта:

```python
success_url = "/course/%(course_id)s/announcements/"
```

Но `reverse()` в `get_success_url()` обычно безопаснее при изменении URL.

## 3.8. `DeleteView`

`DeleteView` показывает страницу подтверждения на GET, удаляет объект только
на POST.

```python
class AnnouncementDeleteView(LoginRequiredMixin, DeleteView):
    model = Announcement
    template_name = "courses/manage/announcement/delete.html"

    def get_queryset(self):
        return Announcement.objects.filter(course__owner=self.request.user)

    def get_success_url(self):
        return reverse("announcement_list", args=[self.object.course_id])
```

Шаблон:

```django
<form method="post">
  {% csrf_token %}
  <p>Удалить «{{ object.title }}»?</p>
  <button type="submit">Да, удалить</button>
  <a href="{% url 'announcement_list' object.course_id %}">Отмена</a>
</form>
```

### Важное отличие Django 6.0

Не определяйте бизнес-логику в `delete()` для обычной HTML `DeleteView`.
Современный `BaseDeleteView` обрабатывает POST через `form_valid()`. Если
переопределить только `delete()`, логика может не вызваться при POST.

Правильный вариант:

```python
class AnnouncementDeleteView(DeleteView):
    def form_valid(self, form):
        messages.success(self.request, "Объявление удалено.")
        return super().form_valid(form)
```

`form_valid()` у BaseDeleteView:

1. вычисляет success URL;
2. удаляет `self.object`;
3. возвращает redirect.

## 3.9. Загрузка файлов

Форма:

```django
<form method="post" enctype="multipart/form-data">
  {% csrf_token %}
  {{ form.as_p }}
  <button>Сохранить</button>
</form>
```

Без `enctype="multipart/form-data"` `request.FILES` будет пустым, и
`FileField`/`ImageField` не получат файл. `FormMixin.get_form_kwargs()`
автоматически передаёт `request.FILES` для POST/PUT.

## 3.10. Поля, которые нельзя принимать от пользователя

Не добавляйте `owner`, `author`, `course`, `is_staff` в `fields`, если их
значение должно определять приложение.

Плохо:

```python
fields = ["course", "author", "title", "body"]
```

Пользователь сможет подставить id чужого курса или автора.

Правильно:

```python
fields = ["title", "body", "is_published"]

def form_valid(self, form):
    form.instance.course = self.course
    form.instance.author = self.request.user
    return super().form_valid(form)
```

## 3.11. Когда нужна ручная `post()`

Не для обычной формы. Нужна, если протокол не совпадает с FormView:

```python
class ModuleOrderView(LoginRequiredMixin, View):
    def post(self, request):
        payload = json.loads(request.body)
        # проверить JSON и обновить порядок
        return JsonResponse({"status": "ok"})
```

Это действие AJAX/JSON, а не HTML ModelForm — `FormView` здесь лишний.

## 3.12. Чеклист editing views

- GET не меняет БД.
- Любая HTML POST-форма содержит `{% csrf_token %}`.
- POST успеха всегда заканчивается redirect.
- `form_valid()` вызывает `super()`.
- Поля owner/course/author назначает сервер.
- Update/Delete ограничивают `get_queryset()` владельцем.
- В DeleteView удаление происходит по POST, не ссылкой GET.
- Для зависимых сохранений используется транзакция.

## 3.13. Интеграция editing views с экранами Educa

### `CreateView`: кнопка «Создать курс»

**Где на сайте:** преподаватель → header «Преподавание» →
`/course/mine/` → кнопка «Создать курс».

Кнопка находится в
`courses/templates/courses/manage/course/list.html`:

```django
<a href="{% url 'course_create' %}" class="button">
  Создать курс
</a>
```

Она отправляет **GET** на `/course/create/`. Это не создаёт объект — только
показывает пустую форму:

```text
GET /course/create/
→ CourseCreateView
→ LoginRequiredMixin: teacher залогинен?
→ PermissionRequiredMixin: есть courses.add_course?
→ CreateView.get
→ ModelForm без instance
→ courses/manage/course/form.html
→ HTTP 200
```

Форма в `courses/manage/course/form.html`:

```django
<form method="post">
  {{ form.as_p }}
  {% csrf_token %}
  <input type="submit" value="Сохранить">
</form>
```

После нажатия «Сохранить» браузер делает POST **на тот же URL**:

```text
POST /course/create/
→ CourseCreateView.post
→ form = ModelForm(request.POST)
→ form.is_valid()
  ├─ errors: form_invalid → HTML 200 с errors
  └─ valid:
     → OwnerEditMixin.form_valid
       → form.instance.owner = request.user
     → ModelFormMixin.form_valid
       → self.object = form.save()
     → FormMixin.form_valid
       → HTTP 302 /course/mine/
→ Browser GET /course/mine/
```

`owner` не выводится в `{{ form.as_p }}`. Это важно: преподаватель не может
через браузер подставить чужой owner. Сервер назначает его перед `form.save()`.

### `UpdateView`: кнопка «Редактировать»

**Где на сайте:** `/course/mine/` → карточка курса → «Редактировать».

```django
<a href="{% url 'course_edit' course.id %}">
  Редактировать
</a>
```

Экран использует **тот же** `course/form.html`, но `UpdateView` передаёт
существующий `object`; поэтому заголовок template переключается:

```django
{% if object %}
  Редактировать курс
{% else %}
  Создать курс
{% endif %}
```

До GET/POST формы UpdateView находит course через owner-scoped queryset.
Это означает, что URL `/course/999/edit/` под чужим teacher вернёт 404
ещё до создания формы.

### `DeleteView`: две разные стадии

**Где на сайте:** `/course/mine/` → «Удалить».

```text
GET /course/7/delete/
→ DeleteView.get
→ получает Course из owner queryset
→ показывает courses/manage/course/delete.html
→ объект ещё существует

POST /course/7/delete/
→ BaseDeleteView.form_valid
→ object.delete()
→ redirect /course/mine/
```

Template confirmation явно использует POST:

```django
<form method="post">
  {% csrf_token %}
  <input type="submit" value="Да, удалить">
</form>
```

На сайте это делает кнопку «Отмена» безопасной link-навигацией, а
«Да, удалить» — единственным действием, которое изменит БД.

### `FormView`: запись студента

**Где на сайте:** details публичного курса → «Записаться на курс».

Это уже описано в §3.2, но важно увидеть интеграцию: форма создаётся
`CourseDetailView`, а обрабатывается `StudentEnrollCourseView`. Это нормально:
одна view подготавливает экран, другая обслуживает конкретное POST-действие.

### Проверка вручную

1. Откройте DevTools → Network.
2. Teacher: откройте create course, отправьте пустую форму — увидите POST 200
   и errors; объект не создастся.
3. Отправьте валидную форму — увидите POST 302, затем GET `/course/mine/`.
4. Нажмите Edit, измените title, отправьте форму.
5. Нажмите Delete: GET показывает confirmation; только POST удаляет course.

Это лучший способ увидеть отличие `form_invalid` (200) от `form_valid` (302).

## Документация Django

- [Generic editing views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-editing/)
- [Editing mixins: `FormMixin`, `ModelFormMixin`, `DeletionMixin`](https://docs.djangoproject.com/en/6.0/ref/class-based-views/mixins-editing/)
- [Работа с forms](https://docs.djangoproject.com/en/6.0/topics/forms/)
- [CSRF protection](https://docs.djangoproject.com/en/6.0/howto/csrf/)
- [Database transactions и `on_commit()`](https://docs.djangoproject.com/en/6.0/topics/db/transactions/)
