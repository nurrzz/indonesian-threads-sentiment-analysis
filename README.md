# Indonesian Threads Sentiment Analysis

Sentiment and topic analysis of public Indonesian-language Threads posts about work, salaries,
education and AI, collected through Meta's official Threads API.

**Status:** setting up API access. No data has been collected yet.

## Checking API access

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add THREADS_ACCESS_TOKEN
python src/check_threads_access.py --keyword gaji
```

The script confirms the token is valid and reports whether keyword search returns posts from
other accounts or only from the authenticated account (Standard Access).
