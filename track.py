"""GEO/AEO visibility tracker.

For each query, asks Claude (with web search on) and records whether your brand
or domain shows up in the answer text or in the cited sources. Appends one row
per query to results.csv so you can trend it over time.

Usage:
    python track.py --brand "Acme" --domain acme.com --queries queries.csv
    python track.py --brand "Acme" --domain acme.com --queries queries.csv --dry-run
"""
import argparse
import csv
import random
from datetime import datetime, timezone
from pathlib import Path

MODEL = "claude-opus-5-5"
FIELDS = ["run_at", "query", "brand", "mentioned", "cited", "cited_urls", "answer_excerpt"]


def read_queries(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [row["query"].strip() for row in csv.DictReader(f) if row.get("query", "").strip()]


def ask_claude(client, query):
    """Return (answer_text, [cited_urls]) for one query."""
    messages = [{"role": "user", "content": query}]
    text_parts, urls = [], []
    for _ in range(4):  # web search can pause a long turn; resume a few times
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
            messages=messages,
        )
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
                for cite in getattr(block, "citations", None) or []:
                    if getattr(cite, "url", None):
                        urls.append(cite.url)
            elif block.type == "web_search_tool_result" and isinstance(block.content, list):
                urls.extend(r.url for r in block.content if getattr(r, "url", None))
        if response.stop_reason != "pause_turn":
            break
        messages = [messages[0], {"role": "assistant", "content": response.content}]
    return "".join(text_parts), list(dict.fromkeys(urls))


def fake_answer(query, brand, domain):
    """Offline stand-in so you can test the pipeline without an API key."""
    if random.random() < 0.5:
        return f"Top options include {brand} and others.", [f"https://{domain}/page", "https://example.org/x"]
    return "Top options include several other vendors.", ["https://example.org/y"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--brand", required=True)
    p.add_argument("--domain", required=True, help="e.g. acme.com")
    p.add_argument("--queries", default="queries.csv")
    p.add_argument("--out", default="results.csv")
    p.add_argument("--dry-run", action="store_true", help="skip the API, use fake answers")
    args = p.parse_args()

    client = None
    if not args.dry_run:
        import anthropic  # needs ANTHROPIC_API_KEY, or `ant auth login`

        client = anthropic.Anthropic()

    out = Path(args.out)
    new_file = not out.exists()
    run_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    brand_l, domain_l = args.brand.lower(), args.domain.lower()

    with open(out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for q in read_queries(args.queries):
            if args.dry_run:
                answer, urls = fake_answer(q, args.brand, args.domain)
            else:
                answer, urls = ask_claude(client, q)
            mentioned = brand_l in answer.lower() or domain_l in answer.lower()
            cited = any(domain_l in u.lower() for u in urls)
            w.writerow({
                "run_at": run_at, "query": q, "brand": args.brand,
                "mentioned": mentioned, "cited": cited,
                "cited_urls": " | ".join(urls[:10]),
                "answer_excerpt": answer[:300].replace("\n", " "),
            })
            print(f"[{'MENTION' if mentioned else '  -    '}] [{'CITED' if cited else '  -  '}] {q}")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
