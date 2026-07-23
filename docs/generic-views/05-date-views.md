# 5. Date-based generic views

[← Mixins и доступы](04-mixins-auth-permissions.md) · [Оглавление](README.md) · [Далее: практикум Educa →](06-practice-educa.md)

Date-based views строят архивы по `DateField`/`DateTimeField`. Они нужны для
блога, новостей, журналов событий, истории объявлений, публикаций.

Для LMS они полезны, если появится публичная новостная лента платформы или
архив объявлений преподавателя.

## 5.1. Базовый набор

| View | Что показывает |
|---|---|
| `ArchiveIndexView` | все объекты, отсортированные по дате |
| `YearArchiveView` | объекты за год и список месяцев |
| `MonthArchiveView` | объекты за месяц и список дней |
| `WeekArchiveView` | объекты за ISO-неделю |
| `DayArchiveView` | объекты за день |
| `TodayArchiveView` | объекты за текущий день |
| `DateDetailView` | один объект по дате + slug/pk |

Все требуют указать `date_field`.

## 5.2. Модель-пример

```python
class PlatformNews(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    body = models.TextField()
    published_at = models.DateTimeField()
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at"]
```

Для `DateTimeField` важно учитывать `USE_TZ=True` и текущую timezone.

## 5.3. `ArchiveIndexView`

```python
from django.views.generic.dates import ArchiveIndexView


class NewsArchiveView(ArchiveIndexView):
    model = PlatformNews
    date_field = "published_at"
    template_name = "news/archive.html"
    context_object_name = "news"
    paginate_by = 20

    def get_queryset(self):
        return PlatformNews.objects.filter(is_published=True)
```

Поток похож на `ListView`: `get_queryset()` → контекст → шаблон. Дополнительно
`DateMixin` знает, какое поле даты использовать.

Контекст включает `latest` (и `object_list`), а с pagination — обычные
`page_obj`, `paginator`, `is_paginated`.

## 5.4. Год, месяц, неделя, день

```python
from django.views.generic.dates import (
    YearArchiveView, MonthArchiveView, WeekArchiveView, DayArchiveView,
)


class NewsYearView(YearArchiveView):
    queryset = PlatformNews.objects.filter(is_published=True)
    date_field = "published_at"
    make_object_list = True


class NewsMonthView(MonthArchiveView):
    queryset = PlatformNews.objects.filter(is_published=True)
    date_field = "published_at"
    month_format = "%m"


class NewsWeekView(WeekArchiveView):
    queryset = PlatformNews.objects.filter(is_published=True)
    date_field = "published_at"


class NewsDayView(DayArchiveView):
    queryset = PlatformNews.objects.filter(is_published=True)
    date_field = "published_at"
```

### `make_object_list`

`YearArchiveView` по умолчанию показывает периоды (месяцы), но не обязательно
все объекты года. `make_object_list=True` добавляет `object_list`.

### `allow_future`

По умолчанию будущие даты не показываются. Для планировщика преподавателя
можно:

```python
allow_future = True
```

Для публичных новостей это обычно опасно: черновик с будущей датой окажется
доступен раньше публикации. Ограничивайте и queryset (`is_published=True`).

### `allow_empty`

`False` превращает пустой период в 404. Для SEO-архива это иногда разумно,
для внутренних календарей — обычно нет.

## 5.5. URL-конфигурация

```python
urlpatterns = [
    path("", NewsArchiveView.as_view(), name="news_archive"),
    path("<int:year>/", NewsYearView.as_view(), name="news_year"),
    path("<int:year>/<str:month>/", NewsMonthView.as_view(), name="news_month"),
    path(
        "<int:year>/week/<int:week>/",
        NewsWeekView.as_view(),
        name="news_week",
    ),
    path(
        "<int:year>/<int:month>/<int:day>/",
        NewsDayView.as_view(),
        name="news_day",
    ),
]
```

Параметры URL должны совпасть с тем, что ожидает view. Для ISO-недели
`WeekArchiveView` ожидает `week`; для месяца формат определяет `month_format`.

## 5.6. `DateDetailView`

Полезна, когда URL содержит дату и slug:

```python
from django.views.generic.dates import DateDetailView


class NewsDetailView(DateDetailView):
    model = PlatformNews
    date_field = "published_at"
    month_format = "%m"
    template_name = "news/detail.html"

    def get_queryset(self):
        return PlatformNews.objects.filter(is_published=True)
```

URL:

```python
path(
    "<int:year>/<int:month>/<int:day>/<slug:slug>/",
    NewsDetailView.as_view(),
    name="news_detail",
)
```

View фильтрует по дате и `slug`/`pk`; это защищает от совпадений slug,
если slug уникален только внутри даты.

## 5.7. Навигация между периодами

Date views добавляют в контекст данные периодов (зависит от конкретного
класса), например `date_list`, `year`, `month`, `week`, `day`,
`previous_month`, `next_month`.

Не предполагайте имена по памяти: для используемого класса сверяйте
официальную документацию или выводите `context.keys()` во время разработки.

Пример ссылки:

```django
{% if previous_month %}
  <a href="{% url 'news_month' previous_month|date:'Y' previous_month|date:'m' %}">
    Предыдущий месяц
  </a>
{% endif %}
```

На практике удобнее создать template tag для date URL, чтобы не смешивать
форматирование дат и URL-логику в шаблоне.

## 5.8. Когда date views не подходят

Не используйте их, если:

- дата — только один из многих фильтров сложной аналитики;
- нужна календарная сетка с бронированиями;
- запрос должен включать permission scope пользователя;
- объект выбирается только по UUID, дата в URL не нужна.

Тогда начните с `ListView`/`DetailView` и добавьте собственные фильтры.

## 5.9. Практика

1. Создайте публичную `PlatformNews`.
2. Добавьте `ArchiveIndexView` и `MonthArchiveView`.
3. Показывайте только `is_published=True`.
4. Убедитесь, что объект с будущей датой не доступен.
5. Добавьте `DateDetailView` с годом, месяцем, днём и slug в URL.

## Документация Django

- [Date-based generic views](https://docs.djangoproject.com/en/6.0/ref/class-based-views/generic-date-based/)
- [Date-based mixins](https://docs.djangoproject.com/en/6.0/ref/class-based-views/mixins-date-based/)
- [Time zones](https://docs.djangoproject.com/en/6.0/topics/i18n/timezones/)
