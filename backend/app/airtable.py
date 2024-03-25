import os

import dotenv
from pyairtable.orm import Model as AirtableModel, fields as F
from pyairtable import Api as AirtableApi
from sqlmodel import Session, select

from app.database import engine
from app.models import Repository

dotenv.load_dotenv()

airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
airtable_token = os.getenv("AIRTABLE_TOKEN")


# noinspection PyArgumentList
class RepositoryAirtable(AirtableModel):
    url = F.TextField("URL")
    alive = F.CheckboxField("Alive")
    highlighted = F.CheckboxField("Highlighted")
    hidden = F.CheckboxField("Hidden")
    nf_files_in_root = F.TextField(".nf files in root")
    nf_files_in_subfolders = F.TextField(".nf files in subfolders")
    comment = F.TextField("Comment")
    title = F.TextField("Title")
    owner = F.TextField("Owner")
    slugified_name = F.TextField("Slugified Name")
    description = F.TextField("Description")
    updated_at = F.DatetimeField("Updated at")
    created_at = F.DatetimeField("Created at")
    topics = F.TextField("Topics")
    website = F.TextField("Website")
    stars = F.IntegerField("Stars")
    watchers = F.IntegerField("Watchers")
    forks = F.IntegerField("Forks")
    number_of_releases = F.IntegerField("Number of releases")
    head_fork = F.TextField("Head fork")
    open_issues = F.IntegerField("Open issues")
    open_prs = F.IntegerField("Open PRs")
    nextflow_main_lang = F.CheckboxField("Nextflow is main language")
    nextflow_code_chars = F.IntegerField("Nextflow code characters")
    languages = F.TextField("Languages")
    readme_name = F.TextField("Readme file name")
    readme_contains_nextflow = F.CheckboxField("Readme contains Nextflow")

    class Meta:
        base_id = airtable_base_id
        api_key = airtable_token
        table_name = "Repositories"


def init_airtable():
    api = AirtableApi(airtable_token)
    base = api.base(airtable_base_id)
    tables = base.tables()

    def _create_table(model_class):
        fields = []
        for k, field in model_class.__dict__.items():
            if isinstance(field, F.CheckboxField):
                fields.append(
                    {
                        "name": field.field_name,
                        "type": "checkbox",
                        "options": {"color": "greenBright", "icon": "check"},
                    }
                )
            elif isinstance(field, F.DatetimeField):
                fields.append(
                    {
                        "name": field.field_name,
                        "type": "dateTime",
                        "options": {
                            "timeZone": "utc",
                            "dateFormat": {
                                "format": "LL",
                                "name": "friendly",
                            },
                            "timeFormat": {
                                "format": "HH:mm",
                                "name": "24hour",
                            },
                        },
                    }
                )
            elif isinstance(field, F.IntegerField):
                fields.append(
                    {
                        "name": field.field_name,
                        "type": "number",
                        "options": {"precision": 0},
                    }
                )
            elif isinstance(field, F.TextField):
                fields.append(
                    {
                        "name": field.field_name,
                        "type": "singleLineText",
                    }
                )
        base.create_table(model_class.Meta.table_name, fields=fields)

    if "Repositories" not in [t.name for t in tables]:
        _create_table(RepositoryAirtable)


def db_to_airtable():
    """
    Load the metadata from the SQLite database and insert it into the Airtable.
    """
    init_airtable()

    with Session(engine) as session:
        repos = session.exec(select(Repository)).all()
        entries = []
        for repo in repos:
            if repo.alive and repo.stars >= 2:
                entries.append(RepositoryAirtable(**repo.model_dump()))

    RepositoryAirtable.batch_save(entries)
    print(f"Saved {len(entries)} entries to Airtable table 'Repositories'")
