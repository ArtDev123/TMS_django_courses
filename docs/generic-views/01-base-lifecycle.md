# 1. Основа: `View`, жизненный цикл и MRO

[← Оглавление](README.md) · [Далее: display views →](02-display-views.md)

## 1.1. От URL до ответа

В `urls.py` класс подключается не напрямую, а через `as_view()`:

```python
path("courses/", CourseListView.as_view(), name="course_list")
```

`as_view()` — class method. Она возвращает функцию, которую URL resolver
может вызвать как обычную Django view. При **каждом** запросе эта функция:

1. создаёт новый экземпляр `CourseListView`;
2. вызывает `setup(request, *args, **kwargs)`;
3. вызывает `dispatch(request, *args, **kwargs)`;
4. возвращает `HttpResponse`.

Новый экземпляр на запрос означает: можно хранить данные текущего запроса в
`self.course`, `self.object`, `self.request`, не опасаясь смешения данных
разных посетителей.

```text
GET /courses/42/?tab=content
          │
          ▼
CourseDetailView.as_view()
          │
          ▼
экземпляр CourseDetailView
          │
          ├─ setup()     → self.request, self.args, self.kwargs
          ├─ dispatch()  → выбирает get()
          ├─ get()       → получает object / context / template
          └─ response    → TemplateResponse → HTML
```

## 1.2. `View`: минимальная CBV

Все generic views в конце MRO наследуют `django.views.generic.base.View`.

```python
from django.http import HttpResponse
from django.views import View


class HealthView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")

    def post(self, request, *args, **kwargs):
        return HttpResponse("created", status=201)
```

```python
path("health/", HealthView.as_view(), name="health")
```

### Как `dispatch()` выбирает метод

| HTTP request | Искомый метод экземпляра |
|---|---|
| `GET` | `get()` |
| `POST` | `post()` |
| `PUT` | `put()` |
| `PATCH` | `patch()` |
| `DELETE` | `delete()` |
| `HEAD` | `head()` или `get()` |
| `OPTIONS` | `options()` |

Если метода нет либо он не разрешён в `http_method_names`, Django вернёт
**405 Method Not Allowed** через `http_method_not_allowed()`.

```python
class OnlyGetView(View):
    http_method_names = ["get"]

    def get(self, request):
        return HttpResponse("read-only")
```

`POST /...` на этой view будет 405. Ограничение методов полезно для
JSON-endpoint или команды, которая не должна обрабатываться браузерным GET.

## 1.3. `setup()`: данные URL и request

Базовая реализация записывает:

```python
self.request  # HttpRequest
self.args     # позиционные URL args
self.kwargs   # именованные URL args
```

Например, для:

```python
path("course/<int:pk>/", CourseDetailView.as_view())
```

внутри view:

```python
self.kwargs == {"pk": 42}
```

Переопределяйте `setup()` редко. Если нужно — **обязательно** вызовите
`super()`, иначе пропадут `self.request`, `self.args` и `self.kwargs`.

```python
class LanguageView(View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.language = request.headers.get("Accept-Language", "ru")
```

В предметных задачах чаще лучше использовать `dispatch()` (доступ до
обработчика) или `get_context_data()` (данные для шаблона).

## 1.4. `dispatch()`: общий вход для всех HTTP-методов

`dispatch()` запускается после `setup()` и до `get()`/`post()`. Это удобная
точка для условий, одинаковых для GET и POST:

- получить родительский объект из URL;
- проверить, что текущий пользователь владелец;
- записать родительский объект в `self`;
- открыть транзакцию для всего запроса (использовать осторожно).

Пример из логики Educa: преподаватель может работать только со своим курсом.

```python
from django.shortcuts import get_object_or_404
from django.views import View

from courses.models import Course


class CourseOwnerRequiredView(View):
    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(
            Course,
            pk=kwargs["course_id"],
            owner=request.user,
        )
        return super().dispatch(request, *args, **kwargs)
```

Почему здесь не `get()`? Потому что `CreateView` использует и `get()` для
формы, и `post()` для сохранения. Проверка в `dispatch()` защищает оба пути.

### Важный порядок при mixins

Когда mixin переопределяет `dispatch()`, он должен стоять **слева** от
основной view:

```python
class PrivateCourseView(LoginRequiredMixin, DetailView):
    ...
```

`LoginRequiredMixin.dispatch()` выполнится раньше `DetailView.dispatch()`.
Если написать `DetailView, LoginRequiredMixin`, защита может не сработать:
MRO найдёт `dispatch` у `View` раньше, чем у mixin.

## 1.5. `get()` и `post()`: когда переопределять

### Переопределяйте `get()` / `post()`, когда

