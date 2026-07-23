# 11. Educa: аннотированный разбор реальных views

[← Локальный ручной прогон](10-local-educa-walkthrough.md) · [Оглавление](README.md)

Это не новый абстрактный пример. Здесь разобраны views, которые уже есть в
Educa: что означает каждая строка, когда Django вызывает метод, что к этому
моменту лежит в `self` и какой экран сайта получает пользователь.

### Теория: читать CBV нужно по времени, а не по расположению строк

Файл `views.py` читается сверху вниз, но request не исполняет код в таком
порядке. Сначала URL создаёт instance, затем access mixins могут завершить
запрос раньше, затем базовый generic class получает данные, и только потом
вызывается переопределённый разработчиком метод. Наконец template создаёт
следующий URL через ссылку или form.

Поэтому у каждого разбора ниже есть три перспективы: код view, HTML экрана и
HTTP timeline. Только вместе они объясняют, почему `self.object` существует
в `get_context_data`, почему `form_valid` получает валидные данные и почему
redirect вызывает новую view.

Для ручной проверки запускайте:

```bash
source .venv/bin/activate
python manage.py runserver
```

И держите рядом:

- браузер с DevTools → Network;
- терминал runserver;
- `courses/views.py` и `students/views.py`;
- соответствующий template из каждого раздела.

## 11.1. Публичный каталог: `CourseListView`

### Где используется на сайте

| Пользователь | Экран / кнопка | URL |
|---|---|---|
| Гость или студент | главная страница | `/` |
| Гость или студент | subject «Programming» в sidebar | `/subject/programming/` |

Кнопки/ссылки расположены в:
`courses/templates/courses/course/list.html`.

```django
<a href="{% url 'course_list' %}">Все курсы</a>
<a href="{% url 'course_list_subject' s.slug %}">
  {{ s.title }}
</a>
```

### Код

```python
class CourseListView(TemplateResponseMixin, View):
    template_name = "courses/course/list.html"

    def get(self, request, subject=None):
        subjects = Subject.objects.annotate(
            total_courses=Count("courses")
        )
        courses = Course.objects.annotate(
            total_modules=Count("modules")
        )
        current_subject = None
        if subject:
            current_subject = get_object_or_404(Subject, slug=subject)
            courses = courses.filter(subject=current_subject)
        return self.render_to_response({
            "subjects": subjects,
            "subject": current_subject,
            "courses": courses,
        })
```

### Почему здесь не `ListView`

На странице нужны два самостоятельных списка:

```text
sidebar: Subject objects + количество курсов
content: Course objects + количество модулей
```

У `ListView` есть основной список `object_list`. Здесь можно было бы всё
собрать через `ListView.get_context_data()`, но связка `View` +
`TemplateResponseMixin` проще и честнее отражает экран: это каталог с фильтром,
а не только список Course.

### Жизненный цикл: `/`

```text
GET /
│
├─ URLconf: CourseListView.as_view()
├─ View.setup(request)
│  ├─ self.request = request
│  ├─ self.args = ()
│  └─ self.kwargs = {}
├─ View.dispatch(request)
│  └─ находит get → вызывает CourseListView.get(request, subject=None)
├─ Subject.objects.annotate(total_courses=Count("courses"))
├─ Course.objects.annotate(total_modules=Count("modules"))
├─ TemplateResponseMixin.render_to_response(context)
│  └─ выбирает template_name = courses/course/list.html
└─ HTTP 200 HTML
```

### Разбор строк

| Код | Что делает | Почему важно |
|---|---|---|
| `TemplateResponseMixin` | добавляет `render_to_response()` | позволяет вернуть HTML template без ручного `render()` |
| `View` | выбирает `get()` по HTTP method | это базовая CBV, не generic list |
| `template_name` | имя HTML | `render_to_response` ищет именно этот template |
| `subject=None` | принимает URL parameter | для `/` параметра нет; для `/subject/<slug>/` есть |
| `annotate(Count(...))` | добавляет вычисляемое поле на каждом объекте | в template есть `s.total_courses` и `course.total_modules` |
| `current_subject = None` | явно обозначает «все предметы» | template отмечает «Все курсы» как selected |
| `get_object_or_404` | получает subject или отдаёт 404 | не будет server 500 при плохом slug |
| `courses.filter(...)` | сужает SQL queryset | не фильтрует HTML после загрузки всех курсов |
| `render_to_response({...})` | строит TemplateResponse | ключи словаря становятся variables template |

### Жизненный цикл: `/subject/programming/`

В `courses/public_urls.py`:

