from __future__ import annotations

import os
from typing import Any

import httpx

from gha_tools.__about__ import __version__

# Optional cache; see `conftest.py`.
cache: dict[str, Any] | None = None


def get_github_json(url: str) -> Any:
    if not url.startswith("https://api.github.com/"):
        raise ValueError("URL must be a GitHub API URL")
    if cache is not None and url in cache:
        return cache[url]
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"gha-tools/{__version__} (@akx)",
    }

    auth = os.environ.get("GITHUB_AUTH") or os.environ.get("GITHUB_TOKEN")
    auth_tuple: tuple[str, str] | None = None
    if auth:
        if ":" in auth:
            username, password = auth.split(":", 1)
            auth_tuple = (username, password)
        else:
            headers["Authorization"] = f"Bearer {auth}"

    with httpx.Client() as client:
        response = client.get(url, headers=headers, auth=auth_tuple, follow_redirects=True)
        response.raise_for_status()
        data = response.json()

    if cache is not None:
        cache[url] = data
    return data
