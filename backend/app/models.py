from sqlalchemy import Column, Integer, String, DateTime, Boolean

from .database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Populated through scraping
    url = Column(String, index=True)
    title = Column(String)
    owner = Column(String)
    name = Column(String)
    description = Column(String)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)
    can_not_pull = Column(Boolean)
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
    nf_files_in_root = Column(String)
    nf_files_in_subfolders = Column(String)
    # readme_name = Column(String)
    # readme_contains_nextflow = Column(Boolean)
    # readme_contents = Column(String)
    # Populated through UI
    labels = Column(String)
    categories = Column(String)
    blacklisted = Column(Boolean)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
