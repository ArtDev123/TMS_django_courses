# 6. Практикум: generic views в Educa

[← Date views](05-date-views.md) · [Оглавление](README.md) · [Далее: справочник →](07-reference-cheatsheet.md)

Этот практикум связывает CBV с текущими сущностями Educa. Выполняйте упражнения
на отдельной ветке и после каждого шага запускайте `python manage.py check`.

### Теория практики: сначала наблюдение, затем изменение

При изучении generic views легко скопировать рабочий фрагмент, не поняв,
почему он работает. Практика должна идти в обратном направлении: сначала
открыть существующий экран, определить URL, HTTP method и базовый класс,
посмотреть Network и только после этого менять один метод.

Так вы замечаете причинно-следственную связь. Например, добавление фильтра в
`get_queryset()` меняет не только число карточек на странице: оно меняет
набор объектов, который Detail/Update/Delete вообще способны найти. Это
понимание важнее самого синтаксиса `filter(...)`.

## 6.1. Подготовка

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py runserver
```

Для CRUD преподавателя создайте:

1. группу `Instructors`;
2. пользователя `teacher`;
3. выдайте ему нужные permissions `courses.*`;
4. создайте хотя бы один курс с owner=`teacher`;
5. создайте студента и запишите его на курс.

## 6.2. Что уже есть в проекте

| View | Generic class | Что демонстрирует |
|---|---|---|
| `CourseDetailView` | `DetailView` | поиск по slug, добавление формы в context |
| `ManageCourseListView` | `ListView` | список owner-объектов |
| `CourseCreateView` | `CreateView` | ModelForm, `form_valid`, owner |
| `CourseUpdateView` | `UpdateView` | редактирование объекта |
| `CourseDeleteView` | `DeleteView` | подтверждение удаления |
| `StudentRegistrationView` | `CreateView` | готовая форма `UserCreationForm` |
| `StudentEnrollCourseView` | `FormView` | бизнес-действие без создания одной модели |
| `StudentCourseDetailView` | `DetailView` | private queryset + дополнительный context |

Сначала прочитайте соответствующие классы в `courses/views.py` и
`students/views.py`, затем сравните со схемами в предыдущих главах.

## 6.3. Упражнение: улучшить `StudentCourseListView`

Цель: отработать `get_queryset`, pagination и контекст.

Требования:

1. Добавить `paginate_by = 6`.
2. Загрузить subject заранее через `select_related("subject")`.
3. Поддержать `?q=` для поиска по названию.
4. Передать строку поиска в контекст как `query`.
5. Добавить pagination controls в шаблон.

Ожидаемый queryset:

```python
def get_queryset(self):
    queryset = (
        Course.objects
        .filter(students=self.request.user)
        .select_related("subject")
    )
    query = self.request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(title__icontains=query)
    return queryset
```

Проверки:

```text
/students/courses/                → только свои курсы
/students/courses/?q=python       → только подходящие
/students/courses/?page=2         → вторая страница
```

## 6.4. Упражнение: безопасный `DetailView`

Цель: увидеть, что доступ к объекту — задача `get_queryset`.

Создайте view «мой сертификат»:

```python
class MyCertificateView(LoginRequiredMixin, DetailView):
    model = Certificate
    slug_field = "code"
    slug_url_kwarg = "code"
    template_name = "students/certificate/detail.html"

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)
```

Проверка:

1. Откройте сертификат владельцем — 200.
2. Скопируйте URL.
3. Выйдите и войдите вторым пользователем.
4. Откройте URL — ожидается 404.

Не делайте проверку в шаблоне: HTML не является границей доступа.

## 6.5. Упражнение: `FormView` для контакта преподавателя

Сценарий: студент отправляет вопрос преподавателю курса. Не создаётся
отдельная модель — письмо/сообщение отправляется после валидации.

Шаги:

1. Создайте `CourseQuestionForm` с полями `subject`, `message`.
2. Создайте `CourseQuestionView(LoginRequiredMixin, FormView)`.
3. В `dispatch()` получите курс только из тех, где student записан.
4. В `form_valid()` временно покажите `messages.success` (что-то типо flash сообщений во фласке, по хорошему отправлять емейл, но сложновато реализовывать).
5. В `get_success_url()` вернитесь в детали курса.

Ключевые решения:

```text
курс из URL → dispatch
данные формы → cleaned_data
действие после валидации → form_valid
redirect зависит от self.course → get_success_url
```

## 6.6. Упражнение: полный CRUD Announcement

Если в проекте есть модель `Announcement`, используйте её. Если нет —
создайте модель с `course`, `author`, `title`, `body`, `is_published`.

### List

```python
class AnnouncementListView(LoginRequiredMixin, ListView):
    model = Announcement
    template_name = "courses/manage/announcement/list.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course, pk=kwargs["course_id"], owner=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Announcement.objects.filter(course=self.course)
```

### Create

```python
class AnnouncementCreateView(LoginRequiredMixin, CreateView):
    model = Announcement
    fields = ["title", "body", "is_published"]

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course, pk=kwargs["course_id"], owner=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("announcement_list", args=[self.course.id])
```

### Update/Delete

У обоих обязательно scope:

```python
def get_queryset(self):
    return Announcement.objects.filter(course__owner=self.request.user)
