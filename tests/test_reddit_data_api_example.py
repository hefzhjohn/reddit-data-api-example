from __future__ import annotations

import base64
import json
import unittest
from urllib.request import Request

from reddit_data_api_example import (
    RedditAPIError,
    RedditCredentials,
    get_hot_posts,
)


class FakeResponse:
    def __init__(self, payload: dict, headers: dict | None = None) -> None:
        self.status = 200
        self.headers = headers or {}
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class RedditAPIExampleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.credentials = RedditCredentials("client-id", "client-secret", "macos:test:v1 (by /u/test)")

    def test_oauth_and_hot_listing_are_authenticated_and_bounded(self) -> None:
        requests: list[Request] = []

        def opener(request: Request, *, timeout: int) -> FakeResponse:
            requests.append(request)
            self.assertEqual(timeout, 15)
            if request.full_url.endswith("/api/v1/access_token"):
                return FakeResponse({"access_token": "synthetic-token"})
            return FakeResponse(
                {
                    "data": {
                        "children": [
                            {"data": {"id": "abc", "title": "Synthetic post", "author": "user", "permalink": "/r/stocks/comments/abc", "created_utc": 1, "score": 2, "num_comments": 3}}
                        ]
                    }
                },
                {"X-Ratelimit-Remaining": "99"},
            )

        posts, headers = get_hot_posts(
            "r/stocks", credentials=self.credentials, limit=500, opener=opener
        )
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].get_header("User-agent"), self.credentials.user_agent)
        expected_auth = base64.b64encode(b"client-id:client-secret").decode("ascii")
        self.assertEqual(requests[0].get_header("Authorization"), f"Basic {expected_auth}")
        self.assertEqual(requests[1].method, "GET")
        self.assertIn("limit=25", requests[1].full_url)
        self.assertEqual(requests[1].get_header("Authorization"), "Bearer synthetic-token")
        self.assertEqual(posts[0]["permalink"], "https://www.reddit.com/r/stocks/comments/abc")
        self.assertEqual(headers["X-Ratelimit-Remaining"], "99")

    def test_missing_credentials_fail_before_any_request(self) -> None:
        with self.assertRaisesRegex(RedditAPIError, "REDDIT_CLIENT_SECRET"):
            RedditCredentials.from_environment({"REDDIT_CLIENT_ID": "id", "REDDIT_USER_AGENT": "ua"})

    def test_rejects_malformed_subreddit_before_oauth(self) -> None:
        called = False

        def opener(_request: Request, *, timeout: int) -> FakeResponse:
            nonlocal called
            called = True
            return FakeResponse({})

        with self.assertRaisesRegex(RedditAPIError, "subreddit name"):
            get_hot_posts("stocks/../private", credentials=self.credentials, opener=opener)
        self.assertFalse(called)


if __name__ == "__main__":
    unittest.main()
