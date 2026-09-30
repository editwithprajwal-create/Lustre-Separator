#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-Updater Engine for Lustre Separator
Supports Git-based auto-updates, commit tracking, and seamless background updates.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = WORKSPACE_DIR / "config.json"
VERSION_FILE = WORKSPACE_DIR / "version.json"

DEFAULT_VERSION_DATA = {
    "version": "2.5.0",
    "app_name": "Lustre Separator",
    "release_date": "2026-09-29",
    "channel": "stable"
}

def get_local_version():
    """Get the current application version."""
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_VERSION_DATA

def is_git_installed():
    """Check if Git CLI is installed on this system."""
    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False

def is_git_repo():
    """Check if the current workspace is a git repository."""
    git_dir = WORKSPACE_DIR / ".git"
    return git_dir.exists() and git_dir.is_dir()

def get_git_info():
    """Retrieve current branch, commit hash, and remote origin URL."""
    if not is_git_repo():
        return {
            "is_git": False,
            "branch": "none",
            "commit": "none",
            "remote_url": "",
            "message": "Not a Git repository yet."
        }
    try:
        # Current branch
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )
        branch = branch_res.stdout.strip() or "main"

        # Current short commit
        commit_res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )
        commit = commit_res.stdout.strip() or "initial"

        # Remote URL
        remote_res = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )
        remote_url = remote_res.stdout.strip()

        return {
            "is_git": True,
            "branch": branch,
            "commit": commit,
            "remote_url": remote_url,
            "message": f"Connected to {branch} ({commit})"
        }
    except Exception as e:
        return {
            "is_git": True,
            "branch": "unknown",
            "commit": "unknown",
            "remote_url": "",
            "message": str(e)
        }

def check_for_updates():
    """
    Check if remote git updates are available.
    Returns dict with update status, commits behind, and details.
    """
    ver = get_local_version()
    if not is_git_installed():
        return {
            "ok": False,
            "update_available": False,
            "current_version": ver.get("version", "2.5.0"),
            "error": "Git is not installed or not in PATH."
        }

    if not is_git_repo():
        return {
            "ok": True,
            "is_git": False,
            "update_available": False,
            "current_version": ver.get("version", "2.5.0"),
            "message": "Local folder is not initialized with Git. Set a Remote URL to enable auto-updates."
        }

    git_info = get_git_info()
    remote_url = git_info.get("remote_url", "")
    if not remote_url:
        return {
            "ok": True,
            "is_git": True,
            "update_available": False,
            "current_version": ver.get("version", "2.5.0"),
            "message": "Git is initialized, but no Remote Origin URL is set."
        }

    try:
        # Fetch remote updates silently with timeout
        fetch_res = subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=15
        )
        if fetch_res.returncode != 0:
            return {
                "ok": False,
                "is_git": True,
                "update_available": False,
                "current_version": ver.get("version", "2.5.0"),
                "error": f"Failed to fetch from remote: {fetch_res.stderr.strip()}"
            }

        # Check commits behind (available to pull)
        branch = git_info.get("branch", "main")
        behind_res = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )

        behind_count = 0
        if behind_res.returncode == 0:
            try:
                behind_count = int(behind_res.stdout.strip())
            except ValueError:
                behind_count = 0

        # Check commits ahead (ready to push to remote)
        ahead_res = subprocess.run(
            ["git", "rev-list", "--count", f"origin/{branch}..HEAD"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )
        ahead_count = 0
        if ahead_res.returncode == 0:
            try:
                ahead_count = int(ahead_res.stdout.strip())
            except ValueError:
                ahead_count = 0

        # Check uncommitted modifications
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
        )
        has_uncommitted = bool(status_res.stdout.strip())

        # Retrieve commit logs of new updates if available
        commits_log = []
        if behind_count > 0:
            log_res = subprocess.run(
                ["git", "log", f"HEAD..origin/{branch}", "--oneline", "-n", "5"],
                cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=5
            )
            if log_res.returncode == 0 and log_res.stdout:
                commits_log = [line.strip() for line in log_res.stdout.strip().split("\n") if line.strip()]

        msg = "Application is up to date."
        if behind_count > 0:
            msg = f"{behind_count} new update(s) available to pull!"
        elif ahead_count > 0:
            msg = f"{ahead_count} local commit(s) ready to push to GitHub!"
        elif has_uncommitted:
            msg = "Local changes detected (ready to push)."

        return {
            "ok": True,
            "is_git": True,
            "update_available": behind_count > 0,
            "behind_count": behind_count,
            "ahead_count": ahead_count,
            "has_uncommitted": has_uncommitted,
            "current_version": ver.get("version", "2.5.0"),
            "current_commit": git_info.get("commit"),
            "branch": branch,
            "remote_url": remote_url,
            "commits": commits_log,
            "message": msg
        }
    except Exception as exc:
        return {
            "ok": False,
            "is_git": True,
            "update_available": False,
            "current_version": ver.get("version", "2.5.0"),
            "error": str(exc)
        }

