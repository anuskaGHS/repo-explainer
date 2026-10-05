"""Handles cloning GitHub repositories and processing repository file trees and contents."""

import gc
import json
import os
import re
import shutil
import stat
import time
from pathlib import Path
from typing import Iterable, List, Optional

import git
import git.exc

# Directory to store cloned repositories in project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLONED_REPOS_DIR = PROJECT_ROOT / "cloned_repos"

# Strict GitHub URL regex matching public repositories
GITHUB_URL_REGEX = re.compile(
    r"^https://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

# Common source and config extensions to keep
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".html",
    ".css",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ipynb",
}

# Source code extensions with higher size limits
SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".ipynb",
}

# Specific filenames to always include
EXACT_FILENAMES = {
    "dockerfile",
    "requirements.txt",
    "package.json",
}

# Directories to skip entirely
SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".idea",
    ".vscode",
}

# Known binary and image extensions to reject
IMAGE_BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
    ".tiff",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".iso",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".pyc",
    ".pyo",
    ".pyd",
    ".class",
    ".jar",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp3",
    ".mp4",
    ".wav",
    ".avi",
    ".mov",
}

# Maximum file sizes: 100 KB for general files, 1 MB for source code
MAX_FILE_SIZE_BYTES = 100 * 1024
MAX_SOURCE_FILE_BYTES = 1_000_000