```

Упражнения:

- добавьте `PermissionRequiredMixin`;
- вынесите повторяемый owner-filter в mixin;
- добавьте отдельное поле `updated_by`;
- покажите студенту только published announcements;
- напишите тест, что чужой преподаватель получает 404.

## 6.7. Тестирование CBV

`django.test.TestCase` + `Client` покрывают CBV так же, как FBV: через HTTP.

```python
from django.test import TestCase
from django.urls import reverse


class CourseViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="secret")
        self.other = User.objects.create_user("other", password="secret")
        self.course = Course.objects.create(
            owner=self.owner,
            subject=...,
            title="Python",
            slug="python",
            overview="...",
        )

    def test_owner_can_open_update_page(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("course_edit", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_other_cannot_open_update_page(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("course_edit", args=[self.course.pk])
        )
        self.assertEqual(response.status_code, 404)
```

Полезные assertions:

| Assertion | Когда |
|---|---|
| `assertTemplateUsed` | выбран правильный template |
| `assertContains` | контент есть на странице |
| `assertRedirects` | успешная форма перенаправила куда нужно |
| `assertFormError` | форма не прошла валидацию |
| `assertQuerySetEqual` | queryset соответствует scope |

## 6.8. Отладка

### Проверить MRO

```bash
python manage.py shell -c "
from courses.views import CourseCreateView
print(*[cls.__name__ for cls in CourseCreateView.__mro__], sep='\n')
"
```

### Посмотреть SQL queryset

```python
queryset = Course.objects.filter(students=request.user).select_related("subject")
print(queryset.query)
```

### Проверить URL

```python
from django.urls import reverse, resolve

reverse("course_edit", args=[1])
resolve("/course/1/edit/")
```

### Проверить permissions

```python
user.has_perm("courses.change_course")
user.get_all_permissions()
```

## 6.9. Рефакторинг: когда остановиться

Не выносите mixin после первого повтора. Оставьте явный код, когда:

- логика нужна одной view;
- условия похожи, но не одинаковы;
- mixin скрывает важную бизнес-проверку;
- MRO становится сложнее, чем исходный код.

Выносите mixin, когда есть стабильное правило, например: «во всех CRUD
преподаватель видит только объекты, у которых `owner=request.user`».

## 6.10. Как каждое упражнение проявится на сайте

Не выполняйте упражнения только через shell: после каждого изменения откройте
реальный экран, чтобы связать метод view с пользовательским действием.

| Упражнение | Где открыть | Что сделать в браузере | Что проверяет |
|---|---|---|---|
| Поиск/пагинация курсов | `/students/courses/` | ввести `?q=python`, затем `?page=2` | `get_queryset`, `paginate_by`, context |
| Приватный certificate | `/students/profile/` | нажать «Открыть», затем повторить чужим user | DetailView scoped queryset |
| Вопрос преподавателю | course details | отправить валидную и невалидную форму | FormView GET/POST |
| Announcement CRUD | CMS course page | Create → Edit → Delete | Create/Update/Delete lifecycle |

### Рекомендуемый цикл разработки

```text
1. Добавили/изменили view.
2. python manage.py check.
3. Открыли экран по URL.
4. Проверили GET в Network.
5. Нажали кнопку/form submit.
6. Проверили POST status и redirect.
7. Проверили, что БД/HTML изменились.
8. Повторили под другим user.
9. Добавили TestCase для успешного и запрещённого сценария.
```

### Пример: добавляете пагинацию «Моих курсов»

**Кодовая задача:** `paginate_by = 6` в `StudentCourseListView`.

**Где будет видно:** в `students/templates/students/course/list.html`, ниже
course cards должна появиться навигация страниц.

**Что Django делает:**

```text
GET /students/courses/?page=2
→ get_queryset() возвращает ВСЕ доступные courses
→ ListView/Paginator отделяет ровно вторую страницу
→ object_list в template содержит только 6 объектов страницы
→ page_obj содержит номер и ссылки previous/next
```

**Что нужно добавить в template:**

```django
{% if is_paginated %}
  {% if page_obj.has_previous %}
    <a href="?page={{ page_obj.previous_page_number }}">Назад</a>
  {% endif %}
  <span>{{ page_obj.number }} / {{ paginator.num_pages }}</span>
  {% if page_obj.has_next %}
    <a href="?page={{ page_obj.next_page_number }}">Вперёд</a>
  {% endif %}
{% endif %}
```

**Локальная проверка:** создайте/запишите student минимум на 7 courses;
откройте `?page=1` и `?page=2`; в DevTools убедитесь, что оба действия —
обычные GET, а не POST.

### Пример: test доступа к чужому объекту

**Где будет видно:** второй teacher вручную вставляет URL чужого edit screen
в адресную строку.

```text
GET /course/17/edit/
→ CourseUpdateView.get_queryset()
→ filter(owner=second_teacher)
→ объект 17 не найден
→ HTTP 404
```

Это не ошибка интерфейса. Это ожидаемый результат того, что scope реализован
на уровне queryset.
