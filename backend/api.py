from sqlalchemy.orm import Session
from models import Repository


def get_repositories(db: Session, skip: int = 0, limit: int = 10):
    return db.query(Repository).offset(skip).limit(limit).all()


def get_repository(db: Session, repo_id: int):
    return db.query(Repository).filter(Repository.id == repo_id).first()


def blacklist_repository(db: Session, repo_id: int):
    repo = get_repository(db, repo_id)
    repo.blacklisted = True
    db.commit()
    return repo

