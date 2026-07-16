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