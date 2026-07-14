import json

from django.contrib.auth.mixins import (
    LoginRequiredMixin, PermissionRequiredMixin,
)
from django.db.models import Count
from django.forms.models import modelform_factory
from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView

from .forms import ModuleFormSet, AnswerFormSet
from .models import (
    Subject, Course, Module, Content, Quiz, Question,
)


# --- Публичный каталог (уже было) ---

class CourseListView(TemplateResponseMixin, View):
    template_name = 'courses/course/list.html'

    def get(self, request, subject=None):
        subjects = Subject.objects.annotate(
            total_courses=Count('courses'))
        courses = Course.objects.annotate(
            total_modules=Count('modules'))
        current_subject = None
        if subject:
            current_subject = get_object_or_404(Subject, slug=subject)
            courses = courses.filter(subject=current_subject)
        return self.render_to_response({
            'subjects': subjects,
            'subject': current_subject,
            'courses': courses,
        })


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course/detail.html'
    slug_field = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.forms import CourseEnrollForm
        context['enroll_form'] = CourseEnrollForm(
            initial={'course': self.object})
        return context


# --- CMS: mixins ---

class OwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin, PermissionRequiredMixin):
    model = Course
    fields = ['subject', 'title', 'slug', 'overview']
    success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    template_name = 'courses/manage/course/form.html'


class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = 'courses/manage/course/list.html'
    permission_required = 'courses.view_course'


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = 'courses.add_course'


class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required = 'courses.change_course'


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = 'courses/manage/course/delete.html'
    permission_required = 'courses.delete_course'


class CourseModuleUpdateView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/module/formset.html'

    def dispatch(self, request, pk):
        self.course = get_object_or_404(
            Course, pk=pk, owner=request.user)
        return super().dispatch(request, pk)

    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)

    def get(self, request, pk):
        formset = self.get_formset()
        return self.render_to_response({
            'course': self.course,
            'formset': formset,
        })

    def post(self, request, pk):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            return redirect('manage_course_list')
        return self.render_to_response({
            'course': self.course,
            'formset': formset,
        })


class ContentCreateUpdateView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/content/form.html'
    module = None
    model = None
    obj = None

    def get_model(self, model_name):
        allowed = ['text', 'video', 'image', 'file', 'quiz']
        if model_name in allowed:
            return apps.get_model(app_label='courses', model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        form_class = modelform_factory(
            model, exclude=['owner', 'created', 'updated'])
        return form_class(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(
            Module, pk=module_id, course__owner=request.user)
        self.model = self.get_model(model_name)
        if not self.model:
            return redirect('course_module_update', pk=self.module.course.pk)
        if id:
            self.obj = get_object_or_404(
                self.model, pk=id, owner=request.user)
        return super().dispatch(request, module_id, model_name, id)

    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response({
            'form': form,
            'object': self.obj,
            'module': self.module,
        })

    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(
            self.model, instance=self.obj,
            data=request.POST, files=request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                Content.objects.create(module=self.module, item=obj)
            if model_name == 'quiz':
                return redirect(
                    'quiz_manage', module_id=self.module.id, quiz_id=obj.id)
            return redirect(
                'course_module_update', pk=self.module.course.id)
        return self.render_to_response({
            'form': form,
            'object': self.obj,
            'module': self.module,
        })


def _get_quiz_in_module(request, module_id, quiz_id):
    module = get_object_or_404(
        Module, pk=module_id, course__owner=request.user)
    quiz = get_object_or_404(Quiz, pk=quiz_id, owner=request.user)
    get_object_or_404(
        Content, module=module,
        content_type__model='quiz', object_id=quiz.id)
    return module, quiz


class QuizManageView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/quiz/manage.html'

    def get(self, request, module_id, quiz_id):
        module, quiz = _get_quiz_in_module(request, module_id, quiz_id)
        questions = quiz.questions.prefetch_related('answers')
        return self.render_to_response({
            'module': module,
            'quiz': quiz,
            'questions': questions,
        })


class QuestionCreateUpdateView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'courses/manage/quiz/question_form.html'

    def dispatch(self, request, module_id, quiz_id, question_id=None):
        self.module, self.quiz = _get_quiz_in_module(
            request, module_id, quiz_id)
        self.question = None
        if question_id:
            self.question = get_object_or_404(
                Question, pk=question_id, quiz=self.quiz)
        return super().dispatch(
            request, module_id, quiz_id, question_id)

    def get_question_form(self, data=None):
        form_class = modelform_factory(Question, fields=['text'])
        return form_class(instance=self.question, data=data)

    def get(self, request, module_id, quiz_id, question_id=None):
        form = self.get_question_form()
        if self.question:
            formset = AnswerFormSet(instance=self.question)
        else:
            formset = AnswerFormSet(instance=Question(quiz=self.quiz))
        return self.render_to_response({
            'module': self.module,
            'quiz': self.quiz,
            'question': self.question,
            'form': form,
            'formset': formset,
        })

    def post(self, request, module_id, quiz_id, question_id=None):
        form = self.get_question_form(data=request.POST)
        if self.question:
            formset = AnswerFormSet(
                instance=self.question, data=request.POST)
            if form.is_valid() and formset.is_valid():
                form.save()
                formset.save()
                return redirect(
                    'quiz_manage', module_id=module_id, quiz_id=quiz_id)
        elif form.is_valid():
            question = form.save(commit=False)
            question.quiz = self.quiz
            question.save()
            formset = AnswerFormSet(instance=question, data=request.POST)
            if formset.is_valid():
                formset.save()
                return redirect(
                    'quiz_manage', module_id=module_id, quiz_id=quiz_id)
            formset = AnswerFormSet(instance=question)
        else:
            formset = AnswerFormSet(
                instance=self.question or Question(quiz=self.quiz))

        return self.render_to_response({
            'module': self.module,
            'quiz': self.quiz,
            'question': self.question,
            'form': form,
            'formset': formset,
        })


class QuestionDeleteView(LoginRequiredMixin, View):
    def post(self, request, module_id, quiz_id, question_id):
        module, quiz = _get_quiz_in_module(request, module_id, quiz_id)
        question = get_object_or_404(
            Question, pk=question_id, quiz=quiz)
        question.delete()
        return redirect('quiz_manage', module_id=module.id, quiz_id=quiz.id)


class ModuleOrderView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            order = json.loads(request.body)
            for item in order:
                Module.objects.filter(
                    pk=item['id'],
                    course__owner=request.user,
                ).update(order=item['order'])
            return JsonResponse({'status': 'ok'})
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({'status': 'error'}, status=400)


class ContentOrderView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            order = json.loads(request.body)
            for item in order:
                Content.objects.filter(
                    pk=item['id'],
                    module__course__owner=request.user,
                ).update(order=item['order'])
            return JsonResponse({'status': 'ok'})
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({'status': 'error'}, status=400)
