# 10. Локальный ручной прогон Educa: экран → кнопка → URL → CBV

[← Реальные рецепты](09-real-world-recipes.md) · [Оглавление](README.md)

Этот документ — практическая карта текущего Educa. Запустите проект на своём
компьютере, нажимайте реальные кнопки и одновременно смотрите:

- DevTools → **Network** (URL, HTTP method, status, redirect);
- терминал с `python manage.py runserver` (Django access log);
- соответствующий класс в `courses/views.py` или `students/views.py`;
- указанный шаблон.

Так generic views перестают быть абстракцией: видно, какой запрос вызвал
`get()`, какой — `post()`, и где Django выполнил redirect.

## 10.1. Подготовка локального проекта

### 1. Запустите PostgreSQL и примените миграции

Используйте настройки проекта и переменные окружения для вашей БД.

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py check
```

Ожидание:

```text
System check identified no issues (0 silenced).
```

### 2. Создайте данные для ручной проверки

Через `/admin/` создайте:

| Что | Минимум |
|---|---|
| Subject | `Programming` |
| Преподаватель | пользователь `teacher`, staff, группа `Instructors` с course permissions |
| Студент | пользователь `student` |
| Course | owner=`teacher`, subject=`Programming`, slug=`python-basics` |
| Module | минимум один |
| Content | Text и Quiz |
| Quiz | минимум один вопрос с верным ответом |

Или используйте локальный seed-скрипт из документации проекта, если вы его
добавляли для разработки.

### 3. Запустите сервер

```bash
python manage.py runserver
```

Откройте [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

### 4. Как читать строку терминала

```text
"GET /course/python-basics/ HTTP/1.1" 200 1934
```

| Часть | Значение |
|---|---|
| `GET` | браузер запросил страницу, ожидается `get()` |
| `/course/python-basics/` | URL, который сопоставил URLconf |
| `200` | HTML отрендерен |
| `302` | redirect; браузер автоматически отправит следующий GET |
| `403` | permission/access запрещён |
| `404` | URL или scoped queryset не нашли объект |
| `500` | исключение во view/template/БД; смотрите traceback |

## 10.2. Быстрая карта всех экранов

| Роль | Что нажать / открыть | HTTP | URL | View |
|---|---|---|---|---|
| Гость | главная | GET | `/` | `CourseListView` |
| Гость | subject sidebar | GET | `/subject/<slug>/` | `CourseListView` |
| Гость | «Подробнее» | GET | `/course/<slug>/` | `CourseDetailView` |
| Гость | «Зарегистрироваться…» | GET/POST | `/students/register/` | `StudentRegistrationView` |
| Студент | «Записаться на курс» | POST | `/students/enroll-course/` | `StudentEnrollCourseView` |
| Студент | «Мои курсы» | GET | `/students/courses/` | `StudentCourseListView` |
| Студент | «Перейти к материалам» | GET | `/students/course/<pk>/` | `StudentCourseDetailView` |
| Студент | модуль в sidebar | GET | `/students/course/<pk>/module/<module_id>/` | `StudentCourseDetailView` |
| Студент | «Пройти тест» | GET/POST | `/students/course/<pk>/quiz/<quiz_id>/` | `QuizTakeView` |
| Студент | «Отправить ответы» | POST | тот же quiz URL | `QuizTakeView` |
| Студент | «Отметить модуль пройденным» | POST | `/students/course/<pk>/module/<id>/complete/` | `ModuleCompleteView` |
| Студент | профиль | GET | `/students/profile/` | `StudentProfileView` |
| Преподаватель | «Мои курсы» | GET | `/course/mine/` | `ManageCourseListView` |
| Преподаватель | «Создать курс» | GET/POST | `/course/create/` | `CourseCreateView` |
| Преподаватель | «Редактировать» | GET/POST | `/course/<pk>/edit/` | `CourseUpdateView` |
| Преподаватель | «Удалить» | GET/POST | `/course/<pk>/delete/` | `CourseDeleteView` |
| Преподаватель | «Модули» | GET/POST | `/course/<pk>/modules/` | `CourseModuleUpdateView` |

Полные URL берутся из:

- корневого подключения — `educa/urls.py`;
- публичного каталога — `courses/public_urls.py`;
- CMS преподавателя — `courses/urls.py`;
- интерфейса студента — `students/urls.py`.

## 10.3. Сценарий A: гость открывает каталог

### Что делать в браузере

1. Откройте `http://127.0.0.1:8000/`.
2. В левом sidebar нажмите «Programming».
3. На карточке курса нажмите «Подробнее».

