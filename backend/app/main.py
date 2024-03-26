from fastapi import FastAPI
from sqlmodel import SQLModel, Session, select
from starlette.middleware.cors import CORSMiddleware

from app.database import engine, es
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
async def repositories():
    with Session(engine) as session:
        return session.exec(select(models.Repository)).all()


@app.get("/spotlight", response_model=list[models.Repository])
def spotlight():
    with Session(engine) as session:
        statement = (
            select(models.Repository)
            .order_by(models.Repository.highlighted.desc())
            .order_by(models.Repository.stars.desc())
            .limit(4)
        )
        return session.exec(statement).all()


@app.post("/repository", response_model=models.Repository)
async def repository(repo_url: str):
    with Session(engine) as session:
        statement = select(models.Repository).where(models.Repository.url == repo_url)
        return session.exec(statement).first()


@app.get("/search", response_model=list[models.Repository])
def search_pipelines(query: str):
    print("Perform Elasticsearch search")
    results = es.search(
        index="repositories",
        body={
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "description"],
                    "fuzziness": "AUTO",
                }
            }
        },
    )
    # Get the URLs of the repositories
    urls = [hit["_id"] for hit in results["hits"]["hits"]]
    print("Fetch the repositories from the database")
    with Session(engine) as session:
        statement = select(models.Repository).where(models.Repository.url.in_(urls))
        return session.exec(statement).all()


if __name__ == "__main__":
    # For debugging purposes only
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
