# 9. Реальные сценарии generic views

[← URLconf и интеграция](08-urls-and-integration.md) · [Оглавление](README.md)

Эта глава показывает не «абстрактный список объектов», а типичные задачи
продуктов: каталог, личный кабинет, блог, dashboard, файл, multi-tenant
система. Для каждого сценария — подходящая view, URL и точка расширения.

### Теория: view выбирается по форме взаимодействия

При выборе CBV не начинайте с модели. Один и тот же Course участвует в
нескольких взаимодействиях: в каталоге это карточка списка, в public details
это один объект, в CMS — редактируемая форма, в student area — приватный
ресурс. Базовый класс определяется тем, какой HTTP-диалог нужен
пользователю, а не тем, из какой таблицы пришли данные.

Поэтому `DetailView` и `UpdateView` могут работать с одной моделью, но
иметь принципиально разные permissions, template и жизненный цикл. Модель
задаёт данные, view задаёт сценарий.

## 9.1. Интернет-каталог: фильтры, поиск, пагинация

**Продуктовая задача:** студент открывает каталог курсов, выбирает subject,
ищет «Django», листает страницы.

```python
class CatalogView(ListView):
    model = Course
    template_name = "courses/course/list.html"
    context_object_name = "courses"
    paginate_by = 12

    def get_queryset(self):
        queryset = Course.objects.select_related("subject", "owner")

        subject_slug = self.kwargs.get("subject")
        if subject_slug:
            queryset = queryset.filter(subject__slug=subject_slug)

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(title__icontains=query)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subjects"] = Subject.objects.all()
        context["query"] = self.request.GET.get("q", "")
        return context
```

```python
urlpatterns = [
    path("", CatalogView.as_view(), name="course_list"),
    path("subject/<slug:subject>/", CatalogView.as_view(), name="course_list_by_subject"),
]
```

**Почему `ListView`:** читает набор объектов; `get_queryset` естественно
объединяет URL filter и query string.

**Production-детали:**

- добавляйте индекс в БД, если фильтруете по полям часто;
- используйте `select_related` для FK в карточке;
- не подставляйте `request.GET` в ORM без whitelist параметров;
- при сложном поиске используйте PostgreSQL full-text search, а не цепочку
  десятков `icontains`.

## 9.2. Публичная страница + приватная страница одного ресурса

**Задача:** курс виден в каталоге всем, материалы — только записанному
студенту.

```python
class PublicCourseDetailView(DetailView):
    model = Course
    slug_field = "slug"
    template_name = "courses/course/detail.html"


class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "students/course/detail.html"

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)
```

```python
urlpatterns = [
    path("course/<slug:slug>/", PublicCourseDetailView.as_view(), name="course_detail"),
    path(
        "students/course/<int:pk>/",
        StudentCourseDetailView.as_view(),
        name="student_course_detail",
    ),
]
```

Не пытайтесь спрятать материалы одним `{% if user in course.students %}`:
данные уже попадут в template context. Разделяйте queryset и URL.

## 9.3. Панель «Мои объекты»: ownership + permission

**Задача:** преподаватель видит собственные курсы и может редактировать их.

```python
class OwnerCourseQuerySetMixin:
    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class ManageCourseListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OwnerCourseQuerySetMixin,
    ListView,
):
    permission_required = "courses.view_course"
    model = Course
    template_name = "courses/manage/course/list.html"
```

```python
path("course/mine/", ManageCourseListView.as_view(), name="manage_course_list")
```

**Жизненный смысл:** permission даёт право использовать CMS, queryset
ограничивает конкретные объекты. Это стандартный паттерн для:

- авторов статей;
- продавцов маркетплейса;
- менеджеров проектов;
- сотрудников организаций;
- пользователей личного кабинета.

## 9.4. Create с родительским объектом

**Задача:** преподаватель создаёт модуль в своём курсе.

```python
class ModuleCreateView(LoginRequiredMixin, CreateView):
    model = Module
    fields = ["title", "description"]
    template_name = "courses/manage/module/form.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course,
            pk=kwargs["course_id"],
            owner=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("course_module_update", args=[self.course.id])
```

