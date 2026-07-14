# Шаг 3 — Модели викторин + миграция

**Предыдущий:** [step-02-fixtures.md](step-02-fixtures.md) · **Следующий:** [step-04-cms.md](step-04-cms.md)

## Зачем

Quiz — 5-й тип контента в модуле. Без Question/Answer/QuizResult CMS викторин и прохождение тестов не заработают.

## 1. Добавить в конец `courses/models.py`

```python
class Quiz(ItemBase):
    description = models.TextField(blank=True)
    pass_percent = models.PositiveIntegerField(
        default=70,
        help_text='Минимальный процент для зачёта теста')


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    order = OrderField(blank=True, for_fields=['quiz'])

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:50]


class Answer(models.Model):
    question = models.ForeignKey(
        Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:50]


class QuizResult(models.Model):
    user = models.ForeignKey(
        User, related_name='quiz_results', on_delete=models.CASCADE)
    quiz = models.ForeignKey(
        Quiz, related_name='results', on_delete=models.CASCADE)
    score = models.PositiveIntegerField()
    passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'quiz'],
                name='unique_user_quiz_result',
            ),
        ]
```

## 2. Миграция

```bash
python manage.py makemigrations courses
python manage.py migrate
```

---

## проверка

| ☐ | Действие | Ожидаемый результат |
|---|----------|---------------------|
| ☐ | `python manage.py migrate` | `Applying courses.0002_... OK` |
| ☐ | Shell — импорт моделей | Без ошибок |
| ☐ | Admin → обновить страницу | Появятся модели Quiz (если admin уже настроен на шаге 4 — иначе проверка через shell) |

### Команды

```bash
python manage.py shell -c "
from courses.models import Quiz, Question, Answer, QuizResult
print('OK:', Quiz, Question, Answer, QuizResult)
"

python manage.py showmigrations courses
# [X] 0001_initial
# [X] 0002_...
```

**Все пункты отмечены?** → [step-04-cms.md](step-04-cms.md)
