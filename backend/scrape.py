#!/usr/bin/env python

"""
Collect metadata for the awesome repositories, initialise and populate the database
"""

import calendar
import os
import pprint
import time
from pathlib import Path

import pandas as pd
from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException
import fire


README_PATH = "../README.md"
BLACKLIST = [
    "nextflow-io",
    "nf-core/modules",
    "nf-core/tools",
    "nf-core/configs",
]

os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"  # Do not clone LFS files
g = Github(os.environ["GITHUB_TOKEN"])


class Scraper:
    def scrape(self, out_path="scraped.csv", limit=None):
        """
        Search for repositories with "Nextflow" in the README, collect metadata on the
        found repositories, filter them, and write the metadata to a CSV.
        """
        searched_path = Path("searched.csv")
        if searched_path.exists():
            print(f"List of found repos exists, remove {out_path} to re-search")
            with searched_path.open() as f:
                found_repos = f.read().splitlines()
        else:
            found_repos = search_gh()
            with searched_path.open("w") as f:
                f.write("\n".join(found_repos))

        if limit is not None:
            found_repos = found_repos[:limit]
            
        out_path = Path(out_path)
        self.metadata_for_urls(found_repos, out_path, save_readme=False, filter=True)

    def readme(self, out_path="repos_from_readme.csv"):
        """
        Parse the README.md file, collect metadata on the found repositories, and
        write the metadata to a CSV.
        """
        out_path = Path(out_path)
        urls = []
        with Path(README_PATH).open() as f:
            for line in f:
                if line.startswith("Tutorials"):
                    break
                if line.startswith("* ["):
                    url = line.split("(")[1].split(")")[0]
                    urls.append(url)

        self.metadata_for_urls(urls, out_path, save_readme=True, filter=False)

    def metadata_for_urls(self, urls: list, out_path: Path, save_readme=False, filter=False):
        df = None
        if out_path.exists():
            df = pd.read_csv(str(out_path))
            print(f"Found metadata for {len(df)} repos, remove {out_path} to reprocess")

        new_dicts = []
        for i, url in enumerate(urls):
            if df is not None and url in df["url"].values:
                continue
            print(f"Processing #{i}: {url}")
            url = "/".join(Path(url).parts[-2:])
            try:
                d = collect_repo_metadata(url, save_readme=save_readme, filter=filter)
            except Exception as e:
                print(f"Error processing {url}: {e}")
            else:
                if filter and not d.get("nf_files_in_root") and not d.get("nf_files_in_subfolder"):
                    continue
                new_dicts.append(d)
        print(f"Processed {len(new_dicts)} more repos")
        if new_dicts:
            new_df = pd.DataFrame(new_dicts)
            if df is None:
                df = pd.DataFrame(new_dicts)
            else:
                df = pd.concat([df, new_df])
            df.to_csv(str(out_path), index=False)


def get_rate_limit(api_type):
    return getattr(g.get_rate_limit(), api_type)


def rate_limit_wait(api_type):
    curr_timestamp = calendar.timegm(time.gmtime())
    reset_timestamp = calendar.timegm(get_rate_limit(api_type).reset.timetuple())
    # add 5 seconds to be sure the rate limit has been reset
    sleep_time = max(0, reset_timestamp - curr_timestamp) + 5
    print(f"Rate limit exceeded, waiting {sleep_time} seconds")
    time.sleep(sleep_time)


def call_rate_limit_aware(func, api_type="core"):
    while True:
        try:
            return func()
        except RateLimitExceededException:
            rate_limit_wait(api_type)


