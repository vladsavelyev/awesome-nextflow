from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

db_path = Path(__file__) / ".." / ".." / "metadata.db"
database_url = f"sqlite:///{db_path}"
# database_url = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    database_url, 
    connect_args={"check_same_thread": False}  # Only for SQLite
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
