# ============================================================
# DATABASE.PY - Connect to the database
# ============================================================
# Creates the database engine and gives each API request
# a fresh database session (connection) to read/write data.
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import load_settings

app_settings = load_settings()

# Extra options depending on database type (SQLite vs PostgreSQL)
extra_db_options = {}
if app_settings.database_url.startswith("sqlite"):
    extra_db_options = {"check_same_thread": False}
elif app_settings.database_url.startswith("postgresql"):
    extra_db_options = {"sslmode": "require"}

# engine = main connection to database
engine = create_engine(
    app_settings.database_url,
    connect_args=extra_db_options,
    pool_pre_ping=True,
)

# SessionLocal = factory to open a new database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = parent class for all our table models (User, Student, etc.)
Base = declarative_base()


def get_db():
    """
    Open database connection for one API request, then close it.
    FastAPI calls this automatically with Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