### Где находятся кнопки

| Элемент | Template | Строка/конструкция |
|---|---|---|
| «Все курсы» | `courses/templates/courses/course/list.html` | `{% url 'course_list' %}` |
| subject | тот же | `{% url 'course_list_subject' s.slug %}` |
| «Подробнее» | тот же | `{% url 'course_detail' course.slug %}` |

### Шаг 1: `GET /`

URLconf:

```python
# courses/public_urls.py
path("", views.CourseListView.as_view(), name="course_list")
```

Lifecycle:

```text
Browser GET /
  → CourseListView.as_view()
  → View.setup(request)
      self.request = request
      self.kwargs = {}
  → View.dispatch()
  → CourseListView.get(request, subject=None)
      Subject.objects.annotate(total_courses=Count("courses"))
      Course.objects.annotate(total_modules=Count("modules"))
  → TemplateResponseMixin.render_to_response(context)
  → courses/course/list.html
  → HTTP 200
```

Обратите внимание: этот экран использует `TemplateResponseMixin + View`, а не
`ListView`. Это хороший пример, когда на одном экране два равноправных
набора данных: `subjects` и `courses`.

### Шаг 2: `GET /subject/programming/`

URLconf захватывает slug:

```python
path(
    "subject/<slug:subject>/",
    views.CourseListView.as_view(),
    name="course_list_subject",
)
```

Теперь:

```python
self.kwargs == {"subject": "programming"}
```

Но текущая `CourseListView.get` получает этот параметр аргументом:

```python
def get(self, request, subject=None):
```

Внутри:

```text
get_object_or_404(Subject, slug="programming")
→ courses.filter(subject=current_subject)
→ render тот же template с subject=current_subject
```

В template условие добавляет `class="selected"` выбранному subject.

### Шаг 3: `GET /course/python-basics/`

URL:

```python
path("course/<slug:slug>/", views.CourseDetailView.as_view(), name="course_detail")
```

View:

```python
class CourseDetailView(DetailView):
    model = Course
    slug_field = "slug"
```

Полный lifecycle:

```text
Browser GET /course/python-basics/
  → CourseDetailView.setup()
      self.kwargs = {"slug": "python-basics"}
  → dispatch() выбирает get()
  → BaseDetailView.get()
      self.object = self.get_object()
        get_queryset() → Course.objects.all()
        filter(slug="python-basics")
        get_object_or_404(...)
  → CourseDetailView.get_context_data()
      super() добавляет object / course
      добавляет enroll_form с initial={"course": self.object}
  → courses/course/detail.html
  → HTTP 200
```

Экран показывает `object.title`, `object.overview`, owner и кнопку записи.

## 10.4. Сценарий B: регистрация и запись на курс

### Экран регистрации

Как гость на details курса нажмите «Зарегистрироваться, чтобы записаться».

Template: `courses/templates/courses/course/detail.html`:

```django
<a href="{% url 'student_registration' %}" class="button">
  Зарегистрироваться, чтобы записаться
</a>
```

URL: `GET /students/register/`.

View: `StudentRegistrationView(CreateView)`.

#### GET lifecycle

```text
GET /students/register/
  → StudentRegistrationView.dispatch()
  → BaseCreateView.get()
      self.object = None
  → ProcessFormView.get()
      get_form() → UserCreationForm()
  → students/student/registration.html
  → 200
```

#### POST lifecycle

Заполните username/password/password confirmation и нажмите submit.

```text
POST /students/register/
  → BaseCreateView.post()
      self.object = None
  → ProcessFormView.post()
      form = UserCreationForm(request.POST)
      form.is_valid()
  → StudentRegistrationView.form_valid(form)
      super().form_valid(form)
        self.object = form.save()        # новый User
        redirect("/students/courses/")
      authenticate(username, password)
      login(request, user)               # session cookie
  → HTTP 302
Browser GET /students/courses/
```

После POST не должен рендериться успешный HTML напрямую: redirect защищает от
повторной регистрации при F5.

### Запись на курс

После входа вернитесь на `/course/python-basics/` и нажмите
«Записаться на курс».

Кнопка — это форма, а не ссылка:

```django
<form action="{% url 'student_enroll_course' %}" method="post">
  {{ enroll_form }}
  {% csrf_token %}
  <input type="submit" value="Записаться на курс">
</form>
```

