import base64
import json
import os
import urllib.request
from typing import Any
from urllib.error import HTTPError

from gha_tools.__about__ import __version__


def get_github_json(url: str) -> Any:
    if not url.startswith("https://api.github.com/"):
        raise ValueError("URL must be a GitHub API URL")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"gha-tools/{__version__} (@akx)",
        },
    )
    if auth := (os.environ.get("GITHUB_AUTH") or os.environ.get("GITHUB_TOKEN")):
        if ":" in auth:
            auth = base64.b64encode(auth.encode("utf-8")).decode("utf-8")
            request.add_header("Authorization", f"Basic {auth}")
        else:
            request.add_header("Authorization", f"Bearer {auth}")
    with urllib.request.urlopen(request) as f:
        content = f.read().decode("utf-8", "replace")
        if f.status != 200:
            raise HTTPError(url, f.status, f.reason, f.headers, None)
        return json.loads(content)
