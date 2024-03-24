#!/usr/bin/env python

"""
Collect metadata for the awesome repositories, initialise and populate the database
"""

import calendar
import datetime
import os
import time
from pathlib import Path
from traceback import print_exc

import pandas as pd
from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException
import fire
import humanize
from sqlmodel import Field, SQLModel, Session, create_engine, select
from pyairtable.orm import Model as AirtableModel, fields as F
from pyairtable import Api as AirtableApi
import dotenv

dotenv.load_dotenv()

airtable_base_id = os.getenv("AIRTABLE_BASE_ID")
airtable_token = os.getenv("AIRTABLE_TOKEN")
github_token = os.getenv("GITHUB_TOKEN")


README_PATH = "../README.md"
BLACKLIST = [
    "nextflow-io",
    "nf-core/modules",
    "nf-core/tools",
    "nf-core/configs",
]

os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"  # Do not clone LFS files
g = Github(github_token)


class FilteredRepositorySQLModel(SQLModel, table=True):
    __tablename__ = "filteredrepo"

    url: str = Field(primary_key=True)
    exists: bool
    no_nf_files: bool | None = None


class RepositorySQLModel(SQLModel, table=True):
    __tablename__ = "repo"

    url: str = Field(primary_key=True)
    exists: bool
    nf_files_in_root: str
    nf_files_in_subfolders: str
    title: str
    owner: str
    slugified_name: str
    description: str | None
    updated_at: datetime.datetime
    created_at: datetime.datetime
    topics: str
    website: str | None
    stars: int
    watchers: int
    forks: int
    last_commit_date: datetime.datetime
    number_of_releases: int
    latest_release_date: datetime.datetime | None = None
    latest_release_name: str | None = None
    head_fork: str | None
    issues: int
    open_issues: int
    closed_issues: int
    prs: int
    open_prs: int
    closed_prs: int
    contributors: int
    nextflow_main_lang: bool
    nextflow_code_chars: int
    languages: str
    readme_name: str | None = None
    readme_contains_nextflow: bool | None = None


engine = create_engine("sqlite:///repositories.db")
SQLModel.metadata.create_all(engine)


class FilteredRepositoryAirtable(AirtableModel):
    url = F.TextField("URL")
    alive = F.CheckboxField("Alive")
    no_nf_files = F.CheckboxField("No .nf files")

    class Meta:
        base_id = airtable_base_id
        api_key = airtable_token
        table_name = "Filtered repositories"


class RepositoryAirtable(AirtableModel):
    url = F.TextField("URL")
    alive = F.CheckboxField("Alive")
    validated = F.CheckboxField("Valid")
    highlighted = F.CheckboxField("Highlighted")
    is_nf_core = F.CheckboxField("nf-core")
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
    last_commit_date = F.DatetimeField("Last commit date")
    number_of_releases = F.IntegerField("Number of releases")
    latest_release_date = F.DatetimeField("Latest release date")
    latest_release_name = F.TextField("Latest release name")
    head_fork = F.TextField("Head fork")
    issues = F.IntegerField("Issues")
    open_issues = F.IntegerField("Open issues")
    closed_issues = F.IntegerField("Closed issues")
    prs = F.IntegerField("PRs")
    open_prs = F.IntegerField("Open PRs")
    closed_prs = F.IntegerField("Closed PRs")
    contributors = F.IntegerField("Contributors")
    nf_files_in_root = F.TextField(".nf files in root")
    nf_files_in_subfolders = F.TextField(".nf files in subfolders")
    nextflow_main_lang = F.CheckboxField("Nextflow is main language")
    nextflow_code_chars = F.IntegerField("Nextflow code characters")
    languages = F.TextField("Languages")
    readme_name = F.TextField("Readme file name")
    readme_contains_nextflow = F.CheckboxField("Readme contains Nextflow")

    class Meta:
        base_id = airtable_base_id
        api_key = airtable_token
        table_name = "Repositories"


def find_metadata_for_urls(
    urls: list[str],
    save_readme=False,
    filter_having_nf_files=False,
):
    """
    Get metadata for each repo and filter to those having *.nf files in the root
    or on the first level. Add found URLs to the table.
    """
    for i, url in enumerate(urls):
        with Session(engine) as session:
            repo = session.exec(
                select(RepositorySQLModel).where(RepositorySQLModel.url == url)
            ).first()
            if repo:
                print(f"{i + 1:04d}/{len(urls)}: {url:<80} already in the database")
                continue
            repo = session.exec(
                select(FilteredRepositorySQLModel).where(
                    FilteredRepositorySQLModel.url == url
                )
            ).first()
            if repo:
                print(
                    f"{i + 1:04d}/{len(urls)}: {url:<80} already in the filtered table"
                )
                continue

            print(f"{i + 1:04d}/{len(urls)}: {url:<80}", end=" ")
            try:
                repo: RepositorySQLModel | FilteredRepositorySQLModel = (
                    _collect_repo_metadata(
                        url,
                        save_readme=save_readme,
                        filter_having_nf_files=filter_having_nf_files,
                    )
                )
            except RateLimitExceededException:
                print("❌rate limit uncaught:")
                print_exc()
            except Exception as e:
                print(f"❌error: {e}")
                print_exc()
            else:
                session.add(repo)
                session.commit()


