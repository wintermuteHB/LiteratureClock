#!/usr/bin/env python3
"""Tests for the ePub quote extractor using Project Gutenberg public domain books."""

import csv
import os
import subprocess
import sys
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "extract-quotes.py"
FIXTURES = Path(__file__).parent / "fixtures"
GATSBY = FIXTURES / "gatsby.epub"
WUTHERING = FIXTURES / "wuthering-heights.epub"


def run_extract(*args):
    """Run the extractor and return parsed CSV rows."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)] + list(args),
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    lines = result.stdout.strip().split('\n')
    if not lines or not lines[0]:
        return []
    reader = csv.DictReader(lines)
    return list(reader)


def run_extract_json(*args):
    """Run the extractor with --json and return parsed data."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"] + list(args),
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


# ── Basic functionality ─────────────────────────────────────────────

def test_gatsby_finds_quotes():
    rows = run_extract(str(GATSBY))
    assert len(rows) >= 30, f"Expected 30+ quotes from Gatsby, got {len(rows)}"


def test_wuthering_finds_quotes():
    rows = run_extract(str(WUTHERING))
    assert len(rows) >= 25, f"Expected 25+ quotes from Wuthering Heights, got {len(rows)}"


def test_multiple_books():
    rows = run_extract(str(GATSBY), str(WUTHERING))
    gatsby_count = sum(1 for r in rows if "Gatsby" in r.get("Title", ""))
    wh_count = sum(1 for r in rows if "Wuthering" in r.get("Title", ""))
    assert gatsby_count > 0, "No Gatsby quotes found"
    assert wh_count > 0, "No Wuthering Heights quotes found"


def test_directory_scan():
    rows = run_extract(str(FIXTURES))
    assert len(rows) >= 55, f"Expected 55+ quotes from directory scan, got {len(rows)}"


# ── Metadata extraction ─────────────────────────────────────────────

def test_gatsby_metadata():
    rows = run_extract(str(GATSBY))
    titles = set(r["Title"] for r in rows)
    authors = set(r["Author"] for r in rows)
    assert any("Gatsby" in t for t in titles), f"Title not found: {titles}"
    assert any("Fitzgerald" in a for a in authors), f"Author not found: {authors}"


def test_wuthering_metadata():
    rows = run_extract(str(WUTHERING))
    titles = set(r["Title"] for r in rows)
    authors = set(r["Author"] for r in rows)
    assert any("Wuthering" in t for t in titles), f"Title not found: {titles}"
    assert any("Bront" in a for a in authors), f"Author not found: {authors}"


# ── Known quotes ────────────────────────────────────────────────────

def test_gatsby_known_times():
    """Gatsby contains well-known time references we must find."""
    rows = run_extract(str(GATSBY), "-c", "medium")
    times = set(r["TimeSinceMidnightInMinutes"] for r in rows)
    # "At nine o'clock, one morning late in July, Gatsby's gorgeous car..."
    assert "540" in times, "Missing 09:00 (Gatsby's car)"
    # "By seven o'clock the orchestra has arrived"
    assert "420" in times, "Missing 07:00 (orchestra)"
    # "At two o'clock Gatsby put on his bathing-suit"
    assert "120" in times or "840" in times, "Missing 02:00/14:00 (bathing-suit)"


def test_wuthering_known_times():
    """Wuthering Heights contains known time references."""
    rows = run_extract(str(WUTHERING), "-c", "medium")
    times = set(r["TimeSinceMidnightInMinutes"] for r in rows)
    # "half-past one" (Nelly looking at clock)
    assert "90" in times, "Missing 01:30 (half-past one)"
    # "half-past six; the family had just finished breakfast"
    assert "390" in times, "Missing 06:30 (breakfast)"


# ── Confidence filter ───────────────────────────────────────────────

def test_confidence_filter_reduces():
    all_rows = run_extract(str(GATSBY))
    medium_rows = run_extract(str(GATSBY), "-c", "medium")
    high_rows = run_extract(str(GATSBY), "-c", "high")
    assert len(all_rows) >= len(medium_rows) >= len(high_rows)
    assert len(all_rows) > len(high_rows), "Confidence filter should reduce results"


def test_high_confidence_has_digital():
    """High confidence should catch '6:00 a.m.' in Gatsby's schedule."""
    rows = run_extract(str(GATSBY), "-c", "high")
    assert len(rows) >= 1, "Expected at least 1 high-confidence quote"
    assert any("6:00" in r.get("TimeMatch", "") or "4:30" in r.get("TimeMatch", "")
               for r in rows), "Should find digital time with AM/PM"


# ── JSON output ─────────────────────────────────────────────────────

def test_json_output():
    data = run_extract_json(str(GATSBY))
    assert isinstance(data, list)
    assert len(data) >= 30
    first = data[0]
    assert "time" in first
    assert "quote" in first
    assert "title" in first
    assert "author" in first
    assert "confidence" in first


def test_json_time_format():
    data = run_extract_json(str(GATSBY))
    for item in data:
        assert len(item["time"]) == 5, f"Bad time format: {item['time']}"
        assert item["time"][2] == ":", f"Bad time format: {item['time']}"


# ── CSV output to file ──────────────────────────────────────────────

def test_output_file(tmp_path):
    outfile = tmp_path / "test-output.csv"
    subprocess.run(
        [sys.executable, str(SCRIPT), str(GATSBY), "-o", str(outfile)],
        capture_output=True, text=True, timeout=60
    )
    assert outfile.exists()
    with open(outfile) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) >= 30


# ── Edge cases ──────────────────────────────────────────────────────

def test_valid_minutes_range():
    """All times must be 0-1439 (00:00 to 23:59)."""
    rows = run_extract(str(GATSBY), str(WUTHERING))
    for r in rows:
        mins = int(r["TimeSinceMidnightInMinutes"])
        assert 0 <= mins <= 1439, f"Invalid time {mins} in: {r['Quote'][:50]}"


if __name__ == "__main__":
    # Simple runner without pytest
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = failed = 0
    for test in tests:
        name = test.__name__
        try:
            if "tmp_path" in test.__code__.co_varnames:
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    test(Path(td))
            else:
                test()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
    sys.exit(1 if failed else 0)