def call_rate_limit_aware_decorator(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException:
                rate_limit_wait("core")

    return inner


@call_rate_limit_aware_decorator
def check_repo_exists(g, full_name):
    try:
        g.get_repo(full_name)
        return True
    except UnknownObjectException:
        print(f"Repo {full_name} has been deleted")
        return False


@call_rate_limit_aware_decorator
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


def collect_repo_metadata(url, save_readme=False, filter=False):
    """
    Collect repository selection criteria and metadata for the spreadsheet:
    https://docs.google.com/document/d/1kZWOBbIt9pY_wloCGcH2d9vYD4zgaTT7x-vTewu0eeA
    """
    d = {"url": url}
    if not check_repo_exists(g, url):
        print(f"Error: repo {url} does not exist")
        d["can_not_pull"] = True
        return d

    print(f"Checking out {url}")
    repo = g.get_repo(url)
    repo = call_rate_limit_aware(lambda: repo, api_type="search")
    
    nf_files_in_root = []
    nf_files_in_subfolders = []
    for f in repo.get_contents(""):
        if f.type == "file":
            if f.name.endswith(".nf"):
                nf_files_in_root.append(f.path)
                break
        elif f.type == "dir":  # One level deeper
            for f1 in repo.get_contents(f.path):
                if f1.type == "file":
                    if f1.name.endswith(".nf"):
                        nf_files_in_subfolders.append(f1.path)
                        break

    if filter and not nf_files_in_root and not nf_files_in_subfolders:
        print(f"Skipping {url} because it no *.nf file found in root or 2st level")
        return d
    
    d["nf_files_in_root"] = ", ".join(nf_files_in_root)
    d["nf_files_in_subfolders"] = ", ".join(nf_files_in_subfolders)

    d["url"] = repo.html_url  # Clickable URL
    d["title"] = repo.name
    d["owner"] = repo.owner.login
    d["name"] = f"{d['title']}--{d['owner']}"
    d["description"] = repo.description
    d["updated_at"] = repo.updated_at
    d["created_at"] = repo.created_at
    d["topics"] = ", ".join(repo.get_topics())
    d["website"] = repo.homepage
    d["stars"] = repo.stargazers_count
    d["watchers"] = repo.watchers_count
    d["forks"] = repo.forks_count
    d["last_commit_date"] = repo.get_commits().reversed[0].commit.committer.date
    releases = repo.get_releases()
    d["number_of_releases"] = releases.totalCount
    if d["number_of_releases"]:
        latest = releases.reversed[0]
        d["latest_release_date"] = latest.created_at
        d["latest_release_name"] = latest.title
    d["head_fork"] = repo.parent.full_name if repo.parent else None
    d["issues"] = repo.get_issues().totalCount
    d["open_issues"] = repo.get_issues(state="open").totalCount
    d["closed_issues"] = repo.get_issues(state="closed").totalCount
    d["prs"] = repo.get_pulls().totalCount
    d["open_prs"] = repo.get_pulls(state="open").totalCount
    d["closed_prs"] = repo.get_pulls(state="closed").totalCount
    d["contributors"] = repo.get_contributors().totalCount
    # d["clones"] = repo.get_clones_traffic()["count"]  # must have push access
    # d["unique_clones"] = repo.get_clones_traffic()["uniques"]  # must have push access
    # d["repo_views"] = repo.get_views_traffic()["count"]  # must have push access
    # d["unique_repo_views"] = repo.get_views_traffic()["uniques"]  # must have push access

    d["nextflow_main_lang"] = repo.language == "Nextflow"
    d["nextflow_code_chars"] = repo.get_languages().get("Nextflow", 0)
    d["languages"] = ", ".join(
        f"{n}: {c:.2f}%" for n, c in get_language_percentages(repo).items()
    )

    # topics = [t.lower() for t in repo.get_topics()]
    # d["nextflow_in_topics"] = "nextflow" in topics
    # d["genomics_in_topics"] = "genomics" in topics
    # d["bioinformatics_in_topics"] = "bioinformatics" in topics
    # d["workflow_in_topics"] = "workflow" in topics
    # d["pipeline_in_topics"] = "pipeline" in topics
    # d["nextflow_in_description"] = repo.description and "nextflow" in repo.description.lower()

    if save_readme:
        # Locate README (can be README.md, README.rst, README.txt, etc.)
        # and save it to repos/repo-name/README.md
        readme = None
        if check_file_exists(repo, "README.md"):
            readme = repo.get_contents("README.md")
        else:
            for f in repo.get_contents(""):
                if f.type == "file" and f.name.split(".")[0] == "README":
                    readme = f
        if readme:
            d["readme_name"] = readme.name
            try:
                readme_content = readme.decoded_content.decode()
            except Exception as r:
                print(f"Error parsing {readme.name}: {r}")
            else:
                d["readme_contains_nextflow"] = "nextflow" in readme_content.lower()
                print("readme_contains_nextflow:", d["readme_contains_nextflow"])
                # save readme to repos/repo-name/README.md
                readme_path = Path("repos") / d["name"] / readme.name
                readme_path.parent.mkdir(parents=True, exist_ok=True)
                with readme_path.open("w") as f:
                    f.write(readme_content)

    # pprint.pprint(d)
    # print()
    return d


def search_gh() -> list:
    """
    Search for GitHub repositories matching the criteria.
    * First, search for repositories with "Nextflow" in the README.
    * Second, filter to those having *.nf files in the root or on the first level.
    """
    repo_search = g.search_repositories(
        "nextflow in:readme archived:false", sort="updated"
    )
    total_count = call_rate_limit_aware(
        lambda: repo_search.totalCount, api_type="search"
    )
    found_repos = []
    print(f"Checking {total_count} repos.")
    for i in range(total_count):
        repo = call_rate_limit_aware(lambda: repo_search[i], api_type="search")
        if i % 10 == 0:
            print(f"{i} of {total_count} repos done.")
        print(f"Processing {repo.full_name}.")
        if repo.owner.login in BLACKLIST or repo.full_name in BLACKLIST:
            print(f"Repo {repo.owner.login} is blacklisted")
            continue
        else:
            found_repos.append(repo.url)
    return found_repos


if __name__ == "__main__":
    fire.Fire(Scraper)