`enroll_form` создаётся `CourseDetailView.get_context_data()`. Hidden field
формы содержит id выбранного course.

Lifecycle:

```text
POST /students/enroll-course/
  → LoginRequiredMixin.dispatch()
      пользователь уже в session → пропускает дальше
  → ProcessFormView.post()
  → CourseEnrollForm(request.POST).is_valid()
  → StudentEnrollCourseView.form_valid(form)
      self.course = form.cleaned_data["course"]
      self.course.students.add(request.user)  # M2M INSERT
      super().form_valid(form)
  → StudentEnrollCourseView.get_success_url()
      reverse_lazy("student_course_detail", args=[course.id])
  → 302 /students/course/<id>/
```

**Что проверить:** второй POST той же формы не создаёт дубликат M2M-связи:
Django M2M table не должна добавлять повторную пару.

## 10.5. Сценарий C: студент изучает модуль

### 1. Список «Мои курсы»

После записи браузер идёт на `/students/course/<id>/`; для отдельной страницы
списка откройте `/students/courses/`.

```text
GET /students/courses/
  → LoginRequiredMixin.dispatch
  → BaseListView.get
  → StudentCourseListView.get_queryset
      Course.objects.filter(students=request.user)
  → get_context_data(object_list=...)
  → students/course/list.html
```

Кнопка «Перейти к материалам» в
`students/templates/students/course/list.html`:

```django
<a href="{% url 'student_course_detail' course.id %}">
  Перейти к материалам
</a>
```

### 2. Первый модуль

```text
GET /students/course/1/
  → LoginRequiredMixin.dispatch
  → BaseDetailView.get
      get_queryset()
        Course.objects.filter(students=request.user)
      get_object(pk=1)
  → StudentCourseDetailView.get_context_data
      module = course.modules.first()
      progress = get_course_progress(request.user, course)
  → students/course/detail.html
```

Это private `DetailView`: если пользователь не записан на курс, queryset
пустой, и `get_object()` вернёт 404.

### 3. Выбор другого модуля

Кнопки — ссылки sidebar в
`students/templates/students/course/detail.html`:

```django
<a href="{% url 'student_course_detail_module' object.id m.id %}">
  {{ m.title }}
</a>
```

Адрес: `/students/course/1/module/2/`.

Lifecycle почти тот же, но:

```python
module_id = self.kwargs.get("module_id")
context["module"] = course.modules.get(pk=module_id)
```

Важно: поиск идёт от `course.modules`, а не `Module.objects`. Поэтому module
другого курса не откроется.

### 4. Контент модуля

Template перебирает `module.contents.all`, затем вызывает GenericForeignKey:

```django
{% with item=content.item %}
  {{ item.render|safe }}
{% endwith %}
```

Для Text/Video/File/Image это рендерит template конкретного item. Для Quiz
ссылка строится отдельно, потому что quiz требует student action:

```django
<a href="{% url 'quiz_take' object.id content.object_id %}">
  Пройти тест
</a>
```

## 10.6. Сценарий D: тест (GET → POST → redirect → result)

### Экран теста

Нажмите «Пройти тест».

```text
GET /students/course/1/quiz/1/
  → LoginRequiredMixin.dispatch
  → QuizTakeView.get
      get_object_or_404(Course, pk=1, students=request.user)
      get_object_or_404(Quiz, pk=1)
      quiz.questions.prefetch_related("answers")
  → students/quiz/take.html
  → 200
```

Почему это простой `View`, а не `FormView`:

- вопросы динамические;
- HTML поля называются `question_<question.id>`;
- ответов и форм нет в одной фиксированной ModelForm;
- результат — вычисление score + `QuizResult.update_or_create`.

В template `students/templates/students/quiz/take.html`:

```django
<input
  type="radio"
  name="question_{{ question.id }}"
  value="{{ answer.id }}"
  required
>
```

`name` определяет ключ, который окажется в `request.POST`.

### Submit

Выберите ответ для каждого вопроса и нажмите «Отправить ответы».

```text
POST /students/course/1/quiz/1/
  → QuizTakeView.post
      проверяет student записан на course
      получает Quiz и вопросы
      для каждого question:
        selected_id = request.POST["question_<id>"]
        проверяет correct answer в queryset
      score = correct / questions * 100
      passed = score >= quiz.pass_percent
      QuizResult.objects.update_or_create(
          user=request.user,
          quiz=quiz,
          defaults={"score": score, "passed": passed},
      )
  → redirect("quiz_result", pk=1, quiz_id=1)
  → HTTP 302
Browser GET /students/course/1/quiz/1/result/
```

