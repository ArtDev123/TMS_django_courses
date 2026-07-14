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
