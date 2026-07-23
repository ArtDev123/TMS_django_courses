# Generic class-based views Django 6.0

Полный учебный раздел о встроенных class-based views (CBV) Django: жизненный
цикл запроса, ModelForm, CRUD, MRO, mixins, доступы, queryset, пагинация,
даты и практическое применение в Educa.

> Версия: Django 6.0. Код ориентирован на приложение этого репозитория, но
> паттерны применимы к обычным Django-проектам.

## Как читать

Начните с первых двух файлов: без жизненного цикла и MRO переопределение
методов в generic view превращается в запоминание рецептов. Затем переходите
к нужному классу view.

| Файл | Что внутри |
|---|---|
| [01-base-lifecycle.md](01-base-lifecycle.md) | `View`, `as_view()`, `setup()`, `dispatch()`, HTTP-методы, MRO |
| [02-display-views.md](02-display-views.md) | `TemplateView`, `RedirectView`, `ListView`, `DetailView`, queryset, pagination |
| [03-forms-and-editing.md](03-forms-and-editing.md) | `FormView`, `CreateView`, `UpdateView`, `DeleteView`, полный поток GET/POST |
| [04-mixins-auth-permissions.md](04-mixins-auth-permissions.md) | собственные mixins, `LoginRequiredMixin`, permissions, ownership, порядок наследования |
| [05-date-views.md](05-date-views.md) | `ArchiveIndexView`, year/month/week/day/today/date detail views |
| [06-practice-educa.md](06-practice-educa.md) | пошаговый практикум на моделях Educa, запуск, тестирование, отладка |
| [07-reference-cheatsheet.md](07-reference-cheatsheet.md) | таблицы выбора view, методы/атрибуты, ошибки, чеклисты |
| [08-urls-and-integration.md](08-urls-and-integration.md) | URLconf, converters, namespaces, `reverse()`, `as_view()`, URL-паттерны для всех CBV |
| [09-real-world-recipes.md](09-real-world-recipes.md) | production-рецепты: каталог, кабинет, блог, dashboard, поиск, файлы, API и multi-tenant |
| [10-local-educa-walkthrough.md](10-local-educa-walkthrough.md) | ручной прогон Educa: экраны, кнопки, URL, HTTP-методы и полный lifecycle реальных views |
| [11-educa-annotated-views.md](11-educa-annotated-views.md) | построчный разбор реальных views Educa: что делает код, когда вызывается и на каком экране видно результат |

## Что такое CBV

Обычная function-based view (FBV) — функция, которая принимает `request` и
возвращает `HttpResponse`.

```python
def course_list(request):
    courses = Course.objects.all()
    return render(request, "courses/course/list.html", {"courses": courses})
```

Class-based view — класс, экземпляр которого Django создаёт **для каждого
запроса**. Базовый класс и mixins уже реализуют повторяющиеся задачи:

- выбрать обработчик `get()` / `post()` по HTTP-методу;
- получить объект по `pk` или `slug`;
- получить список объектов;
- собрать контекст;
- выбрать шаблон;
- создать/провалидировать/сохранить форму;
- вернуть redirect после успешной операции.

Ваш код добавляет только предметную логику: фильтр «только мои курсы»,
подстановку владельца, дополнительные поля контекста или условия доступа.

### CBV как язык композиции

Generic view полезно воспринимать не как «магический класс, который рисует
страницу», а как договор о разделении обязанностей. Django берёт на себя
повторяющуюся механику HTTP: выбрать обработчик метода, создать форму,
получить объект, проверить валидность, выбрать template и вернуть response.
Разработчик формулирует правила конкретного продукта: какой Course доступен
студенту, кто становится owner нового объекта, какие данные вывести рядом с
модулем.

Именно поэтому generic views хорошо масштабируются в обычном CRUD, но
необязательно подходят для любого действия. Если экран одновременно редактирует
несколько formset, получает JSON от drag-and-drop или отдаёт файл, явный
`View` зачастую выражает задачу точнее. Цель CBV — убрать шаблонный код, а не
заставить все HTTP-ответы выглядеть одинаково.

## Быстрый запуск примеров

1. Активируйте окружение и примените миграции:

```bash
source .venv/bin/activate
python manage.py migrate
```

2. Запустите сервер:

```bash
python manage.py runserver
```

3. Для Django shell:

```bash
python manage.py shell
```

4. Проверяйте конфигурацию после изменений:

```bash
python manage.py check
python manage.py showmigrations
```

## Официальные источники

- [Base views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/base/)
- [Generic display views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-display/)
- [Generic editing views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-editing/)
- [Editing mixins](https://docs.djangoproject.com/en/6.0/ref/class-based-views/mixins-editing/)
- [Authentication mixins](https://docs.djangoproject.com/en/6.0/topics/auth/default/#the-loginrequiredmixin-mixin)
- [Flattened CBV index](https://docs.djangoproject.com/en/6.0/ref/class-based-views/flattened-index/)

## Главное правило

Перед тем как переопределять метод, ответьте на два вопроса:

1. На каком шаге жизненного цикла он вызывается?
2. Нужно ли сохранить базовое поведение через `super()`?

В большинстве случаев ответ на второй вопрос — **да**.

## Как читать примеры в этом разделе

У каждого значимого примера теперь нужно отвечать на четыре вопроса:

1. **Где на сайте это используется?** URL, роль и кнопка/экран.
2. **Когда код вызывается?** GET, POST, после валидации формы или перед
   рендером шаблона.
3. **Что уже сделал Django до этого метода?** Например, найден ли
   `self.object`, создана ли form, заполнены ли `self.kwargs`.
4. **Что произойдёт после?** SQL-запрос, template response, redirect,
   следующая view.

Если в примере метод не связан с экраном Educa напрямую, в нём указано
реальное место, где этот паттерн пригодится: каталог, CMS преподавателя,
материалы студента, тесты, профиль или будущая сущность Announcement.
