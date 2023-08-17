from pathlib import Path

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Here you should replace 'YOUR_DATABASE_URL' with your actual database connection string.
db_path = Path("metadata.db")
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL)
# Query the database and also manage the persistence of data.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Repository(Base):
    __tablename__ = "repositories"

    # id = Column(Integer, primary_key=True, index=True)
    url = Column(String, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)
    topics = Column(String)
    website = Column(String)
    stars = Column(Integer)
    watchers = Column(Integer)
    forks = Column(Integer)
    last_commit_date = Column(DateTime)
    number_of_releases = Column(Integer)
    latest_release_date = Column(DateTime)
    latest_release_name = Column(String)
    head_fork = Column(String)
    issues = Column(Integer)
    open_issues = Column(Integer)
    closed_issues = Column(Integer)
    prs = Column(Integer)
    open_prs = Column(Integer)
    closed_prs = Column(Integer)
    contributors = Column(Integer)
    nextflow_main_lang = Column(String)
    nextflow_code_chars = Column(Integer)
    languages = Column(String)
    # labels = Column(String)
    # categories = Column(String)
    # blacklisted = Column(Boolean)
