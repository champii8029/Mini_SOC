from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./soc.db"
# Usamos check_same_thread=False porque FastAPI usa multiples threads y SQLite por defecto restringe esto
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar la sesi\u00f3n en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
