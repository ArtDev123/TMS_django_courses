from django.utils import timezone

from students.models import (
    ModuleProgress, CourseProgress, Certificate, Badge, UserBadge,
)


def get_course_progress(user, course):
    total = course.modules.count()
    if total == 0:
        return 0
    done = ModuleProgress.objects.filter(
        user=user, module__course=course, completed=True,
    ).count()
    return int(done / total * 100)


def mark_module_complete(user, module):
    progress, _ = ModuleProgress.objects.get_or_create(
        user=user, module=module)
    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

    course = module.course
    if get_course_progress(user, course) == 100:
        cp, _ = CourseProgress.objects.get_or_create(
            user=user, course=course)
        if not cp.completed:
            cp.completed = True
            cp.completed_at = timezone.now()
            cp.save()
            on_course_completed(user, course)


def is_module_completed(user, module):
    return ModuleProgress.objects.filter(
        user=user, module=module, completed=True,
    ).exists()


def issue_certificate(user, course):
    return Certificate.objects.get_or_create(user=user, course=course)


def award_course_badges(user, course):
    for badge in Badge.objects.filter(course=course):
        UserBadge.objects.get_or_create(user=user, badge=badge)


def on_course_completed(user, course):
    issue_certificate(user, course)
    award_course_badges(user, course)
