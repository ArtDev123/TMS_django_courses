# Шаг 7 — Views студента: enroll, курсы, материалы, quiz

**Предыдущий:** [step-06-services.md](step-06-services.md) · **Следующий:** [step-08-progress-test.md](step-08-progress-test.md)

## Зачем

Студент регистрируется, записывается на курс, видит **свои** курсы и материалы модулей, проходит викторины.

## 1. `students/forms.py`

Уже есть — **не менять**.

## 2. Заменить `students/views.py` целиком

Скопируйте [`code/students_views.py`](code/students_views.py) → `students/views.py`.

Полный код reference-файла:

```python
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView, DetailView, FormView, ListView, TemplateView,
)

from courses.models import Course, Module, Quiz, QuizResult
from .forms import CourseEnrollForm
from .models import Certificate
from .services import get_course_progress, mark_module_complete


class StudentRegistrationView(CreateView):
    template_name = 'students/student/registration.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('student_course_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        cd = form.cleaned_data
        user = authenticate(
            username=cd['username'], password=cd['password1'])
        login(self.request, user)
        return response


class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    form_class = CourseEnrollForm

    def form_valid(self, form):
        self.course = form.cleaned_data['course']
        self.course.students.add(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'student_course_detail', args=[self.course.id])


class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'students/course/list.html'

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)


class StudentCourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'students/course/detail.html'

    def get_queryset(self):
        return Course.objects.filter(students=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object
        module_id = self.kwargs.get('module_id')
        if module_id:
            context['module'] = course.modules.get(pk=module_id)
        else:
            context['module'] = course.modules.first()
        context['progress'] = get_course_progress(
            self.request.user, course)
        return context


class ModuleCompleteView(LoginRequiredMixin, View):
    def post(self, request, pk, module_id):
        course = get_object_or_404(
            Course, pk=pk, students=request.user)
        module = get_object_or_404(
            Module, pk=module_id, course=course)
        mark_module_complete(request.user, module)
        return redirect(
            'student_course_detail_module', pk, module_id)


class QuizTakeView(LoginRequiredMixin, View):
    template_name = 'students/quiz/take.html'

    def get(self, request, pk, quiz_id):
        course = get_object_or_404(
            Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        return render(request, self.template_name, {
            'course': course,
            'quiz': quiz,
            'questions': quiz.questions.prefetch_related('answers'),
        })

    def post(self, request, pk, quiz_id):
        course = get_object_or_404(
            Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        questions = list(quiz.questions.all())
        if not questions:
            return redirect('student_course_detail', pk)

        correct = 0
        for question in questions:
            selected_id = request.POST.get(f'question_{question.id}')
            if selected_id and question.answers.filter(
                    pk=selected_id, is_correct=True).exists():
                correct += 1

        score = int(correct / len(questions) * 100)
        passed = score >= quiz.pass_percent

        QuizResult.objects.update_or_create(
            user=request.user, quiz=quiz,
            defaults={'score': score, 'passed': passed})

        return redirect('quiz_result', pk=pk, quiz_id=quiz_id)


class QuizResultView(LoginRequiredMixin, View):
    template_name = 'students/quiz/result.html'

    def get(self, request, pk, quiz_id):
        course = get_object_or_404(
            Course, pk=pk, students=request.user)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        result = get_object_or_404(
            QuizResult, user=request.user, quiz=quiz)
        return render(request, self.template_name, {
            'course': course,
            'quiz': quiz,
            'result': result,
        })


class CertificateDetailView(LoginRequiredMixin, DetailView):
    model = Certificate
    template_name = 'students/certificate/detail.html'
    slug_field = 'code'
    slug_url_kwarg = 'code'

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)


class StudentProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'students/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx['certificates'] = user.certificates.select_related('course')
        ctx['badges'] = user.user_badges.select_related('badge')
        return ctx
```

## 3. Заменить `students/urls.py` целиком

```python
from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.StudentRegistrationView.as_view(),
         name='student_registration'),
    path('enroll-course/', views.StudentEnrollCourseView.as_view(),
         name='student_enroll_course'),
    path('courses/', views.StudentCourseListView.as_view(),
         name='student_course_list'),
    path('course/<int:pk>/', views.StudentCourseDetailView.as_view(),
         name='student_course_detail'),
    path('course/<int:pk>/module/<int:module_id>/',
         views.StudentCourseDetailView.as_view(),
         name='student_course_detail_module'),
    path('course/<int:pk>/module/<int:module_id>/complete/',
         views.ModuleCompleteView.as_view(), name='module_complete'),
    path('course/<int:pk>/quiz/<int:quiz_id>/',
         views.QuizTakeView.as_view(), name='quiz_take'),
    path('course/<int:pk>/quiz/<int:quiz_id>/result/',
         views.QuizResultView.as_view(), name='quiz_result'),
    path('certificate/<uuid:code>/',
         views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('profile/', views.StudentProfileView.as_view(),
         name='student_profile'),
]
```

## 4. `courses/templates/base.html` — полное меню для авторизованных

Замените блок `{% if request.user.is_authenticated %}` на:

```html
{% if request.user.is_authenticated %}
  <li><a href="{% url 'student_course_list' %}">Мои курсы</a></li>
  <li><a href="{% url 'student_profile' %}">Профиль</a></li>
  <li><a href="{% url 'manage_course_list' %}">Преподавание</a></li>
  <li>
    <form action="{% url 'logout' %}" method="post" class="logout-form">
      {% csrf_token %}
      <button type="submit">Выход</button>
    </form>
  </li>
{% else %}
```

(Пункт «Преподавание» уже мог быть добавлен на шаге 4 — убедитесь, что все четыре пункта на месте.)

---

## ✅ Ручная проверка (сделайте сейчас)

```bash
python manage.py check
python manage.py runserver
```

### Чеклист в браузере

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | [http://127.0.0.1:8000/students/register/](http://127.0.0.1:8000/students/register/) → создать `student` | Автовход → `/students/courses/` (список пуст) |
| ☐ | Шапка: «Мои курсы», «Профиль», «Преподавание», «Выход» | Ссылки без `NoReverseMatch` |
| ☐ | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) → курс **Python Basics** → «Записаться» | Редирект на `/students/course/<id>/` |
| ☐ | [http://127.0.0.1:8000/students/courses/](http://127.0.0.1:8000/students/courses/) | Курс в списке, прогресс **0%** |
| ☐ | Открыть материалы курса | Sidebar с модулями, контент (текст, файл, видео, викторина) |
| ☐ | Клик по модулю в sidebar | URL `/students/course/<id>/module/<module_id>/`, контент модуля |
| ☐ | Викторина → «Пройти тест» | Форма с radio-кнопками (полная проверка — шаг 9) |
| ☐ | [http://127.0.0.1:8000/students/profile/](http://127.0.0.1:8000/students/profile/) | Страница профиля (сертификаты пока пусто) |
| ☐ | Выйти → войти как другой пользователь, не записанный на курс → `/students/course/99/` | **404** |
| ☐ | Вход `admin` → «Мои курсы» | Страница открывается (может быть пустой) |

**Все пункты отмечены?** → [step-08-progress-test.md](step-08-progress-test.md)