```python
path(
    "course/<int:course_id>/modules/create/",
    ModuleCreateView.as_view(),
    name="module_create",
)
```

**Правило:** parent ID приходит из URL и проверяется сервером; не отдавайте
поле `course` пользователю через form.

## 9.5. Редактирование с черновиком и публикацией

**Задача:** преподаватель создаёт черновик Announcement; студент видит только
опубликованное.

```python
class AnnouncementUpdateView(LoginRequiredMixin, UpdateView):
    model = Announcement
    fields = ["title", "body", "is_published"]

    def get_queryset(self):
        return Announcement.objects.filter(
            course__owner=self.request.user
        )
```

Студенческая лента:

```python
class StudentAnnouncementListView(LoginRequiredMixin, ListView):
    model = Announcement

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course,
            pk=kwargs["course_id"],
            students=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Announcement.objects.filter(
            course=self.course,
            is_published=True,
        )
```

Это более надёжно, чем фильтр `{% if announcement.is_published %}` в
template: черновик не загружается из БД для студента.

## 9.6. Dashboard: несколько наборов данных

**Задача:** личная страница студента показывает курсы, сертификаты, бейджи,
ближайшие объявления.

```python
class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "students/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["courses"] = user.courses_joined.select_related("subject")[:5]
        context["certificates"] = user.certificates.select_related("course")[:5]
        context["badges"] = user.user_badges.select_related("badge")[:5]
        context["announcements"] = Announcement.objects.filter(
            course__students=user,
            is_published=True,
        ).select_related("course")[:5]
        return context
```

**Почему `TemplateView`, а не `ListView`:** нет одного главного queryset.
Если попытаться использовать ListView, один список окажется в `object_list`,
а остальные данные всё равно придётся добавлять вручную.

## 9.7. Файл: download с проверкой доступа

**Задача:** студент может скачать File content только в курсе, куда записан.

```python
from django.http import FileResponse
from django.views import View


class CourseFileDownloadView(LoginRequiredMixin, View):
    def get(self, request, file_id):
        file_item = get_object_or_404(
            File,
            pk=file_id,
            content__module__course__students=request.user,
        )
        return FileResponse(
            file_item.file.open("rb"),
            as_attachment=True,
            filename=file_item.file.name,
        )
```

**Почему не generic display view:** ответ — бинарный файл, не HTML template.
Обычный `View` лучше выражает протокол.

## 9.8. Multi-tenant SaaS

**Задача:** в продукте есть Organization → Project → Task. Пользователь
никогда не должен видеть данные чужой организации.

```python
class OrganizationScopeMixin:
    def get_queryset(self):
        return super().get_queryset().filter(
            organization__members=self.request.user
        )


class TaskUpdateView(
    LoginRequiredMixin,
    OrganizationScopeMixin,
    UpdateView,
):
    model = Task
    fields = ["title", "status", "assignee"]
```

Для Create parent organization тоже надо получить и проверить в `dispatch`.
Не доверяйте hidden `<input name="organization">`: пользователь может
изменить его в DevTools.

## 9.9. API versus generic HTML view

| Нужен ответ | Предпочтительный инструмент |
|---|---|
| HTML список/форма | Django generic CBV |
| JSON endpoint маленького действия | `View` + `JsonResponse` |
| REST CRUD API | Django REST Framework `GenericAPIView`/ViewSet |
| SSE/WebSocket | ASGI/Channels, не `ListView` |
| CSV/PDF/file response | `View`/`FileResponse`/StreamingHttpResponse |

Не заставляйте `ListView` возвращать JSON только потому, что он умеет
`get_queryset()`: для API другие соглашения об ошибках, сериализации,
аутентификации и pagination.

## 9.10. Search form, которая не изменяет БД

Если поиск отправляется GET, `FormView` обычно не нужен:

```html
<form method="get">
  <input name="q" value="{{ request.GET.q }}">
  <button>Найти</button>
</form>
```

Логика в `ListView.get_queryset()`. GET делает URL ссылочным, поэтому поиск
можно копировать, добавлять в закладки и отдавать поисковику.