def perform_update():
    """
    Executes git pull to update the application files automatically.
    Preserves user configuration, media files, and local settings.
    """
    if not is_git_repo():
        return {"ok": False, "error": "Cannot pull: Directory is not a Git repository."}

    git_info = get_git_info()
    branch = git_info.get("branch", "main")

    try:
        # Backup config in memory just in case
        config_backup = None
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config_backup = f.read()
            except Exception:
                pass

        # Perform git pull with unrelated histories allowed if needed
        pull_res = subprocess.run(
            ["git", "pull", "--allow-unrelated-histories", "origin", branch],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=30
        )

        if pull_res.returncode != 0:
            # If there's a merge conflict or unstaged changes, try git stash then pull
            subprocess.run(["git", "stash"], cwd=str(WORKSPACE_DIR), capture_output=True, timeout=10)
            retry_res = subprocess.run(
                ["git", "pull", "--allow-unrelated-histories", "origin", branch],
                cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=30
            )
            if retry_res.returncode != 0:
                return {
                    "ok": False,
                    "error": f"Git pull failed: {retry_res.stderr.strip() or pull_res.stderr.strip()}"
                }

        # Restore config.json if needed
        if config_backup and not CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    f.write(config_backup)
            except Exception:
                pass

        new_info = get_git_info()
        return {
            "ok": True,
            "message": f"Successfully updated to latest version! (Commit: {new_info.get('commit')})",
            "commit": new_info.get("commit"),
            "branch": branch
        }
    except Exception as exc:
        return {"ok": False, "error": f"Update failed: {str(exc)}"}

def perform_push(commit_msg=None):
    """
    Pushes local changes and commits to the remote GitHub repository.
    Automatically stages and commits uncommitted changes if present.
    """
    if not is_git_repo():
        return {"ok": False, "error": "Cannot push: Directory is not a Git repository."}

    git_info = get_git_info()
    branch = git_info.get("branch", "main")
    remote_url = git_info.get("remote_url")
    if not remote_url:
        return {"ok": False, "error": "No Git remote URL configured. Please set the remote URL first."}

    try:
        # Check uncommitted changes
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=10
        )
        if status_res.stdout.strip():
            subprocess.run(["git", "add", "-A"], cwd=str(WORKSPACE_DIR), capture_output=True, timeout=15)
            msg = commit_msg or f"Update from Lustre Separator ({time.strftime('%Y-%m-%d %H:%M')})"
            subprocess.run(["git", "commit", "-m", msg], cwd=str(WORKSPACE_DIR), capture_output=True, timeout=15)

        # Execute push
        push_res = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=120
        )

        if push_res.returncode != 0:
            err = push_res.stderr.strip() or push_res.stdout.strip()
            return {"ok": False, "error": f"Git push failed: {err}"}

        new_info = get_git_info()
        return {
            "ok": True,
            "message": f"Successfully pushed to GitHub! (Commit: {new_info.get('commit')})",
            "commit": new_info.get("commit"),
            "branch": branch
        }
    except Exception as exc:
        return {"ok": False, "error": f"Push failed: {str(exc)}"}

def initialize_git_remote(remote_url, branch="main"):
    """
    Initializes git repository in current directory and links to remote URL.
    """
    if not remote_url:
        return {"ok": False, "error": "Remote URL is required."}

    try:
        if not is_git_repo():
            subprocess.run(["git", "init"], cwd=str(WORKSPACE_DIR), capture_output=True, check=True)
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=str(WORKSPACE_DIR), capture_output=True, check=True)
        else:
            # Update remote url
            subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=str(WORKSPACE_DIR), capture_output=True)

        # Set default branch
        subprocess.run(["git", "branch", "-M", branch], cwd=str(WORKSPACE_DIR), capture_output=True)

        return {
            "ok": True,
            "message": f"Git remote successfully connected to {remote_url} (branch: {branch})",
            "remote_url": remote_url
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
