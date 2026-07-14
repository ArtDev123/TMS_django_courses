import uuid

from django.db import models
from django.contrib.auth.models import User

from courses.models import Course, Module


class ModuleProgress(models.Model):
    user = models.ForeignKey(
        User, related_name='module_progress', on_delete=models.CASCADE)
    module = models.ForeignKey(
        Module, related_name='student_progress', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'module'],
                name='unique_user_module_progress',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.module}'


class CourseProgress(models.Model):
    user = models.ForeignKey(
        User, related_name='course_progress', on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course, related_name='student_progress', on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_progress',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.course}'


class Certificate(models.Model):
    user = models.ForeignKey(
        User, related_name='certificates', on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course, related_name='certificates', on_delete=models.CASCADE)
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'course'],
                name='unique_user_course_certificate',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.course}'


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='badges/', blank=True)
    course = models.ForeignKey(
        Course, related_name='badges', null=True, blank=True,
        on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        User, related_name='user_badges', on_delete=models.CASCADE)
    badge = models.ForeignKey(
        Badge, related_name='awarded_to', on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'badge'],
                name='unique_user_badge',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.badge}'
