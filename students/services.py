from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from courses.models import Quiz, QuizResult
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


def all_module_quizzes_passed(user, module):
    quiz_ct = ContentType.objects.get_for_model(Quiz)
    quiz_ids = list(
        module.contents.filter(content_type=quiz_ct).values_list(
            'object_id', flat=True,
        )
    )
    if not quiz_ids:
        return True
    passed_count = QuizResult.objects.filter(
        user=user, quiz_id__in=quiz_ids, passed=True,
    ).count()
    return passed_count == len(quiz_ids)


def mark_module_complete(user, module):
    if not all_module_quizzes_passed(user, module):
        return False

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
    return True


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