```python
path(
    "subject/<slug:subject>/",
    views.CourseListView.as_view(),
    name="course_list_subject",
)
```

URL dispatcher передаст `subject="programming"` в `get()`. Тогда сработает
ветка `if subject`; `current_subject` попадёт в context, а template:

```django
<li{% if subject.id == s.id %} class="selected"{% endif %}>
```

покрасит выбранную категорию.

### Как улучшить как упражнение

На этом экране можно добавить поиск:

```python
query = request.GET.get("q", "").strip()
if query:
    courses = courses.filter(title__icontains=query)
```

Где будет видно: поле поиска над карточками на `/` и `/subject/.../`.
Использовать `request.GET`, потому что поиск не изменяет БД и URL можно
сохранить в закладки.

## 11.2. Детали публичного курса: `CourseDetailView`

### Где используется на сайте

| Действие | Template / кнопка | URL |
|---|---|---|
| Нажать название курса | `courses/course/list.html`, `course.title` | `/course/<slug>/` |
| Нажать «Подробнее» | `courses/course/list.html` | `/course/<slug>/` |
| Открыть курс по прямой ссылке | браузер | `/course/python-basics/` |

### Код

```python
class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course/detail.html"
    slug_field = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.forms import CourseEnrollForm
        context["enroll_form"] = CourseEnrollForm(
            initial={"course": self.object}
        )
        return context
```

### Что Django делает до `get_context_data`

Это критично: `self.object` не существует при создании instance view. Он
появляется в `BaseDetailView.get()`:

```text
GET /course/python-basics/
→ DetailView.get()
→ self.object = self.get_object()
→ только потом get_context_data()
```

Поэтому `self.object` безопасно использовать в `get_context_data`, но не в
`setup()` без самостоятельного получения объекта.

### Разбор

| Код | Эффект на сайте |
|---|---|
| `model = Course` | `DetailView` знает, какую таблицу искать |
| `slug_field = "slug"` | находит Course по `Course.slug`, а не по id |
| `template_name` | показывает `courses/course/detail.html` |
| `super().get_context_data()` | сохраняет `object` и `course` в context |
| `CourseEnrollForm(initial=...)` | создаёт форму с hidden course field |
| `context["enroll_form"]` | template может нарисовать кнопку «Записаться на курс» |

В template форма выводится только аутентифицированному пользователю:

```django
{% if request.user.is_authenticated %}
<form action="{% url 'student_enroll_course' %}" method="post">
  {{ enroll_form }}
  {% csrf_token %}
  <input type="submit" value="Записаться на курс">
</form>
{% endif %}
```

### Почему `super()` обязателен

Без строки:

```python
context = super().get_context_data(**kwargs)
```

в template пропадёт `object`, а выражения `{{ object.title }}`,
`{{ object.overview }}` не сработают. `DetailView` положил объект в context
именно в родительском `get_context_data`.

## 11.3. Запись студента: `StudentEnrollCourseView(FormView)`

### Где используется

На публичной странице details курса, в блоке действий под описанием.

| Событие | URL | HTTP | Что увидит пользователь |
|---|---|---|---|
| Открывает course detail | `/course/<slug>/` | GET | форма с кнопкой |
| Нажимает «Записаться на курс» | `/students/enroll-course/` | POST | redirect к материалам |

### Код

