# Шаг 4 — CMS преподавателя (`/course/`)

**Предыдущий:** [step-03-quiz-models.md](step-03-quiz-models.md) · **Следующий:** [step-05-student-models.md](step-05-student-models.md)

## Зачем

Преподаватель создаёт курсы, модули, контент и викторины **на сайте**. Файл `courses/urls.py` уже содержит маршруты — нужны views и forms.

## 1. Создать `courses/forms.py`

```python
from django.forms.models import inlineformset_factory

from .models import Course, Module, Question, Answer

ModuleFormSet = inlineformset_factory(
    Course,
    Module,
    fields=['title', 'description'],
    extra=2,
    can_delete=True,
)

AnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    fields=['text', 'is_correct'],
    extra=3,
    can_delete=True,
)
```

## 2. Заменить `courses/views.py` целиком

Скопируйте reference-файл в проект:

```bash
cp docs/remaining/code/courses_views.py courses/views.py
```

Или вручную: [`code/courses_views.py`](code/courses_views.py) → `courses/views.py`.

> **Важно:** в файле должны быть классы: `CourseListView`, `CourseDetailView`, `ManageCourseListView`, `CourseCreateView`, `CourseUpdateView`, `CourseDeleteView`, `CourseModuleUpdateView`, `ContentCreateUpdateView`, `QuizManageView`, `QuestionCreateUpdateView`, `QuestionDeleteView`, `ModuleOrderView`, `ContentOrderView`.

## 3. `courses/admin.py` — заменить целиком

```python
from django.contrib import admin
from .models import Subject, Course, Module, Quiz, Question, Answer


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}


class ModuleInline(admin.StackedInline):
    model = Module
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'created']
    list_filter = ['created', 'subject']
    search_fields = ['title', 'overview']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'pass_percent', 'created']
    inlines = [QuestionInline]
```

## 4. `educa/urls.py` — подключить CMS

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('course/', include('courses.urls')),
    path('students/', include('students.urls')),
    path('', include('courses.public_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

## 5. `courses/templates/base.html` — добавить «Преподавание»

В блоке `{% if request.user.is_authenticated %}` **перед** формой выхода:

```html
<li><a href="{% url 'manage_course_list' %}">Преподавание</a></li>
```

## 6. `courses/urls.py`

Уже готов — не менять.

---

## ✅ Ручная проверка (сделайте сейчас)

**Войдите как `teacher`.** Откройте режим инкогнито для студента позже.

```bash
python manage.py check
python manage.py runserver
```

### Чеклист CMS

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | [http://127.0.0.1:8000/course/mine/](http://127.0.0.1:8000/course/mine/) | «Мои курсы», кнопка «Создать курс» |
| ☐ | Шапка → «Преподавание» | Тот же список |
| ☐ | «Создать курс»: Subject **Programming**, title **Python Basics**, slug `python-basics`, overview — любой текст | Редирект на список, курс виден |
| ☐ | «Модули» → заполнить 2 модуля (title + description) → «Сохранить модули» | Модули в formset |
| ☐ | Chip **Текст** → title + content → Сохранить | Текст в списке контента модуля |
| ☐ | Chip **Файл** → загрузить PDF | Файл в `media/files/`, ссылка в списке |
| ☐ | Chip **Изображение** → загрузить PNG/JPG | Картинка в `media/images/` |
| ☐ | Chip **Видео** → URL YouTube | Контент type video |
| ☐ | Chip **Викторина** → title, pass_percent **70** | Редирект на страницу «Вопросы» |
| ☐ | «Добавить вопрос» → текст + 2–3 ответа, один **is_correct** | Вопрос в списке викторины |
| ☐ | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Курс **Python Basics** в каталоге |
| ☐ | `/course/python-basics/` | Overview + кнопка записи (для гостя/студента) |

### Проверка прав

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | Выйти → войти как будущий `student` (или гость) → `/course/mine/` | **403 Forbidden** |

**Все пункты отмечены?** → [step-05-student-models.md](step-05-student-models.md)
