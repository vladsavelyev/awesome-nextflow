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

import dotenv
import fire
import humanize
import pandas as pd
import requests
from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException
from sqlmodel import Session, select

from app.database import engine
from app.models import Repository, FilteredRepository

dotenv.load_dotenv()

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


class Scraper:
    """
    Usage: python scrape.py scrape --out_path scraped.csv --limit 100
    """

    search_dir = Path("github-search-starred")

    @staticmethod
    def search_github():
        """
        Search for GitHub repositories that mention "nextflow" in README.

        GitHub returns only top 1000 entries, so we work around by searching year
        by each year, or month by month or day by date if needed, and concatenate.
        """
        if Scraper.search_dir.exists():
            print(f"Directory {Scraper.search_dir} already exists, delete to re-search")
            return

        base_query = "nextflow in:readme archived:false stars:>1"
        for year in range(2015, datetime.datetime.today().year + 1):
            print(f"Searching for Nextflow repositories in {year}...")
            query = f"{base_query} created:{year}-01-01..{year}-12-31"
            result = g.search_repositories(query, sort="updated")
            count = call_rate_aware(lambda: result.totalCount, api_type="search")
            if count < 1000:
                print(f"Found {count} repositories in {year}")
                _process_github_search_result(
                    result, count, Scraper.search_dir, str(year)
                )
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
                    _process_github_search_result(
                        result, count, Scraper.search_dir, f"{year}-{month}"
                    )
                    print("")
                    continue

                print(
                    f"Search result includes {count}>=1000 repositories in {year}-{month}, which "
                    f"indicates that we hit search limit. Search day by day instead..."
                )
                for day in range(1, calendar.monthrange(year, month)[1] + 1):
                    query = f"{base_query} created:{year}-{month:02d}-{day:02d}"
                    result = g.search_repositories(query, sort="updated")
                    count = call_rate_aware(
                        lambda: result.totalCount, api_type="search"
                    )
                    print(f"Found {count} repositories in day {year}-{month}-{day}")
                    _process_github_search_result(
                        result, count, Scraper.search_dir, f"{year}-{month}-{day}"
                    )
                    print("")

    @staticmethod
    def collect_metadata():
        """
        Get metadata for each repo and filter to those having *.nf files in the root
        or on the first level. Add found data to the DB.
        """
        # Load initial list of found repositories.
        url_by_date = {}
        for csv_path in sorted(Scraper.search_dir.glob("*.tsv")):
            with csv_path.open() as f:
                df = pd.read_csv(f, sep="\t")
                date = csv_path.stem.split("-", 1)[1]
                url_by_date[date] = df["url"].tolist()
        print(
            f"Loaded list of {sum(len(d) for d in url_by_date.values())} repositories to process"
        )

        for date, urls in url_by_date.items():
            for i, url in enumerate(urls):
                t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cntr = f"{i + 1}/{len(urls)}"
                pref = f"{date} | {cntr:<10} | {t}:"
                with Session(engine) as session:
                    repo = session.exec(
                        select(Repository).where(Repository.url == url)
                    ).first()
                    if repo:
                        print(f"{pref} {url:<80} already in the database")
                        continue

                    repo = session.exec(
                        select(FilteredRepository).where(FilteredRepository.url == url)
                    ).first()
                    if repo:
                        print(f"{pref} {url:<80} already in the filtered table")
                        continue

                    print(f"{pref} {url:<80}", end=" ")
                    try:
                        repo: Repository | FilteredRepository = _collect_repo_metadata(
                            url
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

    @staticmethod
    def to_airtable():
        """
        Load the metadata from the SQLite database and insert it into the Airtable.
        """
        from app.airtable import db_to_airtable

        return db_to_airtable()


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


def _collect_repo_metadata(url) -> Repository | FilteredRepository:
    """
    Collect repository selection criteria and metadata for the spreadsheet:
    https://docs.google.com/document/d/1kZWOBbIt9pY_wloCGcH2d9vYD4zgaTT7x-vTewu0eeA
    """

    def gql_request(query, variables: dict | None = None):
        headers = {"Authorization": f"Bearer {github_token}"}
        request = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )
        if request.status_code == 200:
            return request.json()
        else:
            raise Exception(f"Query failed to run with a {request.status_code}.")

    if url.startswith("http"):
        owner, name = url.split("/")[-2:]
    else:
        owner, name = url.split("/")

    # The GraphQL API does not support directory listing with get_contents,
    # so using the REST API to check for .nf files in the root or 2nd level.
    try:
        repo = call_rate_aware(lambda: g.get_repo(f"{owner}/{name}"))
    except UnknownObjectException:
        print(f"❌error: repo {url} does not exist")
        return FilteredRepository(url=url, exists=False)

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

    if not nf_files_in_root and not nf_files_in_subfolders:
        print("❌skipping: no *.nf file found in root or 2nd level")
        return FilteredRepository(url=url, exists=True, no_nf_files=True)

    # GraphQL query to fetch repository metadata
    query = """
    query RepositoryInfo($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            url
            name
            owner {
                login
            }
            description
            createdAt
            updatedAt
            homepageUrl
            stargazerCount
            watcherCount: watchers {
                totalCount
            }
            forkCount
            issues(states: OPEN) {
                totalCount
            }
            pullRequests(states: OPEN) {
                totalCount
            }
            releases(first: 5) {
                totalCount
            }
            parent {
                nameWithOwner
            }
            languages(first: 10) {
                edges {
                    size
                    node {
                        name
                    }
                }
            }
            repositoryTopics(first: 10) {
                nodes {
                    topic {
                        name
                    }
                }
            }
        }
    }
    """
    gql_response = gql_request(query, {"owner": owner, "name": name})
    repo_info = gql_response["data"]["repository"]
    bytes_by_lang = {
        e["node"]["name"]: e["size"]
        for e in sorted(
            repo_info["languages"]["edges"], key=lambda x: x["size"], reverse=True
        )
    }
    total_bytes = sum(bytes_by_lang.values())
    languages_percentages = {
        lang: (bytes_ / total_bytes) * 100 for lang, bytes_ in bytes_by_lang.items()
    }
    nextflow_code_chars = bytes_by_lang.get("Nextflow", 0)
    nextflow_main_lang = bytes_by_lang and list(bytes_by_lang.keys())[0] == "Nextflow"
    repository = Repository(
        url=url,
        alive=True,
        nf_files_in_root="",
        nf_files_in_subfolders="",
        title=repo_info["name"],
        owner=repo_info["owner"]["login"],
        slugified_name=f"{repo_info['name']}--{repo_info['owner']['login']}",
        description=repo_info["description"],
        # parse dates into datetime objects
        updated_at=datetime.datetime.strptime(
            repo_info["updatedAt"], "%Y-%m-%dT%H:%M:%SZ"
        ),
        created_at=datetime.datetime.strptime(
            repo_info["createdAt"], "%Y-%m-%dT%H:%M:%SZ"
        ),
        topics=", ".join(
            t["repositoryTopics"]["name"]
            for t in repo_info["repositoryTopics"]["nodes"]
            if t["topic"]
        ),
        website=repo_info["homepageUrl"],
        stars=repo_info["stargazerCount"],
        watchers=repo_info["watcherCount"]["totalCount"],
        forks=repo_info["forkCount"],
        number_of_releases=repo_info["releases"]["totalCount"],
        head_fork=repo_info["parent"]["nameWithOwner"] if repo_info["parent"] else None,
        open_issues=repo_info["issues"]["totalCount"],
        open_prs=repo_info["pullRequests"]["totalCount"],
        nextflow_main_lang=nextflow_main_lang,
        nextflow_code_chars=nextflow_code_chars,
        languages=", ".join(f"{k}: {v}%" for k, v in languages_percentages.items()),
        readme_name=None,
        readme_contains_nextflow=None,
    )

    # Locate README (can be README.md, README.rst, README.txt, etc.)
    # and save it to repos/repo-name/README.md
    readme = None
    if check_file_exists(repo, "README.md"):
        readme = call_rate_aware(lambda: repo.get_contents("README.md"))
    else:
        for f in call_rate_aware(lambda: repo.get_contents("")):
            if f.type == "file" and f.name.split(".")[0].lower() == "readme":
                readme = f
    if readme:
        repository.readme_name = readme.name
        try:
            readme_content = readme.decoded_content.decode()
        except Exception as r:
            print(f"⚠️ error parsing {readme.name}: {r}", end=" ")
        else:
            repository.readme_contains_nextflow = "nextflow" in readme_content.lower()
            # Save readme to repos/repo-name/README.md
            readme_path = Path("readmes") / repository.slugified_name / readme.name
            readme_path.parent.mkdir(parents=True, exist_ok=True)
            with readme_path.open("w") as f:
                f.write(readme_content)

    print("👌")
    return repository


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


if __name__ == "__main__":
    fire.Fire(Scraper)
