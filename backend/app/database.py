import os
import dotenv
import elasticsearch

from sqlmodel import SQLModel, create_engine

dotenv.load_dotenv()

sql_url = os.getenv("DATABASE_URL")
assert sql_url is not None, sql_url
engine = create_engine(sql_url)

SQLModel.metadata.create_all(engine)

es = elasticsearch.Elasticsearch(
    cloud_id=os.getenv("ELASTICSEARCH_CLOUD_ID"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
)
