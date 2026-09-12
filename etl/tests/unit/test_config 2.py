from psycopg.conninfo import conninfo_to_dict
from sqlalchemy.engine import make_url

from services.config import Settings


def test_connection_parts_are_shared_and_password_is_escaped():
    settings = Settings(
        _env_file=None, database_url=None, pg_dsn=None,
        postgres_user="custom_user", postgres_password="a@b:/?#%$",
        postgres_host="custom-db", postgres_port=5433, postgres_db="custom_db",
    )
    sqlalchemy = make_url(settings.sqlalchemy_url)
    libpq = conninfo_to_dict(settings.pg_dsn)
    assert sqlalchemy.password == libpq["password"] == "a@b:/?#%$"
    assert sqlalchemy.host == libpq["host"] == "custom-db"
    assert sqlalchemy.port == int(libpq["port"]) == 5433
    assert sqlalchemy.database == libpq["dbname"] == "custom_db"
    assert sqlalchemy.username == libpq["user"] == "custom_user"


def test_explicit_urls_and_test_database_override_remain_supported():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://u:p@explicit:5432/warehouse",
        pg_dsn="postgresql+psycopg://u:p@explicit:5432/warehouse",
    )
    assert make_url(settings.sqlalchemy_url).host == "explicit"
    assert conninfo_to_dict(settings.pg_dsn)["host"] == "explicit"
    test_settings = settings.with_pg_dsn("postgresql://t:p@test-db:5432/tests")
    assert make_url(test_settings.sqlalchemy_url).database == "tests"
    assert conninfo_to_dict(test_settings.pg_dsn)["dbname"] == "tests"
