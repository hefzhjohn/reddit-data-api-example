# Reddit Data API: read-only connector example

This small example demonstrates an external Python app requesting an OAuth
token and reading one public subreddit hot listing. It is a connector example
for review, not the full Investment Desk application. The Investment Desk is a
separate private, local app; this repository contains none of its broker,
portfolio, tax, journal, or trading features.

This example is not yet wired into the private app and does not make requests
unless you run it directly.

## Scope

- One explicit, user-started request reads one subreddit hot listing (up to 25
  posts).
- The example uses the OAuth `client_credentials` grant and an explicit,
  descriptive User-Agent.
- It prints a short JSON view to standard output. It does not persist content,
  post, vote, comment, message users, or send Reddit content to an AI service.
- It has no connection to brokerage accounts or portfolio data.

This example is not affiliated with or endorsed by Reddit. It does not itself
grant API access. Reddit requires explicit approval before API access; obtain
approval and follow the terms and limits that Reddit gives your app before
running it against Reddit. Reddit's current Responsible Builder Policy also
requires apps to register and create a developer profile. This external Python
example is not a Devvit app; check with Reddit that the external API access flow
shown here is authorized for your application. Reddit's current policies and
API documentation take precedence over this technical example.

## Requirements

- Python 3.11 or newer
- A Reddit Data API app with credentials and explicit access approval

Create a local virtual environment (optional) and set the credentials in your
shell. Never commit real credentials or paste them into an issue or pull
request.

```bash
python3 -m venv .venv
source .venv/bin/activate
export REDDIT_CLIENT_ID='your-approved-client-id'
export REDDIT_CLIENT_SECRET='your-approved-client-secret'
export REDDIT_USER_AGENT='macos:reddit-data-api-example:v0.1.0 (by /u/your_reddit_username)'
```

Use the app credentials and authentication flow Reddit actually approved for
your app. The sample intentionally fails when any environment variable is
missing.

## Run

```bash
python reddit_data_api_example.py stocks --limit 10
```

The program makes two HTTPS requests: one to obtain an OAuth token and one to
read `/r/stocks/hot.json`. Choose only communities allowed by your approval.
The script prints titles, authors, timestamps, scores, comment counts, and
permalinks to the terminal; avoid saving its output. It makes no requests until
you run the command.

The example sets connection timeouts, caps the listing size, uses the OAuth
endpoint, and reports Reddit rate-limit headers when present. It does not retry
429 or other failures automatically, so review the response and Reddit's
current guidance before retrying.

## Tests

The unit tests use synthetic HTTP responses and never contact Reddit:

```bash
python3 -m unittest discover -s tests -v
```

## Data handling

Reddit policy requires compliance with deletion and retention rules for content
that is later deleted. This example avoids persistence; any production
integration must implement the currently required data-removal and retention
behavior before use. It is not a research-data collection tool.

## Official references

- [Reddit Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
- [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Reddit app registration](https://developers.reddit.com/app-registration)
- [Data API Terms](https://redditinc.com/policies/data-api-terms)

No license is granted by this example repository. All rights reserved.
