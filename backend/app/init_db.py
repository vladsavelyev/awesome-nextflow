#!/usr/bin/env python

"""
Collect metadata for the awesome repositories, initialise and populate the database
"""

import os
from pathlib import Path

import fire
import pandas as pd
from github import Github

from .database import engine
from .models import Repository

os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"  # Do not clone LFS files
g = Github(os.environ["GITHUB_TOKEN"])


def main(csv_path: str):
    Repository.__table__.create(bind=engine, checkfirst=True)
    
    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"{csv_path.absolute()} does not exist, run parse_into_csv first")
        return
    df = pd.read_csv(str(csv_path))
    for i, row in df.iterrows():
        if "readme_name" in row and isinstance(row["name"], str) and isinstance(row["readme_name"], str):
            readme_path = Path("repos") / row["name"] / row["readme_name"]
            with readme_path.open() as f:
                df.loc[i, "readme_contents"] = f.read()
    df.to_sql("repositories", engine, if_exists="append", index=False)


if __name__ == "__main__":
    fire.Fire(main)
