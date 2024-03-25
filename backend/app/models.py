import datetime

from sqlmodel import Field, SQLModel


class Repository(SQLModel, table=True):
    __tablename__ = "repositories"

    url: str = Field(primary_key=True)
    alive: bool = Field(default=True)
    highlighted: bool = Field(default=False)
    hidden: bool = Field(default=False)
    nf_files_in_root: str
    nf_files_in_subfolders: str
    title: str
    owner: str
    slugified_name: str
    description: str | None
    updated_at: datetime.datetime
    created_at: datetime.datetime
    topics: str
    website: str | None
    stars: int
    watchers: int
    forks: int
    number_of_releases: int
    head_fork: str | None
    open_issues: int
    open_prs: int
    nextflow_main_lang: bool
    nextflow_code_chars: int
    languages: str
    readme_name: str | None = None
    readme_contains_nextflow: bool | None = None


class FilteredRepository(SQLModel, table=True):
    __tablename__ = "filtered_repositories"

    url: str = Field(primary_key=True)
    exists: bool
    no_nf_files: bool | None = None


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    name: str