- endpoint не является обычной формой;
- ответ — JSON, файл, streaming response;
- у действия специфичный протокол;
- нужна отдельная ветка поведения по HTTP-методу.

```python
from django.http import JsonResponse
from django.views import View


class CourseStatsView(View):
    def get(self, request, course_id):
        return JsonResponse({"course_id": course_id, "status": "ok"})
```

### Не переопределяйте их для обычного CRUD

Для `ListView`, `DetailView`, `FormView`, `CreateView`, `UpdateView`,
`DeleteView` базовые `get()`/`post()` уже правильно связывают десятки
внутренних методов. Как правило, переопределяйте ниже по уровню:

| Цель | Правильная точка расширения |
|---|---|
| Отфильтровать список / скрыть чужой объект | `get_queryset()` |
| Добавить данные в HTML-контекст | `get_context_data()` |
| Выбрать форму динамически | `get_form_class()` |
| Передать request/course в форму | `get_form_kwargs()` |
| Изменить объект до сохранения | `form_valid()` |
| Изменить ответ при ошибке | `form_invalid()` |
| Указать redirect | `success_url` или `get_success_url()` |
| Изменить поиск объекта | `get_object()` |

## 1.6. MRO: почему `super()` не «вызов родителя»

`super()` не означает «вызови класс, написанный слева». Он означает:
«найди следующий метод в **Method Resolution Order** текущего класса».

Упрощённый пример:

```python
class AuditMixin:
    def form_valid(self, form):
        print("audit")
        return super().form_valid(form)


class OwnerMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class CourseCreateView(AuditMixin, OwnerMixin, CreateView):
    ...
```

Цепочка `form_valid()`:

```text
AuditMixin.form_valid
  → OwnerMixin.form_valid
    → ModelFormMixin.form_valid
      → form.save()
      → FormMixin.form_valid
      → redirect(get_success_url())
```

Если один mixin не вызовет `super()`, цепочка прервётся. Например, если
`OwnerMixin.form_valid` вернёт response без `super()`, объект может не
сохраниться.

### Посмотреть MRO

В Django shell:

```python
from courses.views import CourseCreateView

for cls in CourseCreateView.__mro__:
    print(cls.__module__, cls.__name__)
```

Либо:

```python
CourseCreateView.mro()
```

Это лучший способ отладить непонятное поведение generic views.

## 1.7. Cooperative inheritance: контракт хорошего mixin

Mixin должен:

1. реализовывать ровно одну общую задачу;
2. не наследоваться от конкретной generic view, если достаточно `object`;
3. вызывать `super()` в переопределённом методе;
4. не предполагать атрибуты, которые другой mixin ещё не успел создать;
5. стоять в MRO раньше класса, чьё поведение он расширяет.

Хороший пример фильтра владельца:

```python
class OwnerQuerySetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(owner=self.request.user)
```

Плохой пример:

```python
class BadOwnerMixin:
    def get_queryset(self):
        return Course.objects.filter(owner=self.request.user)
```

В плохом варианте потеряются оптимизации или фильтры, которые добавил другой
mixin/view. В хорошем сохраняется исходный queryset, затем добавляется одно
условие.

## 1.8. `as_view()` и параметры класса

Можно передать атрибуты класса прямо в URL:

```python
path(
    "courses/",
    CourseListView.as_view(paginate_by=20),
    name="course_list",
)
```

Это задаёт атрибут экземпляра для этой URL-конфигурации. Подходит для простых
настроек, но не для бизнес-логики. Не передавайте методы, которых нет на
классе: `as_view()` проверяет имена и выбросит ошибку.

## 1.9. Async: важное ограничение

Django поддерживает async views, но одна CBV не может смешивать async и sync
обработчики HTTP-методов. Если `get()` объявлен `async def`, согласуйте это с
остальными методами класса и используемым стеком middleware. ORM по умолчанию
синхронный: в async view не вызывайте синхронные ORM-операции напрямую.

Для обычного HTML CRUD в Educa используйте синхронные generic views — они
проще, предсказуемы и подходят для ORM.

## 1.10. Мини-чеклист

- URL подключает `MyView.as_view()`, не `MyView`.
- Данные из URL доступны в `self.kwargs`.
- Общий доступ для GET и POST — в `dispatch()`.
- В mixin после своей логики вызывается `super()`.
- В доступах и ownership mixins стоят слева от generic view.
- Перед сложным наследованием выводите `MyView.mro()`.

## Документация Django

- [Base views: `View`, `as_view()`, `setup()`, `dispatch()`](https://docs.djangoproject.com/en/6.0/ref/class-based-views/base/)
- [Введение в class-based views](https://docs.djangoproject.com/en/6.0/topics/class-based-views/intro/)
- [MRO и mixins в Python](https://docs.python.org/3/tutorial/classes.html#multiple-inheritance)