### Экран результата

```text
GET /students/course/1/quiz/1/result/
  → QuizResultView.get
      проверяет enrollment course
      получает quiz
      get_object_or_404(QuizResult, user=request.user, quiz=quiz)
  → students/quiz/result.html
```

Кнопки экрана:

| Кнопка | Template | URL |
|---|---|---|
| «Пройти снова» | `students/quiz/result.html` | `quiz_take` |
| «Вернуться к курсу» | тот же | `student_course_detail` |

**Что проверить:** отправьте тест повторно с другими ответами. Из-за
`update_or_create` должна обновиться та же строка QuizResult, а не появиться
две записи.

## 10.7. Сценарий E: завершение модуля и flash message

На странице модуля нажмите «Отметить модуль пройденным».

Template:

```django
<form
  action="{% url 'module_complete' object.id module.id %}"
  method="post"
>
  {% csrf_token %}
  <input type="submit" value="Отметить модуль пройденным">
</form>
```

Lifecycle:

```text
POST /students/course/1/module/2/complete/
  → LoginRequiredMixin.dispatch
  → ModuleCompleteView.post
      get_object_or_404(Course, pk=1, students=request.user)
      get_object_or_404(Module, pk=2, course=course)
      mark_module_complete(request.user, module)
        ├─ False: messages.error(...)
        └─ True:  создаёт/обновляет ModuleProgress, messages.success(...)
  → redirect("student_course_detail_module", pk=1, module_id=2)
  → HTTP 302
Browser GET /students/course/1/module/2/
  → base.html читает messages
  → показывает `.alert`
```

Если сервис проверяет прохождение квизов, сначала попробуйте нажать кнопку
до теста: должны увидеть error flash. Затем сдайте тест и повторите.

## 10.8. Сценарий F: преподаватель управляет курсами

### Доступ

Войдите как `teacher`, добавленный в `Instructors` с permissions курса.
Откройте `/course/mine/`.

```text
GET /course/mine/
  → OwnerCourseMixin.get_queryset
      Course.objects.filter(owner=request.user)
  → LoginRequiredMixin.dispatch
  → PermissionRequiredMixin.dispatch
      user.has_perm("courses.view_course")
  → ListView.get
  → courses/manage/course/list.html
```

Фактический порядок зависит от MRO класса
`ManageCourseListView(OwnerCourseMixin, ListView)`, где
`OwnerCourseMixin` объединяет owner, login и permission логику.

В template `courses/templates/courses/manage/course/list.html` находятся:

| Кнопка | URL name | View |
|---|---|---|
| «Создать курс» | `course_create` | `CourseCreateView` |
| «Редактировать» | `course_edit` | `CourseUpdateView` |
| «Модули» | `course_module_update` | `CourseModuleUpdateView` |
| «Удалить» | `course_delete` | `CourseDeleteView` |

### Create course

Нажмите «Создать курс».

```text
GET /course/create/
  → CourseCreateView
  → CreateView.get
  → ModelForm без instance
  → courses/manage/course/form.html

POST /course/create/
  → CourseCreateView.form_valid
      form.instance.owner = request.user
  → ModelFormMixin.form_valid
      self.object = form.save()
  → reverse_lazy("manage_course_list")
  → 302 /course/mine/
```

Шаблон формы:

```django
<form method="post">
  {{ form.as_p }}
  {% csrf_token %}
  <input type="submit" value="Сохранить">
</form>
```

Проверьте через admin/БД: owner нового курса должен быть текущим teacher, а
не значение из формы.

### Update course

Нажмите «Редактировать».

```text
GET /course/1/edit/
  → CourseUpdateView
  → BaseUpdateView.get
      self.object = get_object()
      OwnerMixin.get_queryset() фильтрует owner=request.user
  → ModelForm(instance=self.object)
  → тот же courses/manage/course/form.html

POST /course/1/edit/
  → self.object = get_object() снова
  → ModelForm(request.POST, instance=self.object)
  → form.is_valid → form.save → redirect /course/mine/
```

Откройте тот же URL под вторым преподавателем: ожидается 404 (scope queryset),
даже если у него есть permission `change_course`.

### Delete course

Нажмите «Удалить».

