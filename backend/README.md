Workflow catalog
---------------

Installation

```sh
virtualenv -p python3 venv
source venv/bin/activate
pip install -r requirements.txt
```

Initialise the database with the following command. It will read the list of repositories from the root README.md, and pull metadata using the GitHub API into a SQLite database.

```sh
export GITHUB_TOKEN=<your github token>
python -m app.init_db
```

Start the server backend with the following command:

```sh
source venv/bin/activate
uvicorn app.main:app --reload
```

To start the frontend, go to `../frontend` and run:

```sh
npm start
```
