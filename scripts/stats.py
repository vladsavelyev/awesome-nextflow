import calendar
import os
import pprint
import time
from pathlib import Path

from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException

import pandas as pd
import wandb


# do not clone LFS files
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


def check_repo(url):
    print(f"Checking out {url}")
    d = dict()
    
    url = "/".join(Path(url).parts[-2:])
    if not check_repo_exists(g, url):
        print("Error: repo does not exist")
        d["exists"] = False
        return d
    d["exists"] = True
    repo = g.get_repo(url)
    repo = call_rate_limit_aware(lambda: repo, api_type="search")
    print(f"Processing {repo.full_name}")

    d["updated_at"] = repo.updated_at
    
    d["nextflow_main_lang"] = repo.language == "Nextflow"
    d["nextflow_chars"] = repo.get_languages().get("Nextflow", 0)
    d["languages"] = ", ".join(f"{n}: {c:.2f}%" for n, c in get_language_percentages(repo).items())

    d["modules/nf-core exists"] = check_file_exists(repo, "modules/nf-core")
    d["modules/subworkflows exists"] = check_file_exists(repo, "modules/subworkflows")
    
    topics = [t.lower() for t in repo.get_topics()]
    d["nextflow in topics"] = "nextflow" in topics
    d["nf-core in topics"] = "nf-core" in topics
    d["genomics in topics"] = "genomics" in topics
    d["bioinformatics in topics"] = "bioinformatics" in topics
    d["workflow in topics"] = "workflow" in topics
    d["pipeline in topics"] = "pipeline" in topics
    if repo.description:
        description = repo.description.lower()
        d["nextflow in description"] = "nextflow" in description
        d["nf-core in description"] = "nf-core" in description
    else:
        d["nextflow in description"] = False
        d["nf-core in description"] = False
        
    def _check_file(f):
        d = {}
        if f.name == "main.nf":
            d["main.nf"] = True
        if f.name == "nextflow_schema.json":
            d["nextflow_schema.json"] = True
        if f.name == "nextflow.config":
            d["nextflow.config"] = True

        if f.name.endswith(".nf"):
            d["*.nf"] = True
            try:
                content = f.decoded_content.decode()
            except Exception as r:
                print(f"Error parsing file {f}: {r}")
            else:
                if content.startswith("#!/bin/env nextflow"):
                    d["#!/bin/env nextflow"] = True
                if "workflow {" in content:
                    d["workflow {"] = True
        return d
    
    d1 = {
        "main.nf": False,
        "nextflow_schema.json": False,
        "nextflow.config": False,
        "*.nf": False,
        "#!/bin/env nextflow": False,
        "workflow {": False,
    }
    for f in repo.get_contents(""):
        if f.type == "file":
            d1 |= _check_file(f)
    d |= {f'{k} (in root)': v for k, v in d1.items()}

    d1 = {
        "main.nf": False,
        "nextflow_schema.json": False,
        "nextflow.config": False,
        "*.nf": False,
        "#!/bin/env nextflow": False,
        "workflow {": False,
    }
    for f in repo.get_contents(""):
        if f.type == "dir":
            for f1 in repo.get_contents(f.path):
                if f1.type == "file":
                    d1 |= _check_file(f1)
    d |= {f'{k} (in subfolder)': v for k, v in d1.items()}
    
    pprint.pprint(d)
    print()
    return d


def plot(df):
    # Assuming you've gotten the SWEEP_ID from the previous step
    SWEEP_ID = "n8pjxih7"
    import wandb
    api = wandb.Api()

    sweep_id = wandb.sweep(
        sweep={
            'method': 'grid',
            'metric': {
                'name': 'dummy_metric',
                'goal': 'maximize'
            },
            'parameters': {
                'dummy_param': {
                    'values': [1],
                },
            }
        },
        project='repos2'
    )

    def wandb_log():
        wandb.init(project='repos2')
        for _, row in df.iterrows():
            wandb.log(row.to_dict())

    wandb.agent(sweep_id, function=wandb_log, count=1)


def main():
    if Path("stats.csv").exists():
        df = pd.read_csv("stats.csv")
        print(f"{len(df)} repos already processed, remove stats.csv to reprocess")
    else:
        df = None
    
    dicts = []
    with Path("README.md").open() as f:
        for line in f:
            if line.startswith("Tutorials"):
                break
            if line.startswith("* ["):
                name = line.split("[")[1].split("]")[0]
                url = line.split("(")[1].split(")")[0]
                dicts.append({"name": name, "url": url})

    new_dicts = []
    for i, d in enumerate(dicts):
        if df is not None and d['url'] in df['url'].values:
            continue
        print(f"Processing #{i}: {d['name']}")
        try:
            d.update(check_repo(d['url']))
        except Exception as e:
            print(f"Error processing {d['name']}: {e}")
            break
        new_dicts.append(d)
    print(f"Processed {len(new_dicts)} more repos")
    new_df = pd.DataFrame(new_dicts)
    if df is None:
        df = pd.DataFrame(new_dicts)
    else:
        df = pd.concat([df, new_df])
    df.to_csv("stats.csv")
    
    plot(df)


if __name__ == "__main__":
    main()
