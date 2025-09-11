"""Easily handle package git repo maintainance"""

import os
import subprocess
from pathlib import Path
from .runner import RunBase


def _run_git(args, result_queue, complete=True, work_dir="/"):
    return RunBase(["git", *args], result_queue, complete=complete, work_dir=work_dir).run()


class RepoManager:
    """Object to pull and keep a repo updated"""
    def __init__(self, repo_path: str, repo_url: str, branch: str):
        self.repo_path = Path(repo_path)
        self.repo_url = repo_url
        self.branch = branch

    def _run(self, args, result_queue, work_dir=None, complete=False):
        work_dir = work_dir or self.repo_path
        return _run_git(args, result_queue, complete=complete, work_dir=str(work_dir))

    def ensure_repo(self, result_queue):
        if not self.repo_path.exists():
            result_queue.put_nowait(f"Cloning {self.repo_url} into {self.repo_path}")
            parent_dir = self.repo_path.parent
            _run_git(
                ["clone", "-b", self.branch, self.repo_url, str(self.repo_path)],
                result_queue,
                work_dir=str(parent_dir),
            )
        else:
            result_queue.put_nowait(f"Using existing repo at {self.repo_path}")
            self._run(["fetch", "--all"], result_queue)
            self._run(["checkout", self.branch], result_queue)
            self._run(["reset", "--hard", "HEAD"], result_queue)
            self._run(["pull", "origin", self.branch], result_queue)

    def remove_repo(self, result_queue):
        if self.repo_path.exists():
            result_queue.put_nowait(f"Removing repo at {self.repo_path}")
            RunBase(
                ["rm", "-rf", str(self.repo_path)],
                result_queue,
                complete=True,
                work_dir=str(self.repo_path.parent),
            ).run()
        else:
            result_queue.put_nowait(f"No repo found at {self.repo_path}, nothing to remove.")