```text
GET /course/1/delete/
  → CourseDeleteView.get
  → получает object через owner-scoped queryset
  → courses/manage/course/delete.html
  → confirmation screen

POST /course/1/delete/
  → BaseDeleteView.form_valid
  → object.delete()
  → 302 /course/mine/
```

Нажмите «Отмена»: это обычный GET link, объект не удаляется. Нажмите
«Да, удалить»: это POST form с CSRF token.

## 10.9. Сценарий G: модули, content и граница generic views

Нажмите «Модули» в CMS.

```text
GET /course/1/modules/
  → CourseModuleUpdateView.dispatch
      self.course = get_object_or_404(Course, pk=1, owner=request.user)
  → CourseModuleUpdateView.get
      get_formset()
      ModuleFormSet(instance=self.course)
  → courses/manage/module/formset.html
```

Это осознанно **не** `UpdateView`: один экран одновременно редактирует
набор Module через formset, а не одну ModelForm.

После submit:

```text
POST /course/1/modules/
  → dispatch проверяет owner
  → get_formset(data=request.POST)
  → formset.is_valid()
  → formset.save()
  → redirect("course_module_update", pk=course.id)
```

Это наглядная граница:

| Ситуация | Лучший выбор |
|---|---|
| Одна модель + одна форма | CreateView/UpdateView |
| Один экран + formset нескольких моделей | `View` + `TemplateResponseMixin` |
| GFK и динамический model type | `View` + явная логика |
| JSON reorder | `View` + `JsonResponse` |

## 10.10. Сценарий H: профиль и certificate

### Profile

Откройте `/students/profile/`.

```text
GET /students/profile/
  → LoginRequiredMixin.dispatch
  → TemplateView.get
  → StudentProfileView.get_context_data
      certificates = user.certificates.select_related("course")
      badges = user.user_badges.select_related("badge")
  → students/profile.html
```

Это пример `TemplateView`: экран показывает несколько независимых collections,
поэтому у него нет одного правильного `object_list`.

### Certificate detail

На profile нажмите «Открыть» рядом с сертификатом:

```django
<a href="{% url 'certificate_detail' cert.code %}">Открыть</a>
```

```text
GET /students/certificate/<uuid>/
  → CertificateDetailView
      slug_field = "code"
      slug_url_kwarg = "code"
      get_queryset() → Certificate.objects.filter(user=request.user)
  → DetailView.get_object()
  → students/certificate/detail.html
```

Проверьте в другом браузере: UUID чужого certificate не должен открыть
страницу; ожидается 404.

## 10.11. Ручной чеклист по HTTP-методам

Откройте DevTools → Network и выполните:

| Действие | Должно быть |
|---|---|
| Открыть каталог | один `GET`, 200 |
| Выбрать subject | один `GET`, 200 |
| Нажать «Подробнее» | один `GET`, 200 |
| Зарегистрироваться | `POST`, 302, затем `GET` |
| Записаться на курс | `POST`, 302, затем `GET` |
| Открыть модуль | `GET`, 200 |
| Сдать тест | `POST`, 302, затем `GET result` |
| Завершить модуль | `POST`, 302, затем `GET module` |
| Создать курс | `POST`, 302, затем `GET /course/mine/` |
| Открыть delete | `GET`, 200, объект остаётся |
| Подтвердить delete | `POST`, 302, объект исчезает |

Если вместо 302 после формы видите 200 на POST, проверьте `form_valid()`:
возможно, не вызван `super().form_valid(form)` или view вернула template
вместо redirect.

## 10.12. Как связать экран с исходным кодом

Для любого незнакомого экрана работайте в таком порядке:

1. В браузере скопируйте URL.
2. Найдите соответствующий `path(...)` в `urls.py`.
3. Откройте class после `.as_view()`.
4. Посмотрите базовый класс (`ListView`, `DetailView`, `CreateView` и т.д.).
5. Найдите переопределённые методы: `dispatch`, `get_queryset`,
   `get_context_data`, `form_valid`, `get_success_url`.
6. Откройте `template_name`.
7. В template найдите кнопку/форму и `{% url ... %}`.
8. Повторите действие и проверьте Network + terminal.

Эта последовательность работает для любого Django-проекта с CBV.

## Документация Django

- [Request and response](https://docs.djangoproject.com/en/6.0/ref/request-response/)
- [URL dispatcher](https://docs.djangoproject.com/en/6.0/topics/http/urls/)
- [Generic display views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-display/)
- [Generic editing views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-editing/)
- [Messages framework](https://docs.djangoproject.com/en/6.0/ref/contrib/messages/)