class Scraper:
    """
    Usage: python scrape.py scrape --out_path scraped.csv --limit 100
    """

    @staticmethod
    def scrape():
        """
        Search for repositories with "Nextflow" in the README, collect metadata on the
        found repositories, filter them, and write the metadata to a CSV.
        """
        print("Step 1: GitHub search for alive repos with 'nextflow' in README")
        search_dir = Path("github-search")
        if search_dir.exists():
            print(f"Directory {search_dir} already exists, delete to re-search")
        else:
            search_gh(out_dir=search_dir)

        urls = []
        for csv_path in search_dir.glob("*.tsv"):
            with csv_path.open() as f:
                df = pd.read_csv(f, sep="\t")
                urls.extend(df.url)

        print(f"Step 2: collecting metadata for found {len(urls)} repos")
        find_metadata_for_urls(
            urls,
            save_readme=True,
            filter_having_nf_files=True,
        )

    @staticmethod
    def read_readme():
        """
        Parse the README.md file, collect metadata on the found repositories, and
        write the metadata to a CSV.
        """
        urls = []
        with Path(README_PATH).open() as f:
            for line in f:
                if line.startswith("Tutorials"):
                    break
                if line.startswith("* ["):
                    url = line.split("(")[1].split(")")[0]
                    urls.append(url)

        find_metadata_for_urls(urls, save_readme=True, filter_having_nf_files=False)

    @staticmethod
    def to_airtable():
        """
        Load the metadata from the SQLite database and insert it into the Airtable.
        """
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

        if "Filtered repositories" not in [t.name for t in tables]:
            _create_table(FilteredRepositoryAirtable)
        if "Repositories" not in [t.name for t in tables]:
            _create_table(RepositoryAirtable)

        with Session(engine) as session:
            bad_repos = session.exec(select(FilteredRepositorySQLModel)).all()
            entries = []
            for repo in bad_repos:
                d = repo.model_dump()
                d["alive"] = repo.exists
                del d["exists"]
                entries.append(FilteredRepositoryAirtable(**d))
            FilteredRepositoryAirtable.batch_save(entries)
            print(
                f"Saved {len(entries)} entries to Airtable table 'Filtered repositories'"
            )

            repos = session.exec(select(RepositorySQLModel)).all()
            entries = []
            for repo in repos:
                d = repo.model_dump()
                d["alive"] = repo.exists
                del d["exists"]
                entries.append(RepositoryAirtable(**d))
            RepositoryAirtable.batch_save(entries)
            print(f"Saved {len(entries)} entries to Airtable table 'Repositories'")


def get_rate_limit(api_type):
    return getattr(g.get_rate_limit(), api_type)


def rate_limit_wait(api_type):
    curr_timestamp = calendar.timegm(time.gmtime())
    reset_timestamp = calendar.timegm(get_rate_limit(api_type).reset.timetuple())
    # add 5 seconds to be sure the rate limit has been reset
    sleep_time = max(0, reset_timestamp - curr_timestamp) + 5
    print(f"Rate limit exceeded, waiting {sleep_time} seconds")
    time.sleep(sleep_time)


def call_rate_aware(func, api_type="core"):
    while True:
        try:
            return func()
        except RateLimitExceededException:
            rate_limit_wait(api_type)


