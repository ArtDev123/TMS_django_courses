-- Скрипт создания БД и пользователя для платформы онлайн-курсов (educa).
-- PostgreSQL на хосте, порт 5432.
--
-- Запуск (peer auth, без пароля postgres):
--   sudo -u postgres psql -f scripts/init_postgres.sql
--
-- Или из каталога проекта:
--   sudo -u postgres psql -v ON_ERROR_STOP=1 -f /path/to/scripts/init_postgres.sql
--
-- Пароль educa_user должен совпадать с DB_PASSWORD в .env:
--   DB_PASSWORD=educa_secret_change_me

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'educa_user') THEN
        CREATE USER educa_user WITH PASSWORD 'educa_secret_change_me';
    ELSE
        ALTER USER educa_user WITH PASSWORD 'educa_secret_change_me';
    END IF;
END
$$;

SELECT 'CREATE DATABASE educa OWNER educa_user ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'educa')\gexec

GRANT CONNECT ON DATABASE educa TO educa_user;

\c educa

GRANT ALL PRIVILEGES ON SCHEMA public TO educa_user;
GRANT CREATE ON SCHEMA public TO educa_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO educa_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO educa_user;
