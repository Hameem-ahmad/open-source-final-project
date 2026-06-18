from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import load_settings

app_settings = load_settings()
extra_db_options = {}
if app_settings.database_url.startswith("sqlite"):
    extra_db_options = {"check_same_thread": False}
elif app_settings.database_url.startswith("postgresql"):
    extra_db_options = {"sslmode": "require"}
engine = create_engine(
    app_settings.database_url,
    connect_args=extra_db_options,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
