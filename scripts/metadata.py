#!/usr/bin/env python

"""
Collect metadata for the awesome repositories, populate metadata.csv.
"""

import calendar
import os
import pprint
import time
from pathlib import Path

from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException

import pandas as pd


# Lines to check that *.nf files contain
CHECK_CONTENTS = [
    # "#!/bin/env nextflow",
    # "workflow {",
]


# Do not clone LFS files
os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"
g = Github(os.environ["GITHUB_TOKEN"])

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


# def metadata(url):
#     """
#     Collect metadata of pre-selected repos for the platform
#     """
#     if not check_repo_exists(g, url):
#         print(f"Error: repo {url} does not exist")
#         return None
# 
#     print(f"Checking out {url}")
#     d = dict()
#     repo = g.get_repo(url)
#     repo = call_rate_limit_aware(lambda: repo, api_type="search")
#     print(f"Processing {repo.full_name}")
# 
#     d["title"] = repo.name
#     d["description"] = repo.description
#     d["updated_at"] = repo.updated_at
#     d["created_at"] = repo.created_at
#     d["topics"] = ", ".join(repo.get_topics())
#     d["website"] = repo.homepage
#     d["stars"] = repo.stargazers_count
#     d["watchers"] = repo.watchers_count
#     d["forks"] = repo.forks_count
#     d["last_commit_date"] = repo.get_commits().reversed[0].commit.committer.date
#     releases = repo.get_releases()
#     d["number_of_releases"] = releases.totalCount
#     if d["number_of_releases"]:
#         latest = releases.reversed[0]
#         d["latest_release_date"] = latest.created_at
#         d["latest_release_name"] = latest.title
#     d["head_fork"] = repo.parent.full_name if repo.parent else None
#     d["issues"] = repo.get_issues().totalCount
#     d["open_issues"] = repo.get_issues(state="open").totalCount
#     d["closed_issues"] = repo.get_issues(state="closed").totalCount
#     d["prs"] = repo.get_pulls().totalCount
#     d["open_prs"] = repo.get_pulls(state="open").totalCount
#     d["closed_prs"] = repo.get_pulls(state="closed").totalCount
#     d["contributors"] = repo.get_contributors().totalCount
#     # d["clones"] = repo.get_clones_traffic()["count"]  # must have push access
#     # d["unique_clones"] = repo.get_clones_traffic()["uniques"]  # must have push access
#     # d["repo_views"] = repo.get_views_traffic()["count"]  # must have push access
#     # d["unique_repo_views"] = repo.get_views_traffic()["uniques"]  # must have push access
# 
#     pprint.pprint(d)
#     print()
#     return d


def metadata(url):
    """
    Collect repository selection criteria and metadata for the spreadsheet: 
    https://docs.google.com/document/d/1kZWOBbIt9pY_wloCGcH2d9vYD4zgaTT7x-vTewu0eeA
    """
    d = dict()
    if not check_repo_exists(g, url):
        print(f"Error: repo {url} does not exist")
        d["exists"] = False
        return d

    d["exists"] = True
    print(f"Checking out {url}")
    repo = g.get_repo(url)
    repo = call_rate_limit_aware(lambda: repo, api_type="search")

    d["title"] = repo.name
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

    print("Calculating selection criteria")
    d["nextflow main lang"] = repo.language == "Nextflow"
    d["nextflow code chars"] = repo.get_languages().get("Nextflow", 0)
    d["languages"] = ", ".join(f"{n}: {c:.2f}%" for n, c in get_language_percentages(repo).items())

    topics = [t.lower() for t in repo.get_topics()]
    d["nextflow in topics"] = "nextflow" in topics
    d["genomics in topics"] = "genomics" in topics
    d["bioinformatics in topics"] = "bioinformatics" in topics
    d["workflow in topics"] = "workflow" in topics
    d["pipeline in topics"] = "pipeline" in topics
    d["nextflow in description"] = repo.description and "nextflow" in repo.description.lower()

    # d["modules/nf-core exists"] = check_file_exists(repo, "modules/nf-core")
    # d["modules/subworkflows exists"] = check_file_exists(repo, "modules/subworkflows")
    
    def _check_file(f):
        d = {}
        if f.name == "main.nf":
            d["main.nf"] = True
        if f.name == "nextflow.config":
            d["nextflow.config"] = True
        if f.name.endswith(".nf"):
            d["*.nf"] = True
            if CHECK_CONTENTS:
                try:
                    content = f.decoded_content.decode()
                except Exception as r:
                    print(f"Error parsing file {f}: {r}")
                else:
                    for line in CHECK_CONTENTS:
                        if line in content:
                            d[f"contains {line}"] = True
        return d
    
    for f in repo.get_contents(""):
        if f.type == "file":
            d |= {f'{k} (in root)': v for k, v in _check_file(f).items()}

    for f in repo.get_contents(""):
        if f.type == "dir":
            for f1 in repo.get_contents(f.path):
                if f1.type == "file":
                    d |= {f'{k} (in subfolder)': v for k, v in _check_file(f).items()}
    
    pprint.pprint(d)
    print()
    return d


def main():
    dicts = []
    with Path("README.md").open() as f:
        for line in f:
            if line.startswith("Tutorials"):
                break
            if line.startswith("* ["):
                url = line.split("(")[1].split(")")[0]
                dicts.append({"url": url})

    metadata_path = Path("metadata.csv")
    if metadata_path.exists():
        df = pd.read_csv(str(metadata_path))
        print(f"{len(df)} repos already have metadata, remove {metadata_path} to reprocess")
    else:
        df = None

    new_dicts = []
    for i, d in enumerate(dicts):
        if df is not None and d['url'] in df['url'].values:
            continue
        print(f"Processing #{i}: {d['url']}")
        url = "/".join(Path(d['url']).parts[-2:])
        try:
            d.update(metadata(url))
        except Exception as e:
            print(f"Error processing {d[url]}: {e}")
            break
        new_dicts.append(d)
    print(f"Processed {len(new_dicts)} more repos")
    if new_dicts:
        new_df = pd.DataFrame(new_dicts)
        if df is None:
            df = pd.DataFrame(new_dicts)
        else:
            df = pd.concat([df, new_df])
        df.to_csv(str(metadata_path))


if __name__ == "__main__":
    main()