`FormView` нужен, если форма сама имеет сложную валидацию и отдельный
результат, но для одного query parameter это избыточно.

## 9.11. Внешнее действие после сохранения

**Задача:** после создания объявления отправить email студентам.

```python
from django.db import transaction


class AnnouncementCreateView(CreateView):
    ...
    def form_valid(self, form):
        response = super().form_valid(form)
        transaction.on_commit(
            lambda: notify_students_about_announcement(self.object.pk)
        )
        return response
```

`transaction.on_commit()` запускает уведомление только после успешного commit.
Без него email может уйти, а транзакция позже откатится — студент получит
ссылку на несуществующее объявление.

В production тяжёлую рассылку лучше отправлять в очередь задач (Celery/RQ),
не выполнять во время HTTP request.

## 9.12. Как выбрать точку расширения: реальные вопросы

| Вопрос | Метод/инструмент |
|---|---|
| «Какие строки SQL вообще доступны?» | `get_queryset()` |
| «Какие данные показать рядом с объектом?» | `get_context_data()` |
| «Какая форма нужна текущему user?» | `get_form_class()` |
| «Как передать курс в форму?» | `get_form_kwargs()` |
| «Как записать owner до save?» | `form_valid()` |
| «Куда редиректить после save?» | `get_success_url()` |
| «Как получить parent из URL для GET и POST?» | `dispatch()` |
| «Нужен JSON/file, не HTML?» | `View`, не generic template view |

## 9.13. Production review перед merge

1. Проверить, что queryset не раскрывает чужие данные.
2. Проверить guest, member, owner и admin отдельными tests.
3. Проверить direct POST без открытия формы.
4. Проверить upload и CSRF.
5. Проверить N+1 на списке.
6. Проверить redirect URL после create/update/delete.
7. Проверить, что пользовательские поля не дают менять owner/role/tenant.
8. Проверить пользовательские ошибки формы и 404/403 страницы.

## 9.14. Как переносить production-рецепт в экран Educa

Каждый рецепт сначала нужно связать с конкретным пользователем и кнопкой,
иначе generic view останется кодом без интерфейса.

### Пример: будущие объявления курса

**Роль:** преподаватель.  
**Точка входа на сайте:** `/course/mine/` → рядом с кнопками
«Редактировать / Модули / Удалить» добавить «Объявления».  
**Template:** `courses/templates/courses/manage/course/list.html`.

```django
<a href="{% url 'announcement_list' course.id %}">
  Объявления
</a>
```

Полная цепочка:

```text
Teacher clicks «Объявления»
→ GET /course/<course_id>/announcements/
→ AnnouncementListView.get_queryset()
  → Announcement.objects.filter(course=<course>, course__owner=request.user)
→ announcement list template
→ Teacher clicks «Новое объявление»
→ GET create form
→ POST same create URL
→ form_valid assigns course + author
→ form.save()
→ 302 back to announcement list
```

**Студенческий экран:** `/students/course/<id>/` может показывать три
последних published announcements над module content. Link «Все объявления»
ведёт на `StudentAnnouncementListView`, где queryset обязан иметь:

```python
Announcement.objects.filter(
    course__students=request.user,
    is_published=True,
)
```

Пользовательский эффект: teacher видит черновики и actions, student —
только опубликованный текст без edit/delete buttons.

### Пример: dashboard recipe

В §9.6 предложен `StudentDashboardView(TemplateView)`.

**Где разместить:** header после «Мои курсы» или сделать `/students/profile/`
dashboard-страницей.  
**Что будет видно:** ближайшие announcements, прогресс, certificate, badge.  
**Почему TemplateView:** один экран объединяет несколько источников данных;
нет честного единственного `object_list`.

До добавления view нужно последовательно сделать:

```text
1. path("dashboard/", StudentDashboardView.as_view(), name="student_dashboard")
2. link в base.html через {% url 'student_dashboard' %}
3. students/dashboard.html
4. get_context_data с select_related/prefetch_related
5. ручной GET test + assertion template/context
```

Так рецепт становится пользовательской функцией, а не изолированным классом.
