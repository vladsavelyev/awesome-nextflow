from sqlalchemy import Column, Integer, String, DateTime, Boolean

from .database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Populated through scraping
    url = Column(String, index=True)
    title = Column(String)
    description = Column(String)
    updated_at = Column(DateTime)
    created_at = Column(DateTime)
    not_available = Column(Boolean)
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
    any_nf_in_root = Column(Boolean)
    main_nf_in_root = Column(Boolean)
    nextflow_config_in_root = Column(Boolean)
    any_nf_in_subfolder = Column(Boolean)
    main_nf_in_subfolder = Column(Boolean)
    nextflow_config_in_subfolder = Column(Boolean)
    # Populated through UI
    labels = Column(String)
    categories = Column(String)
    blacklisted = Column(Boolean)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String)
