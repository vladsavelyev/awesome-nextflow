from fastapi import FastAPI
from sqlmodel import SQLModel, Session, select
from starlette.middleware.cors import CORSMiddleware

from app.database import engine
from . import models

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_db_and_tables() -> None:
    """Create the database and tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


@app.get("/", tags=["root"])
async def read_repositories():
    with Session(engine) as session:
        return session.exec(select(models.Repository)).all()


@app.post("/repositories", response_model=models.Repository)
async def read_repository(repo_url: str):
    with Session(engine) as session:
        statement = select(models.Repository).where(models.Repository.url == repo_url)
        return session.exec(statement).first()


if __name__ == "__main__":
    # For debugging purposes only
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
