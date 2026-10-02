"""Minimal, read-only Reddit Data API example using the Python standard library."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE_URL = "https://oauth.reddit.com"
MAX_LIMIT = 25
TIMEOUT_SECONDS = 15
_SUBREDDIT_RE = re.compile(r"^[A-Za-z0-9_]{2,21}$")

OpenRequest = Callable[..., object]


class RedditAPIError(RuntimeError):
    """Safe-to-display API error without request credentials or response body."""


@dataclass(frozen=True)
class RedditCredentials:
    client_id: str
    client_secret: str
    user_agent: str

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> "RedditCredentials":
        source = os.environ if env is None else env
        values = {
            "REDDIT_CLIENT_ID": str(source.get("REDDIT_CLIENT_ID") or "").strip(),
            "REDDIT_CLIENT_SECRET": str(source.get("REDDIT_CLIENT_SECRET") or "").strip(),
            "REDDIT_USER_AGENT": str(source.get("REDDIT_USER_AGENT") or "").strip(),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RedditAPIError("Missing required environment variable(s): " + ", ".join(missing))
        return cls(
            client_id=values["REDDIT_CLIENT_ID"],
            client_secret=values["REDDIT_CLIENT_SECRET"],
            user_agent=values["REDDIT_USER_AGENT"],
        )


def _read_json(request: Request, *, opener: OpenRequest = urlopen) -> tuple[dict, Mapping[str, str]]:
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:  # type: ignore[attr-defined]
            status = int(getattr(response, "status", 200))
            if status < 200 or status >= 300:
                raise RedditAPIError(f"Reddit API returned HTTP {status}.")
            payload = json.loads(response.read().decode("utf-8"))
            headers = getattr(response, "headers", {}) or {}
    except HTTPError as exc:
        raise RedditAPIError(f"Reddit API returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RedditAPIError(f"Reddit API request failed ({type(exc).__name__}).") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RedditAPIError("Reddit API returned malformed JSON.") from None
    if not isinstance(payload, dict):
        raise RedditAPIError("Reddit API returned an unexpected response shape.")
    return payload, headers


def get_access_token(
    credentials: RedditCredentials,
    *,
    opener: OpenRequest = urlopen,
) -> str:
    basic_auth = base64.b64encode(
        f"{credentials.client_id}:{credentials.client_secret}".encode("utf-8")
    ).decode("ascii")
    request = Request(
        TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode("ascii"),
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": credentials.user_agent,
        },
        method="POST",
    )
    payload, _ = _read_json(request, opener=opener)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token.strip():
        raise RedditAPIError("Reddit OAuth response did not include an access token.")
    return token.strip()


def get_hot_posts(
    subreddit: str,
    *,
    credentials: RedditCredentials,
    limit: int = 10,
    opener: OpenRequest = urlopen,
) -> tuple[list[dict[str, object]], Mapping[str, str]]:
    name = subreddit.removeprefix("r/").strip()
    if not _SUBREDDIT_RE.fullmatch(name):
        raise RedditAPIError("Provide a subreddit name without spaces or URL characters.")
    bounded_limit = max(1, min(int(limit), MAX_LIMIT))
    token = get_access_token(credentials, opener=opener)
    url = f"{OAUTH_BASE_URL}/r/{quote(name, safe='')}/hot.json?{urlencode({'limit': bounded_limit})}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": credentials.user_agent,
            "Accept": "application/json",
        },
        method="GET",
    )
    payload, headers = _read_json(request, opener=opener)
    data = payload.get("data")
    children = data.get("children") if isinstance(data, dict) else None
    if not isinstance(children, list):
        raise RedditAPIError("Reddit API response did not contain a post listing.")

    posts: list[dict[str, object]] = []
    for child in children[:bounded_limit]:
        post = child.get("data") if isinstance(child, dict) else None
        if not isinstance(post, dict):
            continue
        posts.append(
            {
                "id": str(post.get("id") or ""),
                "title": str(post.get("title") or ""),
                "author": str(post.get("author") or "[deleted]"),
                "created_utc": post.get("created_utc"),
                "score": post.get("score"),
                "num_comments": post.get("num_comments"),
                "permalink": "https://www.reddit.com" + str(post.get("permalink") or ""),
            }
        )
    return posts, headers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subreddit", help="approved public subreddit, with or without r/")
    parser.add_argument("--limit", type=int, default=10, help=f"posts to show (maximum {MAX_LIMIT})")
    args = parser.parse_args(argv)

    try:
        credentials = RedditCredentials.from_environment()
        posts, headers = get_hot_posts(
            args.subreddit,
            credentials=credentials,
            limit=args.limit,
        )
    except RedditAPIError as exc:
        print(f"Reddit API error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"subreddit": args.subreddit.removeprefix("r/"), "posts": posts}, indent=2))
    rate_fields = {
        name: value
        for name, value in headers.items()
        if str(name).lower().startswith("x-ratelimit-")
    }
    if rate_fields:
        print("Rate-limit headers: " + json.dumps(rate_fields, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
