# 4. Mixins, авторизация, permissions и ownership

[← Формы и CRUD](03-forms-and-editing.md) · [Оглавление](README.md) · [Далее: date views →](05-date-views.md)

## 4.1. Что такое mixin

Mixin — маленький класс, который добавляет один аспект поведения другому
классу. Он не является готовой страницей. В CBV mixins обычно расширяют:

- `dispatch()` — аутентификация, permissions, проверка родителя;
- `get_queryset()` — scope данных;
- `get_context_data()` — общий контекст;
- `form_valid()` — серверные поля объекта;
- `get_form_kwargs()` — request-dependent данные в форму.

### Теория: mixin — политика, а не склад кода

Хороший mixin выражает одно правило, которое не зависит от конкретной
страницы: «пользователь должен быть залогинен», «в queryset остаются только
owner-объекты», «новый объект получает автора». Благодаря этому одна политика
применяется одинаково к списку, detail, update и delete.

Плохой mixin превращается в мини-framework внутри проекта: он создаёт формы,
выбирает templates, делает redirects и знает детали нескольких моделей.
Такой класс трудно читать через MRO и опасно переиспользовать. Если правило
нельзя объяснить одним предложением, его лучше оставить явным кодом в view
или вынести в service.

Пример для курсов Educa:

```python
class OwnerQuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)


class OwnerAssignMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
```

Их можно соединить:

```python
class CourseUpdateView(
    OwnerQuerySetMixin,
    OwnerAssignMixin,
    LoginRequiredMixin,
    UpdateView,
):
    model = Course
    fields = ["subject", "title", "slug", "overview"]
```

Но для update менять owner обычно не надо; `OwnerAssignMixin` логичнее на
CreateView. Разделяйте read-scope и write-assignment.

## 4.2. Порядок наследования

Общее правило:

```python
class MyView(
    AccessMixin,
    DomainMixin,
    GenericView,
):
    ...
```

То есть **ваши mixins и auth mixins слева**, `ListView`/`CreateView`/`View`
справа.

Проверьте:

```python
for cls in MyView.__mro__:
    print(cls.__name__)
```

Если mixin не срабатывает — первым делом смотрите MRO и наличие `super()`.

## 4.3. `LoginRequiredMixin`

```python
from django.contrib.auth.mixins import LoginRequiredMixin


class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
```

Что происходит:

1. `LoginRequiredMixin.dispatch()` проверяет `request.user.is_authenticated`;
2. гость получает redirect на `settings.LOGIN_URL`;
3. исходный URL сохраняется в query parameter `next`;
4. залогиненный пользователь идёт дальше по MRO.

Настройки:

```python
class PrivateView(LoginRequiredMixin, TemplateView):
    login_url = "/accounts/login/"
    redirect_field_name = "next"
```

Обычно лучше задать `LOGIN_URL` глобально в `settings.py`, а не повторять URL
в каждой view.

## 4.4. `PermissionRequiredMixin`

Проверяет стандартные или пользовательские Django permissions.

```python
from django.contrib.auth.mixins import PermissionRequiredMixin


class CourseCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    permission_required = "courses.add_course"
    model = Course
    fields = ["subject", "title", "slug", "overview"]
```

Стандартные permissions создаются для каждой модели при migrate:

```text
courses.add_course
courses.change_course
courses.delete_course
courses.view_course
```

По умолчанию пользователь без permission получает 403. Атрибуты:

| Атрибут | Назначение |
|---|---|
| `permission_required` | строка или iterable строк permissions |
| `raise_exception` | 403 вместо redirect для неавторизованного пользователя |
| `login_url` | override login URL |
| `permission_denied_message` | текст для `PermissionDenied` |

Несколько разрешений:

```python
permission_required = [
    "courses.change_course",
    "courses.view_course",
]
```

Пользователь должен иметь **все** перечисленные permissions.

### Группы

В Educa преподавателей удобно держать в группе `Instructors` и выдать ей:

- `courses.view_course`, `add_course`, `change_course`, `delete_course`;
- соответствующие права для `Announcement`;
- права на управляемые модели, если они нужны в CMS.