def call_rate_aware_decorator(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException:
                rate_limit_wait("core")

    return inner


@call_rate_aware_decorator
def check_repo_exists(g, full_name):
    try:
        g.get_repo(full_name)
        return True
    except UnknownObjectException:
        print(f"Repo {full_name} has been deleted")
        return False


@call_rate_aware_decorator
def check_file_exists(repo, file_name):
    try:
        repo.get_contents(file_name)
        return True
    except UnknownObjectException:
        return False


def get_language_percentages(repo):
    languages = repo.get_languages()
    total_bytes = sum(languages.values())
    return {lang: (bytes / total_bytes) * 100 for lang, bytes in languages.items()}


def _collect_repo_metadata(
    url, save_readme=False, filter_having_nf_files=False
) -> RepositorySQLModel | FilteredRepositorySQLModel:
    """
    Collect repository selection criteria and metadata for the spreadsheet:
    https://docs.google.com/document/d/1kZWOBbIt9pY_wloCGcH2d9vYD4zgaTT7x-vTewu0eeA
    """
    if url.startswith("http"):
        short_url = "/".join(url.split("/")[-2:])
    else:
        short_url = url
    d = {"url": url}

    try:
        repo = call_rate_aware(lambda: g.get_repo(short_url))
    except UnknownObjectException:
        print(f"❌error: repo {short_url} does not exist")
        d["exists"] = False
        return FilteredRepositorySQLModel(**d)

    d["exists"] = True
    nf_files_in_root = []
    nf_files_in_subfolders = []
    for f in call_rate_aware(lambda: repo.get_contents("")):
        if f.type == "file":
            if f.name.endswith(".nf"):
                nf_files_in_root.append(f.path)
                break
        elif f.type == "dir":  # One level deeper
            for f1 in call_rate_aware(lambda: repo.get_contents(f.path)):
                if f1.type == "file":
                    if f1.name.endswith(".nf"):
                        nf_files_in_subfolders.append(f1.path)
                        break

    if filter_having_nf_files and not nf_files_in_root and not nf_files_in_subfolders:
        print("❌skipping: no *.nf file found in root or 2nd level")
        d["no_nf_files"] = True
        return FilteredRepositorySQLModel(**d)

    d["nf_files_in_root"] = ", ".join(nf_files_in_root)
    d["nf_files_in_subfolders"] = ", ".join(nf_files_in_subfolders)

    d["url"] = call_rate_aware(lambda: repo.html_url)  # clickable URL
    d["title"] = call_rate_aware(lambda: repo.name)
    d["owner"] = call_rate_aware(lambda: repo.owner.login)
    d["slugified_name"] = f"{d['title']}--{d['owner']}"
    d["description"] = call_rate_aware(lambda: repo.description)
    d["updated_at"] = call_rate_aware(lambda: repo.updated_at)
    d["created_at"] = call_rate_aware(lambda: repo.created_at)
    d["topics"] = ", ".join(call_rate_aware(lambda: repo.get_topics()))
    d["website"] = call_rate_aware(lambda: repo.homepage)
    d["stars"] = call_rate_aware(lambda: repo.stargazers_count)
    d["watchers"] = call_rate_aware(lambda: repo.watchers_count)
    d["forks"] = call_rate_aware(lambda: repo.forks_count)
    d["last_commit_date"] = call_rate_aware(
        lambda: repo.get_commits().reversed[0].commit.committer.date
    )
    releases = call_rate_aware(lambda: repo.get_releases())
    d["number_of_releases"] = call_rate_aware(lambda: releases.totalCount)
    if d["number_of_releases"]:
        latest = call_rate_aware(lambda: releases.reversed[0])
        d["latest_release_date"] = call_rate_aware(lambda: latest.created_at)
        d["latest_release_name"] = call_rate_aware(lambda: latest.title)
    d["head_fork"] = call_rate_aware(
        lambda: repo.parent.full_name if repo.parent else None
    )
    d["issues"] = call_rate_aware(lambda: repo.get_issues().totalCount)
    d["open_issues"] = call_rate_aware(lambda: repo.get_issues(state="open").totalCount)
    d["closed_issues"] = call_rate_aware(
        lambda: repo.get_issues(state="closed").totalCount
    )
    d["prs"] = call_rate_aware(lambda: repo.get_pulls().totalCount)
    d["open_prs"] = call_rate_aware(lambda: repo.get_pulls(state="open").totalCount)
    d["closed_prs"] = call_rate_aware(lambda: repo.get_pulls(state="closed").totalCount)
    d["contributors"] = call_rate_aware(lambda: repo.get_contributors().totalCount)
    # d["clones"] = repo.get_clones_traffic()["count"]  # must have push access
    # d["unique_clones"] = repo.get_clones_traffic()["uniques"]  # must have push access
    # d["repo_views"] = repo.get_views_traffic()["count"]  # must have push access
    # d["unique_repo_views"] = repo.get_views_traffic()["uniques"]  # must have push access

    d["nextflow_main_lang"] = call_rate_aware(lambda: repo.language) == "Nextflow"
    d["nextflow_code_chars"] = call_rate_aware(
        lambda: repo.get_languages().get("Nextflow", 0)
    )
    d["languages"] = ", ".join(
        f"{n}: {c:.2f}%"
        for n, c in call_rate_aware(lambda: get_language_percentages(repo)).items()
    )

    if save_readme:
        # Locate README (can be README.md, README.rst, README.txt, etc.)
        # and save it to repos/repo-name/README.md
        readme = None
        if check_file_exists(repo, "README.md"):
            readme = call_rate_aware(lambda: repo.get_contents("README.md"))
        else:
            for f in call_rate_aware(lambda: repo.get_contents("")):
                if f.type == "file" and f.name.split(".")[0] == "README":
                    readme = f
        if readme:
            d["readme_name"] = readme.name
            try:
                readme_content = readme.decoded_content.decode()
            except Exception as r:
                print(f"⚠️ error parsing {readme.name}: {r}", end=" ")
            else:
                d["readme_contains_nextflow"] = "nextflow" in readme_content.lower()
                # Save readme to repos/repo-name/README.md
                readme_path = Path("readmes") / d["slugified_name"] / readme.name
                readme_path.parent.mkdir(parents=True, exist_ok=True)
                with readme_path.open("w") as f:
                    f.write(readme_content)

    print("👌")
    return RepositorySQLModel(**d)


def _process_github_search_result(paginated_list, count: int, out_dir: Path, date: str):
    out_path = out_dir / f"repos-{date}.tsv"
    if out_path.exists():
        print(f"File {out_path} already exists, delete to re-search for {date}")
        return

    # Iterate over search results and retrieve repo details
    page_idx = 0
    repo_num = 0
    repo_infos = []
    while True:
        print(f"Processing page {page_idx + 1}...")
        repos = call_rate_aware(
            lambda: paginated_list.get_page(page_idx), api_type="search"
        )
        page_idx += 1
        if not repos:
            break

        for repo in repos:
            repo_num += 1
            print(
                f"{date}: {repo_num:<3}/{count:<3}. Checking {repo.full_name:<80} "
                f"last updated {humanize.naturaldate(repo.updated_at):<20} "
                f"{repo.stargazers_count} stars... ",
                end="",
            )
            if repo.owner.login in BLACKLIST:
                print(f"❌ Repo owner {repo.owner.login} is blacklisted")
                continue
            elif repo.full_name in BLACKLIST:
                print(f"❌ Repo {repo.full_name} is blacklisted")
                continue
            print("👌")
            repo_infos.append(
                {
                    "name": repo.full_name,
                    "url": repo.html_url,
                    "last_updated": repo.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "stars": repo.stargazers_count,
                    "issues": -1,
                }
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Appending {len(repo_infos)} entries to file {out_path}...")
    df = pd.DataFrame(repo_infos)
    df.to_csv(out_path, index=False, sep="\t", header=True)


def search_gh(out_dir: Path):
    """
    Search for GitHub repositories that mention "nextflow" in README.

    GitHub returns only top 1000 entries, so we work around by searching year
    by each year, or month by month or day by date if needed, and concatenate.
    """
    base_query = "nextflow in:readme archived:false"
    for year in range(2015, datetime.datetime.today().year + 1):
        print(f"Searching for Nextflow repositories in {year}...")
        query = f"{base_query} created:{year}-01-01..{year}-12-31"
        result = g.search_repositories(query, sort="updated")
        count = call_rate_aware(lambda: result.totalCount, api_type="search")
        if count < 1000:
            print(f"Found {count} repositories in {year}")
            _process_github_search_result(result, count, out_dir, str(year))
            print("")
            continue

        print(
            f"Search result includes {count}>=1000 repositories in {year}, which "
            f"indicates that we hit search limit. Search month by month instead..."
        )
        for month in range(1, 12 + 1):
            month_days = calendar.monthrange(year, month)[1]
            query = f"{base_query} created:{year}-{month:02d}-01..{year}-{month:02d}-{month_days}"
            result = g.search_repositories(query, sort="updated")
            count = call_rate_aware(lambda: result.totalCount, api_type="search")
            if count < 1000:
                print(f"Found {count} repositories in month {year}-{month}")
                _process_github_search_result(result, count, out_dir, f"{year}-{month}")
                print("")
                continue

            print(
                f"Search result includes {count}>=1000 repositories in {year}-{month}, which "
                f"indicates that we hit search limit. Search day by day instead..."
            )
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                query = f"{base_query} created:{year}-{month:02d}-{day:02d}"
                result = g.search_repositories(query, sort="updated")
                count = call_rate_aware(lambda: result.totalCount, api_type="search")
                print(f"Found {count} repositories in day {year}-{month}-{day}")
                _process_github_search_result(
                    result, count, out_dir, f"{year}-{month}-{day}"
                )
                print("")


if __name__ == "__main__":
    fire.Fire(Scraper)
