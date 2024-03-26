# Seqera Hub

Seqera Hub provides access to a curated list of public Nextflow pipelines, and the
ability
to export and run them using the Seqera Platform.

## Development

### Backend

The backend is implemented using FastAPI, backed by an SQL database and elasticsearch
index.

To set up the backend, first install the dependencies:

```sh
virtualenv venv
pip install -r requirements.txt
```

And set up the environment variables in a `.env` file:

```
AIRTABLE_BASE_ID=...
AIRTABLE_TOKEN=...
GITHUB_TOKEN=...
DATABASE_URL=sqlite:///repositories.db
ELASTICSEARCH_CLOUD_ID=...
ELASTICSEARCH_API_KEY=...
```

The database of pipelines is populated by scraping GitHub repositories. Use the
following
script to populate the database:

```sh
python app/scrape.py search_github  # will find a preliminary list of repositories with the keyword 'nextflow'
python app/scrape.py collect_metadata  # will collect extended metadata for each repository, filter and populate the database
python app/scrape.py to_airtable  # will populate an Airtable base with the collected metadata
python app/scrape.py create_es_index  # will create the elasticsearch index
```

After the database is set up, you can start the backend with the following command:

```sh
uvicorn app.main:app --host 0.0.0.0
```

### Frontend

The frontend is implemented using Next.js.

To set up the frontend, first install the dependencies:

```sh
npm install
```

And set up the environment variables in a `.env` file:

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8001
```

Then start the frontend with the following command:

```sh
npm run dev
```