Пользователь получает group permissions через `user.has_perm(...)` без
копирования каждого права каждому user.

## 4.5. Permission не равен ownership

Permission отвечает на вопрос: «разрешено ли пользователю вообще создавать/
изменять **модель**?»

Ownership отвечает: «разрешено ли ему изменить **именно этот объект**?»

Оба слоя нужны:

```python
class OwnerCourseMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)


class CourseUpdateView(
    OwnerCourseMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Course
    permission_required = "courses.change_course"
```

Если оставить только permission, преподаватель A с `change_course` сможет
угадать `/course/999/edit/` и изменить курс преподавателя B.

## 4.6. 403 или 404

| Сценарий | Обычно лучше |
|---|---|
| Гость открывает приватную страницу | redirect login |
| Залогиненный без роли пытается открыть CMS | 403 |
| Пользователь знает id чужого приватного объекта | 404 через scoped queryset |
| Админ API с явно запрещённым действием | 403 |

Для object ownership используйте scoped `get_queryset()`: это компактнее,
не раскрывает существование объекта и одинаково защищает Detail/Update/Delete.

## 4.7. `UserPassesTestMixin`

Используется, когда проверка не выражается одной permission:

```python
from django.contrib.auth.mixins import UserPassesTestMixin


class CourseOwnerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        course = self.get_object()
        return course.owner_id == self.request.user.id
```

Но здесь легко дважды запросить объект: один раз в `test_func`, второй — в
`DetailView`. Для ownership чаще эффективнее `get_queryset`.

`UserPassesTestMixin` хорошо подходит для условий без object lookup:

```python
class StaffOnlyView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_staff
```

Не складывайте несколько `UserPassesTestMixin` с ожиданием, что все
`test_func()` будут автоматически вызываться: из-за MRO это часто работает
не так, как ожидают. Создайте один mixin с объединённым условием либо
используйте permissions.

## 4.8. Общий mixin для курса из URL

Если много views имеют `<int:course_id>`, повторяющаяся проверка оправдывает
небольшой mixin:

```python
class OwnedCourseFromUrlMixin:
    course_url_kwarg = "course_id"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course,
            pk=kwargs[self.course_url_kwarg],
            owner=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course"] = self.course
        return context
```

Используйте mixin, если он применяется минимум в двух-трёх местах. Если
проверка нужна только CreateView, явный `dispatch()` внутри view часто
проще читать.

## 4.9. Mixins для `form_valid()`

```python
class AuthorAssignMixin:
    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
```

Этот mixin уместен на CreateView. Для UpdateView он перезапишет автора при
каждом редактировании. Выберите одно:

```python
class AnnouncementCreateView(AuthorAssignMixin, CreateView):
    ...
```

или добавьте `updated_by` в модель и присваивайте именно его при update.

## 4.10. `AccessMixin` и собственный отказ

`LoginRequiredMixin`, `PermissionRequiredMixin`, `UserPassesTestMixin`
наследуют `AccessMixin`. Если нужен особый ответ:

```python
from django.core.exceptions import PermissionDenied


class PaidCourseMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.profile.has_subscription:
            raise PermissionDenied("Нужна подписка.")
        return super().dispatch(request, *args, **kwargs)
```

Не возвращайте template с HTTP 200 для отказа: браузер и monitoring будут
считать запрос успешным. Используйте 302/403/404 по смыслу.

## 4.11. CSRF и доступ — разные защиты

- `LoginRequiredMixin` — кто пользователь.
- `PermissionRequiredMixin` — есть ли модельное право.
- scoped queryset — имеет ли доступ к объекту.
- `{% csrf_token %}` / `CsrfViewMiddleware` — форма действительно отправлена
  со страницы вашего сайта.

Один механизм не заменяет другой.

## 4.12. Практический стек Educa

Для CRUD объявления:

