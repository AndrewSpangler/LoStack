import os
import subprocess
from pathlib import Path
from .runners.base import RunBase


def _run_git(args, result_queue, complete=True, work_dir="/"):
    return RunBase(["git", *args], result_queue, complete=complete, work_dir=work_dir).run()


class RepoManager:
    def __init__(self, repo_path: str, repo_url: str, branch: str, result_queue):
        self.repo_path = Path(repo_path)
        self.repo_url = repo_url
        self.branch = branch
        self.queue = result_queue

    def _run(self, args, work_dir=None, complete=False):
        work_dir = work_dir or self.repo_path
        return _run_git(args, self.queue, complete=complete, work_dir=str(work_dir))

    def ensure_repo(self):
        if not self.repo_path.exists():
            self.queue.put_nowait(f"Cloning {self.repo_url} into {self.repo_path}")
            parent_dir = self.repo_path.parent
            _run_git(
                ["clone", "-b", self.branch, self.repo_url, str(self.repo_path)],
                self.queue,
                work_dir=str(parent_dir),
            )
        else:
            self.queue.put_nowait(f"Using existing repo at {self.repo_path}")
            self._run(["fetch", "--all"])
            self._run(["checkout", self.branch])
            self._run(["reset", "--hard", "HEAD"])
            self._run(["pull", "origin", self.branch])

    def current_branch(self):
        result = self._run(["rev-parse", "--abbrev-ref", "HEAD"], complete=True)
        last_line = None
        for msg in list(result.queue.queue):
            if msg.startswith("stdout:"):
                last_line = msg.replace("stdout:", "").strip()
        return last_line

    def remove_repo(self):
        if self.repo_path.exists():
            self.queue.put_nowait(f"Removing repo at {self.repo_path}")
            RunBase(
                ["rm", "-rf", str(self.repo_path)],
                self.queue,
                complete=True,
                work_dir=str(self.repo_path.parent),
            ).run()
        else:
            self.queue.put_nowait(f"No repo found at {self.repo_path}, nothing to remove.")