```python
class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    form_class = CourseEnrollForm

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

### Почему `FormView`, а не `CreateView`

CreateView создаёт один экземпляр модели, например новый Course. Здесь:

```text
Course существует
User существует
нужно создать связь в M2M таблице Course.students
```

Ни `Course`, ни `User` не создаются/не редактируются через форму. Это
действие над связью — правильная область `FormView`.

### Полный POST lifecycle

```text
POST /students/enroll-course/
│
├─ LoginRequiredMixin.dispatch()
│  ├─ гость: 302 на LOGIN_URL с ?next=...
│  └─ student: продолжает
├─ ProcessFormView.post()
│  └─ form = get_form()
│     └─ CourseEnrollForm(data=request.POST)
├─ form.is_valid()
│  ├─ False: form_invalid(form) → тот же form template с errors
│  └─ True:
│     └─ StudentEnrollCourseView.form_valid(form)
│        ├─ cleaned_data["course"] → валидный Course instance
│        ├─ course.students.add(request.user) → INSERT M2M
│        └─ super().form_valid(form)
│           └─ get_success_url()
│              └─ reverse_lazy("student_course_detail", args=[course.id])
└─ HTTP 302 → GET /students/course/<id>/
```

### Что может пойти не так

| Симптом | Причина | Где смотреть |
|---|---|---|
| 403 CSRF | отсутствует `{% csrf_token %}` | публичный course detail template |
| user попал на login | не аутентифицирован | `LoginRequiredMixin` |
| redirect ведёт не туда | ошибка URL name/args | `get_success_url()` |
| course не валиден | hidden input испорчен или course удалён | `CourseEnrollForm` |

## 11.4. Список и детали курсов студента

### Где используются

- `/students/courses/` — «Мои курсы» в header.
- `/students/course/<id>/` — кнопка «Перейти к материалам».
- `/students/course/<id>/module/<id>/` — название module в sidebar.

### Список: `StudentCourseListView`

```python
class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "students/course/list.html"

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)
```

#### Что происходит

```text
GET /students/courses/
→ LoginRequiredMixin.dispatch
→ BaseListView.get
→ StudentCourseListView.get_queryset
→ Course.objects.filter(students=request.user)
→ get_context_data(object_list=queryset)
→ students/course/list.html
```

### Почему фильтр здесь — security boundary

Не просто «показать красивый список». Тот же queryset нужен для защиты:
студент видит только курсы, где он в M2M `students`.

В template:

```django
{% for course in object_list %}
  <a href="{% url 'student_course_detail' course.id %}">
    {{ course.title }}
  </a>
{% endfor %}
```

`object_list` появился благодаря `ListView`; его не добавляли вручную.

### Детали: `StudentCourseDetailView`

```python
class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "students/course/detail.html"

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        module_id = self.kwargs.get("module_id")
        if module_id:
            context["module"] = course.modules.get(pk=module_id)
        else:
            context["module"] = course.modules.first()
        context["progress"] = get_course_progress(
            self.request.user, course
        )
        return context
```

#### Где видно каждый context key

| Context key | Template | Результат на экране |
|---|---|---|
| `object` | `students/course/detail.html` | title и список modules |
| `module` | тот же | выбранный модуль и контент |
| `progress` | тот же | число и ширина progress bar |

#### Риск и улучшение

`course.modules.get(pk=module_id)` выбросит `Module.DoesNotExist`, что даст
500, если `module_id` не принадлежит выбранному course. Для user-facing URL
лучше:

```python
context["module"] = get_object_or_404(
    course.modules,
    pk=module_id,
)
```

Где увидит пользователь: вместо server error при вручную введённом плохом URL
он получит нормальную 404 страницу.

## 11.5. Тест: простой `View` вместо generic form view

### Где используется

| Элемент | Template | URL |
|---|---|---|
| «Пройти тест» | `students/course/detail.html` | `quiz_take` |
| «Отправить ответы» | `students/quiz/take.html` | тот же URL, POST |
| «Пройти снова» | `students/quiz/result.html` | `quiz_take` |

### Почему здесь `View`

Форма теста создаётся динамически из Question/Answer. У неё нет фиксированного
набора Python form fields:

```text
question_4
question_8
question_15
```

Значит обычный `FormView` с заранее объявленным Form class был бы неудобен.
Простой `View` явно обрабатывает `request.POST`.

### GET: показать вопросы

```python
def get(self, request, pk, quiz_id):
    course = get_object_or_404(
        Course, pk=pk, students=request.user
    )
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    return render(request, self.template_name, {
        "course": course,
        "quiz": quiz,
        "questions": quiz.questions.prefetch_related("answers"),
    })
```

| Строка | Что происходит | Где видно |
|---|---|---|
| course lookup | проверяет enrollment | чужой студент получает 404 |
| quiz lookup | получает Quiz | заголовок и порог в template |
| `prefetch_related("answers")` | заранее получает варианты ответов | цикл `question.answers.all` не создаёт N+1 |
| `render(...)` | формирует HTML | `students/quiz/take.html` |

### POST: проверить ответы

```text
POST quiz URL
→ получает course + quiz + questions
→ для каждого question читает request.POST["question_<id>"]
→ проверяет, принадлежит ли выбранный Answer question и правильный ли он
→ вычисляет score / passed
→ update_or_create QuizResult
→ redirect на QuizResultView
```

`update_or_create` важен на экране «Пройти снова»: студент не копит результаты
в одной таблице, а обновляет свой текущий результат по конкретному quiz.

## 11.6. Course CRUD преподавателя: одна форма для Create и Update

### Где используется

| Действие | Button | Template | URL |
|---|---|---|---|
| открыть CMS | header «Преподавание» | `base.html` | `/course/mine/` |
| создать | «Создать курс» | `courses/manage/course/list.html` | `/course/create/` |
| изменить | «Редактировать» | тот же | `/course/<pk>/edit/` |
| удалить | «Удалить» | тот же | `/course/<pk>/delete/` |

### Миксины

```python
class OwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)
```

#### Объяснение

- `OwnerMixin` **не** получает `Course.objects.all()` заново. Он берёт
  queryset следующего класса MRO через `super()`, затем добавляет filter.
- Поэтому mixin работает с `ListView`, `DetailView`, `UpdateView` и
  `DeleteView`: все они вызывают `get_queryset()`.
- `OwnerEditMixin` меняет объект, когда ModelForm уже валидна, но ещё не
  сохранена. Это правильный момент подставить owner.

### Собирающий mixin и View

```python
class OwnerCourseMixin(
    OwnerMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
):
    model = Course
    fields = ["subject", "title", "slug", "overview"]
    success_url = reverse_lazy("manage_course_list")


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    template_name = "courses/manage/course/form.html"


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = "courses.add_course"


