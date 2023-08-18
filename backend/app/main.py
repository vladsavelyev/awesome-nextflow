from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from . import crud, models, schemas
from .database import SessionLocal, engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://localhost:8001"],
    allow_methods=["*"],
    allow_headers=["*"]
)

models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", tags=["root"])
async def read_repos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_repos(db, skip=skip, limit=limit)


@app.get("/repositories")
async def read_repos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_repos(db, skip=skip, limit=limit)


@app.get("/repositories/{repo_id}")
async def read_repo(repo_id: int, db: Session = Depends(get_db)):
    return crud.get_repo(db, repo_id)


@app.post("/repositories", response_model=schemas.Repository)
async def create_repo(repo: schemas.RepositoryCreate, db: Session = Depends(get_db)):
    return crud.create_repo(db=db, repo=repo)


@app.post("/repositories/{repo_id}/labels")
async def add_label(repo_id: int, label: str, db: Session = Depends(get_db)):
    return crud.add_label(db=db, repo_id=repo_id, label=label)


@app.post("/repositories/{repo_id}/categories")
async def add_category(repo_id: int, category: str, db: Session = Depends(get_db)):
    return crud.add_category(db=db, repo_id=repo_id, category=category)


@app.delete("/repositories/{repo_id}/labels")
async def remove_label(repo_id: int, label: str, db: Session = Depends(get_db)):
    return crud.remove_label(db=db, repo_id=repo_id, label=label)


@app.delete("/repositories/{repo_id}/categories")
async def remove_category(repo_id: int, category: str, db: Session = Depends(get_db)):
    return crud.remove_category(db=db, repo_id=repo_id, category=category)


@app.post("/repositories/{repo_id}/blacklist")
async def blacklist_repo(repo_id: int, db: Session = Depends(get_db)):
    return crud.blacklist_repo(db=db, repo_id=repo_id)


if __name__ == "__main__":
    # For debugging purposes only
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