```text
AnnouncementListView:
  LoginRequiredMixin
  PermissionRequiredMixin
  CourseOwnerQuerySetMixin
  ListView

AnnouncementCreateView:
  LoginRequiredMixin
  PermissionRequiredMixin
  OwnedCourseFromUrlMixin (или явный dispatch)
  AuthorAssignMixin
  CreateView

AnnouncementUpdate/DeleteView:
  LoginRequiredMixin
  PermissionRequiredMixin
  CourseOwnerQuerySetMixin
  UpdateView / DeleteView
```

Набор можно упростить объединяющими миксинами, но не теряйте ясность:
один mixin — одна причина существования.

## 4.13. Чеклист безопасности

- `LoginRequiredMixin` находится слева.
- Модельные permissions выданы группе.
- Detail/Update/Delete имеют scoped queryset.
- `course`, `owner`, `author` не входят в пользовательские `fields`.
- Create получает родителя из URL через `get_object_or_404`.
- Проверка доступа одинаково работает на GET и POST.
- При добавлении mixin проверен `__mro__`.

## 4.14. Где mixins работают в Educa

### Экран CMS преподавателя

**Где на сайте:** header → «Преподавание» → `/course/mine/`.

Этот URL вызывает `ManageCourseListView`, который использует общий стек:

```python
class OwnerCourseMixin(
    OwnerMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
):
    model = Course
    fields = ["subject", "title", "slug", "overview"]
```

```python
class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = "courses/manage/course/list.html"
    permission_required = "courses.view_course"
```

На одном URL mixins отвечают за разные вопросы:

| Шаг | Кто выполняет | Что проверяется | Что увидит пользователь |
|---|---|---|---|
| 1 | `LoginRequiredMixin` | есть ли session | гость → login URL |
| 2 | `PermissionRequiredMixin` | есть ли `courses.view_course` | нет права → 403 |
| 3 | `OwnerMixin.get_queryset` | course.owner = текущий teacher | только свои course cards |
| 4 | `ListView` | как получить/отрендерить коллекцию | HTML списка |

Это не четыре независимых запроса. Это один GET, но MRO собирает общий
конвейер поведения в одном instance view.

### Почему `OwnerMixin` важен на экране Update/Delete

На `/course/<pk>/edit/` и `/course/<pk>/delete/` пользователь уже знает
primary key из ссылки или может набрать его вручную. Permission сам по себе не
защищает объект:

```text
teacher A имеет courses.change_course
teacher B имеет courses.change_course
course 17 принадлежит A
```

Без `OwnerMixin` B сможет открыть `/course/17/edit/`. С ним `get_queryset`
становится:

```python
Course.objects.filter(owner=request.user)
```

и `Detail/Update/Delete` не находят course 17 для B → 404.

### Где проверить permissions локально

1. В admin создайте group `Instructors`.
2. Выдайте `courses | course | Can view/add/change/delete course`.
3. Добавьте teacher в эту group.
4. Войдите teacher и откройте `/course/mine/`.
5. Уберите `view_course` у group, обновите страницу — ожидается 403.
6. Верните permission, войдите вторым teacher и вручную откройте чужой edit
   URL — ожидается 404.

Так в браузере видно различие:

```text
403 = модельное право запрещено
404 = объект не входит в разрешённый queryset
```

### Когда создавать новый mixin для сайта

Создавайте его, если одинаковое правило реально появляется на нескольких
экранах. Например, будущие Announcement views:

```text
CMS announcement list
CMS announcement edit
CMS announcement delete
```

все должны видеть только:

```python
Announcement.objects.filter(course__owner=self.request.user)
```

Тогда `CourseOwnerQuerySetMixin` уменьшает копипасту. Если правило нужно
только на одной CreateView, явный `dispatch()` внутри неё будет понятнее.

## Документация Django

- [Authentication и authorization](https://docs.djangoproject.com/en/6.0/topics/auth/default/)
- [`LoginRequiredMixin`, `PermissionRequiredMixin`, `UserPassesTestMixin`](https://docs.djangoproject.com/en/6.0/topics/auth/default/#the-loginrequiredmixin-mixin)
- [Permissions и groups](https://docs.djangoproject.com/en/6.0/topics/auth/default/#permissions-and-authorization)
- [Security checklist](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/)