class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required = "courses.change_course"
```

### Как это работает на экране Create

```text
GET /course/create/
→ LoginRequiredMixin: teacher залогинен?
→ PermissionRequiredMixin: есть courses.add_course?
→ CreateView: создаёт пустую ModelForm из model + fields
→ template courses/manage/course/form.html

POST /course/create/
→ тот же access check
→ form.is_valid()
→ OwnerEditMixin.form_valid: form.instance.owner = teacher
→ ModelFormMixin.form_valid: self.object = form.save()
→ FormMixin.form_valid: redirect success_url
→ GET /course/mine/
```

### Как это работает на экране Update

```text
GET /course/12/edit/
→ access checks
→ UpdateView.get
→ OwnerMixin.get_queryset → только owner=current teacher
→ get_object(pk=12)
→ ModelForm(instance=object)
→ тот же form.html, но object существует

POST /course/12/edit/
→ снова owner-scoped lookup
→ ModelForm(request.POST, instance=object)
→ OwnerEditMixin сохраняет owner текущего user
→ form.save → redirect
```

На template тот же HTML использует:

```django
{% if object %}
  Редактировать курс
{% else %}
  Создать курс
{% endif %}
```

Именно `CreateView` оставляет `object=None`, а `UpdateView` кладёт найденный
Course в `object`.

### Важное замечание об `OwnerEditMixin` на Update

В данном проекте owner переустанавливается текущим user на update. Так как
`OwnerMixin` уже разрешает получить объект только его владельцу, значение не
изменится. Но как общий production-паттерн лучше применять такой mixin
только к CreateView: это предотвращает неожиданную смену author/owner в
более сложных сценариях.

## 11.7. Checklist: как объяснять себе любой новый CBV-код

Перед добавлением метода в view допишите в комментарии/документации:

```text
Экран:
URL:
Кто открывает:
GET или POST:
Что Django сделал до метода:
Что делает мой код:
Что увидит пользователь:
Что будет после return:
```

Пример:

```text
Экран: детали курса студента.
URL: /students/course/12/module/4/.
Кто: записанный студент.
GET или POST: GET.
До метода: DetailView нашёл course=12 в scoped queryset, self.object готов.
Мой код: получает module=4 только из self.object.modules и считает progress.
Пользователь: видит выбранный module и progress bar.
После return: DetailView рендерит students/course/detail.html.
```

Это лучший способ не потерять смысл при расширении generic views.

## 11.8. Как пользоваться этой главой при чтении проекта

Откройте один реальный экран, например `/students/course/1/`, и держите
параллельно четыре вкладки:

```text
Browser                 — видимый интерфейс и кнопки
DevTools Network        — GET/POST/302/200
students/urls.py        — URL → CBV class
students/views.py       — lifecycle и custom methods
template detail.html    — context variables и следующий URL
```

Затем пройдите код **сверху вниз по запросу**, а не по файлам:

```text
Клик «Пройти тест»
→ {% url 'quiz_take' object.id content.object_id %}
→ students/urls.py: QuizTakeView.as_view()
→ QuizTakeView.get()
→ render(..., questions=...)
→ students/quiz/take.html
→ POST после «Отправить ответы»
→ QuizTakeView.post()
→ redirect('quiz_result', ...)
→ QuizResultView.get()
→ students/quiz/result.html
```

Если добавить свою feature, например Announcement, используйте этот же
шаблон документации: сначала нарисуйте user flow и URL, затем выберите CBV,
после — добавьте model/queryset/permissions/template. Так код начинается с
реального поведения сайта, а не с случайно выбранного базового класса.
