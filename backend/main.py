import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

import models, api


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "localhost:3000"
    ],
    allow_methods=["*"],
    allow_headers=["*"]
)


models.Base.metadata.create_all(bind=models.engine)

def get_db():
    db = models.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", tags=["root"])
def read_repositories(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return api.get_repositories(db, skip=skip, limit=limit)

@app.get("/repositories")
def read_repositories(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return api.get_repositories(db, skip=skip, limit=limit)

@app.get("/repositories/{repo_id}")
def read_repository(repo_id: int, db: Session = Depends(get_db)):
    return api.get_repository(db, repo_id)
