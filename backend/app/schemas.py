"""
Define pydantic schemas for the API.
"""

from pydantic import BaseModel


class RepositoryBase(BaseModel):
    url: str
    labels: list[str] = []
    categories: list[str] = []
    blacklisted: bool


class RepositoryCreate(RepositoryBase):
    pass


class Repository(RepositoryBase):
    id: int
    url: str
    title: str
    description: str
    updated_at: str
    created_at: str
    not_available: bool
    topics: str
    website: str
    stars: int
    watchers: int
    forks: int
    last_commit_date: str
    number_of_releases: int
    latest_release_date: str
    latest_release_name: str
    head_fork: str
    issues: int
    open_issues: int
    closed_issues: int
    prs: int
    open_prs: int
    closed_prs: int
    contributors: int
    nextflow_main_lang: str
    nextflow_code_chars: int
    languages: str
    any_nf_in_root: bool
    main_nf_in_root: bool
    nextflow_config_in_root: bool
    any_nf_in_subfolder: bool
    main_nf_in_subfolder: bool
    nextflow_config_in_subfolder: bool

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    name: str
    
    
class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int

    class Config:
        orm_mode = True
