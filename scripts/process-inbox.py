#!/usr/bin/env python3
"""
process-inbox.py — Batch-process ePubs from inbox/ into the Literature Clock.

Pipeline:
  1. Scan inbox/ for .epub files
  2. Extract time quotes (extract-quotes.py logic)
  3. HIGH confidence → merge directly into data/quotes.json
  4. MEDIUM/LOW → write to data/review-queue.json (for manual review)
  5. Move processed .epub → processed/
  6. Dedup against existing quotes (same time + first 80 chars)

Usage:
    python3 process-inbox.py                    # process all in inbox/
    python3 process-inbox.py --limit 5          # max 5 books
    python3 process-inbox.py --dry-run          # scan only, don't modify

Designed to run autonomously (heartbeat/cron) or manually.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add parent scripts dir to path for import
sys.path.insert(0, str(Path(__file__).parent))
from importlib import import_module

# We need the functions from extract-quotes.py
# Since it has hyphens in the name, use importlib
import importlib.util
spec = importlib.util.spec_from_file_location(
    "extract_quotes",
    Path(__file__).parent / "extract-quotes.py"
)
extract_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_mod)

BASE = Path(__file__).resolve().parent.parent
INBOX = BASE / "inbox"
PROCESSED = BASE / "processed"
QUOTES_FILE = BASE / "data" / "quotes.json"
REVIEW_FILE = BASE / "data" / "review-queue.json"
LOG_FILE = BASE / "data" / "processing-log.json"


def load_json(path: Path) -> list:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return []


def save_json(path: Path, data: list):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def quote_fingerprint(time: str, quote: str) -> str:
    """Generate dedup key from time + first 80 chars of quote."""
    return hashlib.sha256(f"{time}:{quote[:80]}".encode()).hexdigest()[:16]


def build_existing_fingerprints(quotes: list) -> set:
    """Build set of fingerprints from existing quotes."""
    fps = set()
    for q in quotes:
        fps.add(quote_fingerprint(q['time'], q['quote']))
    return fps


def process_book(epub_path: Path, existing_fps: set, dry_run: bool = False) -> dict:
    """Process a single ePub. Returns stats dict."""
    stats = {
        'file': epub_path.name,
        'title': '',
        'author': '',
        'total_found': 0,
        'high_added': 0,
        'review_queued': 0,
        'duplicates': 0,
        'timestamp': datetime.now().isoformat(),
    }

    try:
        text, title, author = extract_mod.extract_text_from_epub(str(epub_path))
        stats['title'] = title
        stats['author'] = author

        raw_quotes = extract_mod.find_time_quotes(text, title, author)
        stats['total_found'] = len(raw_quotes)

        high_quotes = []
        review_quotes = []

        for q in raw_quotes:
            minutes = extract_mod.apply_qualifier_jitter(q.minutes, q.quote)
            time_str = f"{minutes // 60:02d}:{minutes % 60:02d}"

            entry = {
                'time': time_str,
                'quote': q.quote,
                'title': q.title,
                'author': q.author,
            }

            fp = quote_fingerprint(time_str, q.quote)
            if fp in existing_fps:
                stats['duplicates'] += 1
                continue

            if q.confidence == 'high':
                high_quotes.append(entry)
                existing_fps.add(fp)  # prevent intra-batch dupes
                stats['high_added'] += 1
            else:
                review_entry = {**entry, 'confidence': q.confidence, 'time_match': q.time_match}
                review_quotes.append(review_entry)
                stats['review_queued'] += 1

        if not dry_run:
            # Merge high-confidence into quotes.json
            if high_quotes:
                quotes = load_json(QUOTES_FILE)
                quotes.extend(high_quotes)
                quotes.sort(key=lambda q: q['time'])
                save_json(QUOTES_FILE, quotes)

            # Append medium/low to review queue
            if review_quotes:
                review = load_json(REVIEW_FILE)
                review.extend(review_quotes)
                save_json(REVIEW_FILE, review)

            # Move epub to processed/
            dest = PROCESSED / epub_path.name
            if dest.exists():
                dest = PROCESSED / f"{epub_path.stem}_{datetime.now().strftime('%H%M%S')}{epub_path.suffix}"
            shutil.move(str(epub_path), str(dest))

    except Exception as e:
        stats['error'] = str(e)
        print(f"  ERROR processing {epub_path.name}: {e}", file=sys.stderr)

    return stats


def main():
    parser = argparse.ArgumentParser(description='Process ePub inbox for Literature Clock')
    parser.add_argument('--limit', type=int, default=5, help='Max books to process (default: 5)')
    parser.add_argument('--dry-run', action='store_true', help='Scan only, don\'t modify files')
    parser.add_argument('--all', action='store_true', help='Process all (ignore limit)')
    args = parser.parse_args()

    INBOX.mkdir(exist_ok=True)
    PROCESSED.mkdir(exist_ok=True)

    epubs = sorted(INBOX.glob('*.epub'))
    if not epubs:
        print("Inbox empty — nothing to process.", file=sys.stderr)
        return

    limit = len(epubs) if args.all else args.limit
    batch = epubs[:limit]

    print(f"Inbox: {len(epubs)} ePubs, processing {len(batch)}", file=sys.stderr)
    if args.dry_run:
        print("DRY RUN — no files will be modified", file=sys.stderr)

    # Load existing fingerprints for dedup
    existing = load_json(QUOTES_FILE)
    fps = build_existing_fingerprints(existing)
    print(f"Existing quotes: {len(existing)}, fingerprints: {len(fps)}", file=sys.stderr)

    all_stats = []
    total_added = 0
    total_review = 0

    for epub_path in batch:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Processing: {epub_path.name}", file=sys.stderr)
        stats = process_book(epub_path, fps, dry_run=args.dry_run)
        all_stats.append(stats)
        total_added += stats['high_added']
        total_review += stats['review_queued']
        print(f"  {stats['title']} by {stats['author']}", file=sys.stderr)
        print(f"  Found: {stats['total_found']} | Added: {stats['high_added']} | Review: {stats['review_queued']} | Dupes: {stats['duplicates']}", file=sys.stderr)
        if 'error' in stats:
            print(f"  ERROR: {stats['error']}", file=sys.stderr)

    # Update processing log
    if not args.dry_run and all_stats:
        log = load_json(LOG_FILE)
        log.append({
            'batch_date': datetime.now().isoformat(),
            'books_processed': len(all_stats),
            'quotes_added': total_added,
            'quotes_review': total_review,
            'details': all_stats,
        })
        save_json(LOG_FILE, log)

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SUMMARY: {len(batch)} books | +{total_added} quotes (auto) | {total_review} for review", file=sys.stderr)
    remaining = len(epubs) - len(batch)
    if remaining > 0:
        print(f"Remaining in inbox: {remaining}", file=sys.stderr)

    # Final count
    if not args.dry_run:
        final = load_json(QUOTES_FILE)
        print(f"Total quotes now: {len(final)}", file=sys.stderr)


if __name__ == '__main__':
    main()
