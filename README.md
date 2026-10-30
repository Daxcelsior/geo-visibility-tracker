# GEO/AEO Visibility Tracker

Checks whether a brand is mentioned or cited when Claude answers questions with web search on.

## Step 1 (5 minutes): prove it runs, no API key needed
```
python track.py --brand "Acme" --domain acme.com --dry-run
```
Done when `results.csv` exists with 5 rows.

## Step 2: run it for real
```
pip install -r requirements.txt
set ANTHROPIC_API_KEY=your-key   (PowerShell: $env:ANTHROPIC_API_KEY="your-key")
python track.py --brand "YourBrand" --domain yourdomain.com
```
Edit `queries.csv` with 10 questions your customers would actually ask.

## Columns
- `mentioned`: brand or domain appears in the answer text
- `cited`: your domain appears in the sources the answer used
- Run it weekly; each run appends rows, so the CSV becomes your trend data.

## Next steps (one per sitting)
1. Add a small summary (mention rate and citation rate per run).
2. Add a competitor list and compare.
3. Chart it (Looker Studio or matplotlib) and write a one-page case study.
