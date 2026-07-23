# 7. Справочник и шпаргалка generic views

[← Практикум](06-practice-educa.md) · [Оглавление](README.md)

## 7.1. Как выбрать view

| Задача | Выбор |
|---|---|
| Статичная страница | `TemplateView` |
| Redirect / старый URL | `RedirectView` |
| Показать коллекцию | `ListView` |
| Показать один объект | `DetailView` |
| Валидировать форму, не создающую одну модель | `FormView` |
| Создать модель | `CreateView` |
| Редактировать модель | `UpdateView` |
| Подтвердить и удалить модель | `DeleteView` |
| Архив объектов по дате | date-based views |
| JSON/AJAX/action с особым протоколом | простой `View` |
| Сложная оркестрация formsets/GFK | простой `View` + `TemplateResponseMixin` |

## 7.2. Атрибуты display views

| Атрибут | View | Смысл |
|---|---|---|
| `model` | List/Detail/Create/Update/Delete | модель |
| `queryset` | почти все model views | исходная выборка |
| `template_name` | все template views | явный template |
| `context_object_name` | List/Detail | понятное имя в context |
| `paginate_by` | List | размер страницы |
| `page_kwarg` | List | имя GET parameter |
| `allow_empty` | List/date | 404 на пустом списке |
| `slug_field` | Detail | поле модели для slug |
| `slug_url_kwarg` | Detail | параметр URL для slug |
| `pk_url_kwarg` | Detail | параметр URL для PK |

## 7.3. Атрибуты editing views

| Атрибут | Смысл |
|---|---|
| `form_class` | свой класс Form/ModelForm |
| `fields` | поля автоматической ModelForm |
| `initial` | начальные значения |
| `prefix` | префикс HTML-полей |
| `success_url` | постоянный URL redirect |
| `template_name_suffix` | default suffix (`_form`, `_confirm_delete`) |

## 7.4. Методы и точки расширения

| Метод | Когда вызывается | Для чего |
|---|---|---|
| `setup()` | до dispatch | инициализация request/args/kwargs |
| `dispatch()` | до get/post | общая проверка GET и POST |
| `get_queryset()` | поиск списка/объекта | filters, ownership, optimisation |
| `get_object()` | Detail/Update/Delete | нестандартный lookup |
| `get_context_data()` | перед template | дополнительные данные |
| `get_template_names()` | перед template | template по условию |
| `get_form_class()` | до формы | динамический Form class |
| `get_form_kwargs()` | до формы | user/course/files/initial |
| `form_valid()` | после valid form | изменить объект, side effects |
| `form_invalid()` | после invalid form | сообщения/особый response |
| `get_success_url()` | перед redirect | URL зависит от object |
| `test_func()` | `UserPassesTestMixin` | произвольная проверка |

## 7.5. Method flowchart

### `ListView`

```text
setup → dispatch → get → get_queryset → get_context_data → render_to_response
```

### `DetailView`

```text
setup → dispatch → get → get_object → get_queryset
                  → get_context_data → render_to_response
```

### `FormView`

```text
GET:  setup → dispatch → get → get_form → context → render
POST: setup → dispatch → post → get_form → is_valid
                                      ├─ form_valid → redirect
                                      └─ form_invalid → render
```

### `CreateView`

```text
GET:  self.object=None → form без instance → render
POST: self.object=None → valid form → form.save → self.object → redirect
```

### `UpdateView`

```text
GET/POST: self.object=get_object → form(instance=self.object)
POST valid: form.save() → redirect
```

### `DeleteView`

```text
GET:  get_object → confirmation template
POST: get_object → form_valid → object.delete → redirect
```

## 7.6. Default template names

При `model = Course`:

| View | Default template |
|---|---|
| `ListView` | `courses/course_list.html` |
| `DetailView` | `courses/course_detail.html` |
| `CreateView` | `courses/course_form.html` |
| `UpdateView` | `courses/course_form.html` |
| `DeleteView` | `courses/course_confirm_delete.html` |

В production-коде явный `template_name` снижает магию и облегчает поиск.

## 7.7. Default context names

| View | Всегда | Дополнительно при model |
|---|---|---|
| ListView | `object_list` | `course_list` |
| DetailView | `object` | `course` |
| Create/Update | `form`, `view` | `object` на Update |
| Delete | `object` | имя модели |

## 7.8. Антипаттерны

### Нет `super()`

```python
def get_context_data(self, **kwargs):
    return {"title": "x"}  # ломает object_list/form/pagination
```

Правильно:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["title"] = "x"
    return context
```

### Ownership только в template

```django
{% if object.owner == request.user %}
  <a>Редактировать</a>
{% endif %}
```

Скрытие кнопки не защищает URL. Нужен `get_queryset()` с `owner=request.user`.

### Сохранение по GET

```python
def get(self, request, pk):
    Course.objects.get(pk=pk).delete()
```

GET должен быть безопасным и идемпотентным; удаление — только POST/DELETE.

### Широкий `fields = "__all__"`

Он может открыть пользователю служебные поля после изменения модели.
Явно перечисляйте editable fields.

### Смешивание form и объектной логики

`get_context_data` не место для сохранения объекта. `form_valid` не место
для отображения ошибки формы. Каждому этапу — свой метод.

## 7.9. Производительность

| Ситуация | Решение |
|---|---|
| `course.subject` в цикле | `select_related("subject")` |
| `course.modules.all()` в цикле | `prefetch_related("modules")` |
| счётчик M2M/related в цикле | `annotate(Count(...))` |
| список на тысячи строк | `paginate_by` |
| template делает сложную логику | перенести в queryset/context/service |

Профилируйте реальную страницу, не добавляйте `prefetch_related` «на всякий
случай»: лишний prefetch тоже стоит запросов и памяти.

## 7.10. Отладка 500/403/404

| Ошибка | Первое место проверки |
|---|---|
| 404 на Detail/Update | `get_queryset`, URL kwarg, pk/slug |
| 403 на CMS | `user.has_perm`, группа, `permission_required` |
| view не требует login | порядок mixins в MRO |
| форма не сохраняет owner | `form_valid`, вызван ли `super()` |
| `NoReverseMatch` | URL name/args, `get_success_url` |
| template не найден | `template_name`, app templates directory |
| queryset не фильтруется | реально ли вызывается ваш `get_queryset` |

## 7.11. Финальный checklist новой CRUD-сущности

1. Модель и миграция готовы.
2. Есть `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`.
3. `fields` не включает серверные поля.
4. Create назначает owner/parent/author на сервере.
5. Update/Delete/Detail ограничены scoped queryset.
6. Все POST формы имеют CSRF token.
7. Success даёт redirect.
8. Delete требует POST confirmation.
9. Есть permissions и проверка их у нужной группы.
10. URL names используются через `reverse`/`{% url %}`.
11. Написаны хотя бы owner/other/anonymous tests.
12. Выполнен `python manage.py check`.

## 7.12. Что читать дальше

После этой серии:

- официальную документацию по каждому классу через flattened index;
- исходный код Django в виртуальном окружении (`django/views/generic/`);
- [Classy Class-Based Views](https://ccbv.co.uk/) для MRO и методов;
- текущие `courses/views.py` и `students/views.py` проекта — как реальный
  материал для рефакторинга.
