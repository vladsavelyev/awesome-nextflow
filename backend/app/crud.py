from sqlalchemy.orm import Session

from . import models, schemas


def get_repos(db: Session, skip: int = 0, limit: int = 10) -> list:
    # return db.query(models.Repository).offset(skip).limit(limit).all()
    return db.query(models.Repository).all()


def get_repo(db: Session, repo_id: int):
    return db.query(models.Repository).filter(models.Repository.id == repo_id).first()


def create_repo(db: Session, repo: schemas.RepositoryCreate):
    db_repo = models.Repository(
        url=repo.url,
        labels=repo.labels,
        categories=repo.categories,
        blacklisted=repo.blacklisted,
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def add_label(db: Session, repo_id: int, label: str):
    repo = get_repo(db, repo_id)
    repo.labels.append(label)
    db.commit()
    return repo


def add_category(db: Session, repo_id: int, category: str):
    repo = get_repo(db, repo_id)
    repo.categories.append(category)
    db.commit()
    db.refresh(repo)
    return repo


def remove_label(db: Session, repo_id: int, label: str):
    repo = get_repo(db, repo_id)
    repo.labels.remove(label)
    db.commit()
    db.refresh(repo)
    return repo


def remove_category(db: Session, repo_id: int, category: str):
    repo = get_repo(db, repo_id)
    repo.categories.remove(category)
    db.commit()
    db.refresh(repo)
    return repo


def blacklist_repo(db: Session, repo_id: int):
    repo = get_repo(db, repo_id)
    repo.blacklisted = True
    db.commit()
    db.refresh(repo)
    return repo
