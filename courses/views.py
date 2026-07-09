from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from .models import Subject, Course


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.forms import CourseEnrollForm
        context['enroll_form'] = CourseEnrollForm(
            initial={'course': self.object})
        return context
    