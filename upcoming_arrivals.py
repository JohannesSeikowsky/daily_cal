"""Generate a simple HTML page listing arrivals in the next 3 weeks."""

from pathlib import Path
from datetime import date, timedelta, datetime

ROOT = Path(__file__).parent
SRC = ROOT / "overviews"
OUT = ROOT / "arrivals.html"

WEEKDAYS = {0: "Mo.", 1: "Di.", 2: "Mi.", 3: "Do.", 4: "Fr.", 5: "Sa.", 6: "So."}


def parse_date(s):
    """Parse date string in DD.MM.YY or DD.MM.YYYY format."""
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def weekday_german(d):
    """Return German weekday abbreviation for a date."""
    return WEEKDAYS[d.weekday()]


def collect_arrivals(days=21):
    """Read overview files and return arrivals within next N days, sorted by date."""
    today = date.today()
    cutoff = today + timedelta(days=days)
    arrivals = []
    for fp in sorted(SRC.glob("*.txt")):
        home = fp.stem
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip() or "Belegungen" in line or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            try:
                arr = parse_date(parts[2])
            except ValueError:
                continue
            if not (today <= arr <= cutoff):
                continue
            try:
                length = int(parts[4])
            except ValueError:
                length = None
            try:
                nums = [int(n) for n in parts[5].split("/")]
                guest_count = nums[0] + (nums[1] if len(nums) > 1 else 0)
            except (ValueError, IndexError):
                guest_count = None
            arrivals.append((arr, home, guest_count, length))
    return sorted(arrivals, key=lambda x: x[0])


def week_label(arrival, today):
    """Return week heading for an arrival date relative to today."""
    days_ahead = (arrival - today).days
    monday_offset = today.weekday()
    end_of_this_week = 6 - monday_offset  # days until Sunday
    if days_ahead <= end_of_this_week:
        return "Diese Woche"
    elif days_ahead <= end_of_this_week + 7:
        return "Nächste Woche"
    return "Übernächste Woche"


def generate_html(arrivals):
    """Build minimal HTML page listing upcoming arrivals grouped by week."""
    today = date.today()
    lines = [
        "<html>",
        "<head><meta charset='utf-8'></head>",
        "<body>",
        "<p><a href='calendar.html'>Visual Calendar</a> &nbsp; <a href='quick_overview.html'>Quick Overview</a> &nbsp; <a href='arrivals.html'>Arrivals</a> &nbsp; <a href='departures.html'>Departures</a></p>",
        "<br>",
        f"<h1>{weekday_german(today)} {today.strftime('%d.%m.%Y')} - Upcoming Arrivals</h1>",
    ]
    current_week = None
    for arr, home, count, length in arrivals:
        week = week_label(arr, today)
        if week != current_week:
            current_week = week
            lines.append(f"<h3>{week}</h3>")
        ppl = f"{count} Personen" if count else "? Personen"
        stay = f"für {length} {'Tag' if length == 1 else 'Tage'}" if length else "für ? Tage"
        lines.append(
            f"<p>{weekday_german(arr)} {arr.strftime('%d.%m.')} / {home} / {ppl} / {stay}</p>"
        )
    if not arrivals:
        lines.append("<p>Keine Anreisen in den nächsten 3 Wochen.</p>")
    lines += ["</body>", "</html>"]
    return "\n".join(lines)


def main():
    """Generate arrivals HTML page."""
    OUT.write_text(generate_html(collect_arrivals()), encoding="utf-8")


if __name__ == "__main__":
    main()