def _handle_remove_readonly(func, path, exc):
    """Clear Windows readonly attribute and reattempt removal."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        time.sleep(0.05)
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass


def _delete_directory(dir_path: Path) -> None:
    """Safely delete directory handling Windows git read-only files and open handles."""
    if not dir_path.exists():
        return
    gc.collect()
    try:
        shutil.rmtree(dir_path, onexc=_handle_remove_readonly)
    except TypeError:
        # Fallback for Python < 3.12
        def _onerror(func, p, exc_info):
            _handle_remove_readonly(func, p, exc_info[1])
        shutil.rmtree(dir_path, onerror=_onerror)


def _is_lock_file(filename: str) -> bool:
    """Check if the given filename is a dependency lock file."""
    low = filename.lower()
    if low.endswith(".lock"):
        return True
    if low.endswith("-lock.json") or low.endswith("-lock.yaml") or low.endswith("-lock.yml"):
        return True
    if low in {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "cargo.lock",
        "gemfile.lock",
        "composer.lock",
        "pipfile.lock",
    }:
        return True
    return False


def _is_binary_file(file_path: Path) -> bool:
    """Check if file has known binary extensions or contains null bytes."""
    if file_path.suffix.lower() in IMAGE_BINARY_EXTENSIONS:
        return True
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        return True


def clone_repo(repo_url: str) -> Path:
    """Clone a public GitHub repository using shallow clone (depth=1).

    Args:
        repo_url: Public GitHub repository URL (e.g. https://github.com/user/repo).

    Returns:
        Path to the cloned repository folder.

    Raises:
        ValueError: If the repository URL is not a valid public GitHub URL.
        RuntimeError: If cloning fails (repo not found, no internet, or git not installed).
    """
    clean_url = repo_url.strip()
    match = GITHUB_URL_REGEX.match(clean_url)
    if not match:
        raise ValueError(
            f"Invalid GitHub URL: '{repo_url}'. "
            "Only public GitHub URLs (e.g., https://github.com/owner/repository) are accepted."
        )

    _, repo_name = match.groups()
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    CLONED_REPOS_DIR.mkdir(parents=True, exist_ok=True)
    target_dir = CLONED_REPOS_DIR / repo_name

    # Delete existing repository directory if present
    if target_dir.exists():
        _delete_directory(target_dir)

    try:
        repo = git.Repo.clone_from(clean_url, str(target_dir), depth=1)
        # Explicitly close repo to release Windows file locks
        repo.close()
        del repo
        gc.collect()
        return target_dir
    except git.exc.GitCommandNotFound:
        raise RuntimeError("Git is not installed or not found in system PATH. Please install Git.") from None
    except git.exc.GitCommandError as exc:
        _delete_directory(target_dir)
        stderr_msg = exc.stderr.strip() if hasattr(exc, "stderr") and exc.stderr else str(exc)
        low_err = stderr_msg.lower()
        if "not found" in low_err or "repository not found" in low_err or "authentication failed" in low_err:
            raise RuntimeError(
                f"Repository not found or private: '{clean_url}'. Please check the URL and permissions."
            ) from None
        if any(net in low_err for net in ["could not resolve host", "network is unreachable", "failed to connect", "timed out"]):
            raise RuntimeError("Network error: Unable to reach GitHub. Please check your internet connection.") from None
        raise RuntimeError(f"Failed to clone repository: {stderr_msg}") from None
    except Exception as exc:
        _delete_directory(target_dir)
        raise RuntimeError(f"Unexpected error while cloning repository: {exc}") from None


def get_relevant_files(repo_path: Path) -> List[Path]:
    """Retrieve relevant source and configuration files from the repository.

    Filters files based on extensions, skips ignored folders, ignores lock files,
    binary files, images, and files larger than 100 KB.

    Args:
        repo_path: Path to the root directory of the repository.

    Returns:
        Sorted list of relevant file Paths.
    """
    repo_path = Path(repo_path).resolve()
    relevant: List[Path] = []

    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories in-place
        dirs[:] = [d for d in dirs if d.lower() not in {s.lower() for s in SKIP_DIRS}]

        for filename in files:
            file_path = Path(root) / filename
            name_lower = filename.lower()
            stem_lower = file_path.stem.lower()
            suffix_lower = file_path.suffix.lower()

            # Skip lock files
            if _is_lock_file(filename):
                continue

            # Check if matching allowed extensions or special filenames
            is_allowed = (
                stem_lower == "readme"
                or name_lower == "readme"
                or name_lower in EXACT_FILENAMES
                or name_lower.startswith("dockerfile")
                or suffix_lower in ALLOWED_EXTENSIONS
            )

            if not is_allowed:
                continue

            # Determine maximum size limit based on file type
            max_bytes = (
                MAX_SOURCE_FILE_BYTES
                if suffix_lower in SOURCE_EXTENSIONS
                else MAX_FILE_SIZE_BYTES
            )

            # Skip files larger than their respective limit
            try:
                if file_path.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue

            # Skip binary files and images
            if _is_binary_file(file_path):
                continue

            relevant.append(file_path)

    relevant.sort()
    return relevant


def _extract_ipynb_text(raw_json: str) -> str:
    """Parse Jupyter Notebook JSON and build plain text from cells only.

    - Code cells: include cell source as-is.
    - Markdown cells: include source as comment lines starting with '# [markdown] '.
    - Separate cells with '# --- cell N (code) ---' or '# --- cell N (markdown) ---'.
    - Ignores outputs, metadata, images, and execution counts.
    - Falls back to raw_json if parsing fails.
    """
    try:
        data = json.loads(raw_json)
        cells = data.get("cells", [])
        if not isinstance(cells, list):
            return raw_json
    except Exception:
        return raw_json

    cell_blocks: List[str] = []
    for idx, cell in enumerate(cells, 1):
        if not isinstance(cell, dict):
            continue

        cell_type = cell.get("cell_type", "code")
        raw_source = cell.get("source", "")
        if isinstance(raw_source, list):
            source_text = "".join(raw_source)
        else:
            source_text = str(raw_source)

        header = f"# --- cell {idx} ({cell_type}) ---"

        if cell_type == "code":
            cell_blocks.append(f"{header}\n{source_text}".rstrip())
        elif cell_type == "markdown":
            commented = [
                f"# [markdown] {line}" if line.strip() else "# [markdown]"
                for line in source_text.splitlines()
            ]
            cell_blocks.append(f"{header}\n" + "\n".join(commented))

    if not cell_blocks:
        return raw_json

    return "\n\n".join(cell_blocks)


def read_files(paths: Iterable[Path], repo_path: Path) -> List[dict]:
    """Read contents of given files relative to the repository path.

    For .ipynb files, extracts text from code cells and commented markdown cells,
    ignoring outputs, metadata, and images.

    Args:
        paths: Iterable of file Paths to read.
        repo_path: Root Path of the repository.

    Returns:
        List of dicts formatted as {"path": relative_path_str, "content": file_content_str}.
    """
    repo_path = Path(repo_path).resolve()
    records: List[dict] = []

    for file_path in paths:
        path_obj = Path(file_path).resolve()
        try:
            rel_path = path_obj.relative_to(repo_path).as_posix()
        except ValueError:
            rel_path = path_obj.as_posix()

        try:
            with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Special parsing for Jupyter Notebooks
            if path_obj.suffix.lower() == ".ipynb":
                content = _extract_ipynb_text(content)

            records.append({"path": rel_path, "content": content})
        except OSError:
            continue

    return records


def build_file_tree(repo_path: Path, files: Optional[List[Path]] = None) -> str:
    """Generate a clean text tree of relevant files in the repository.

    Args:
        repo_path: Root Path of the repository.
        files: Optional pre-filtered list of relevant file Paths.

    Returns:
        Formatted ASCII/Unicode text tree string.
    """
    repo_path = Path(repo_path).resolve()
    if files is None:
        files = get_relevant_files(repo_path)

    if not files:
        return f"{repo_path.name}/\n    (no relevant files found)"

    tree: dict = {}
    for file_path in files:
        try:
            rel_path = Path(file_path).resolve().relative_to(repo_path).as_posix()
        except ValueError:
            rel_path = Path(file_path).name

        parts = rel_path.split("/")
        curr = tree
        for part in parts:
            curr = curr.setdefault(part, {})

    def _render(node: dict, prefix: str = "") -> List[str]:
        lines: List[str] = []
        # Sort folders before files, alphabetical case-insensitive
        keys = sorted(node.keys(), key=lambda s: (len(node[s]) == 0, s.lower()))
        for idx, key in enumerate(keys):
            is_last = (idx == len(keys) - 1)
            connector = "└── " if is_last else "├── "
            if node[key]:
                lines.append(f"{prefix}{connector}{key}/")
                sub_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(_render(node[key], sub_prefix))
            else:
                lines.append(f"{prefix}{connector}{key}")
        return lines

    return "\n".join([f"{repo_path.name}/"] + _render(tree))
