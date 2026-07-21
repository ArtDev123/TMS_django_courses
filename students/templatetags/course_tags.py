from django import template

from students.services import get_course_progress, is_module_completed

register = template.Library()


@register.filter
def course_progress(course, user):
    return get_course_progress(user, course)


@register.filter
def module_completed(module, user):
    return is_module_completed(user, module)