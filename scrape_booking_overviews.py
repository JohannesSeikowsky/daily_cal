"""Scrape v-office booking PDFs into overviews/*.txt."""
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from urls_config import FEWOS
from utils import get_fewo_name, error_email, get_email_recipients

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")
REQUEST_TIMEOUT = 60
RETRIES = 3
RETRY_DELAY = 10
REQUEST_DELAY = 2

BOOKING_ROW = re.compile(
    r"^\s*(\d{4,})\s+(.+?)\s+(\d{2}\.\d{2}\.\d{2})\s+(\d{2}\.\d{2}\.\d{2})\s+"
    r"(\d+)\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s+(\d+)\s+([\d.,]+\s*\S+)\s+([\d.,]+\s*\S+)\s*$")
SUMMARY_ROW = re.compile(r"^\s*(\d+)\s+Belegung(?:en)?\b")
DATA_LINE = re.compile(r"^\s*\d{4,}\s+\S")


class ScrapeError(Exception):
    """A URL could not be fetched or its PDF could not be parsed reliably."""


def fetch_pdf(url):
    """Download a v-office print URL, retrying on transient failures."""
    for attempt in range(RETRIES):
        try:
            data = urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT).read()
        except Exception as exc:
            if attempt == RETRIES - 1:
                raise ScrapeError(f"download failed: {exc}")
            time.sleep(RETRY_DELAY)
            continue
        if not data.startswith(b"%PDF"):
            raise ScrapeError("response was not a PDF")
        return data


def pdf_to_text(pdf_bytes):
    """Extract column-aligned text from PDF bytes via pdftotext."""
    result = subprocess.run(["pdftotext", "-layout", "-", "-"],
                            input=pdf_bytes, capture_output=True)
    if result.returncode != 0:
        raise ScrapeError(f"pdftotext failed: {result.stderr.decode(errors='replace')}")
    return result.stdout.decode("utf-8")


def parse_bookings(text):
    """Parse booking rows, verifying the count against the PDF's own total."""
    rows, totals = [], []
    for line in text.splitlines():
        match = BOOKING_ROW.match(line)
        summary = SUMMARY_ROW.match(line)
        if match:
            res, guest, start, end, days, adults, kids, babies, pets, turnover, income = match.groups()
            rows.append([res, guest.strip(), start, end, days,
                         f"{adults} / {kids} / {babies}", pets, turnover, income])
        elif summary:
            totals.append(int(summary.group(1)))
        elif DATA_LINE.match(line):
            raise ScrapeError(f"unrecognised row: {line.strip()}")
    if len(totals) != 1:
        raise ScrapeError(f"expected one summary line, found {len(totals)}")
    if len(rows) != totals[0]:
        raise ScrapeError(f"parsed {len(rows)} rows but PDF reports {totals[0]}")
    return rows


def scrape_property(urls):
    """Merge rows from all of a property's URLs; raise if any one of them fails."""
    rows = []
    for url in urls:
        rows.extend(parse_bookings(pdf_to_text(fetch_pdf(url))))
        time.sleep(REQUEST_DELAY)
    return rows


def main():
    """Scrape all properties; write a file only when every URL succeeded."""
    if not shutil.which("pdftotext"):
        raise SystemExit("pdftotext not found - install poppler-utils")
    if not get_email_recipients("errors"):
        print("WARNING: EMAIL_RECIPIENT_ERRORS not set - failures will not be mailed")

    failures = []
    for fewo_name, urls in FEWOS.items():
        try:
            rows = scrape_property([url for url in urls if url.strip()])
        except ScrapeError as exc:
            failures.append(f"{fewo_name}: {exc}")
            print(f"{fewo_name}: FAILED ({exc}) - keeping existing file")
            continue
        output_file = PROJECT_PATH / "overviews" / f"{get_fewo_name(fewo_name)}.txt"
        output_file.write_text("\n".join("|".join(row) for row in rows), encoding="utf-8")
        print(f"{fewo_name}: wrote {len(rows)} rows")

    if failures:
        error_email("Scraper failures (existing files kept):\n\n" + "\n".join(failures))


if __name__ == "__main__":
    main()
