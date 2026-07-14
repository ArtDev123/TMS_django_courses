# TMS_django_courses — платформа онлайн-курсов (Django 6)

## Запуск

```bash
# PostgreSQL (один раз) — через Unix-сокет, без пароля postgres:
sudo -u postgres psql -v ON_ERROR_STOP=1 -f scripts/init_postgres.sql


# Окружение
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Миграции
python manage.py migrate
python manage.py loaddata subjects.json
python manage.py createsuperuser

# Сервер
python manage.py runserver
```

## Структура

```text
TMS_django_courses/
├── manage.py
├── educa/          # настройки Django
├── courses/        # курсы, CMS, контент
├── students/       # регистрация, прогресс, викторины, сертификаты
├── scripts/        # init_postgres.sql
└── guide.md        # документация
```

Подробный гайд: [docs/guide.md](docs/guide.md)  
**Оставшаяся реализация (пошагово):** [docs/remaining/README.md](docs/remaining/README.md)
