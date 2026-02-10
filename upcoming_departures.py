"""Generate a simple HTML page listing departures in the next 3 weeks."""

from pathlib import Path
from datetime import date, timedelta, datetime

ROOT = Path(__file__).parent
SRC = ROOT / "overviews"
OUT = ROOT / "departures.html"

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


def collect_departures(days=21):
    """Read overview files and return departures within next N days, sorted by date."""
    today = date.today()
    cutoff = today + timedelta(days=days)
    departures = []
    for fp in sorted(SRC.glob("*.txt")):
        home = fp.stem
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip() or "Belegungen" in line or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            try:
                dep = parse_date(parts[3])
            except ValueError:
                continue
            if not (today <= dep <= cutoff):
                continue
            departures.append((dep, home))
    return sorted(departures, key=lambda x: x[0])


def week_label(d, today):
    """Return week heading for a date relative to today."""
    days_ahead = (d - today).days
    end_of_this_week = 6 - today.weekday()
    if days_ahead <= end_of_this_week:
        return "Diese Woche"
    elif days_ahead <= end_of_this_week + 7:
        return "Nächste Woche"
    return "Übernächste Woche"


def generate_html(departures):
    """Build minimal HTML page listing upcoming departures grouped by week."""
    today = date.today()
    lines = [
        "<html>",
        "<head><meta charset='utf-8'></head>",
        "<body>",
        "<p><a href='calendar.html'>Visual Calendar</a> &nbsp; <a href='quick_overview.html'>Quick Overview</a> &nbsp; <a href='arrivals.html'>Arrivals</a> &nbsp; <a href='departures.html'>Departures</a></p>",
        "<br>",
        f"<h1>{weekday_german(today)} {today.strftime('%d.%m.%Y')} - Upcoming Departures</h1>",
    ]
    current_week = None
    for dep, home in departures:
        week = week_label(dep, today)
        if week != current_week:
            current_week = week
            lines.append(f"<h3>{week}</h3>")
        lines.append(f"<p>{weekday_german(dep)} {dep.strftime('%d.%m.')} / {home}</p>")
    if not departures:
        lines.append("<p>Keine Abreisen in den nächsten 3 Wochen.</p>")
    lines += ["</body>", "</html>"]
    return "\n".join(lines)


def main():
    """Generate departures HTML page."""
    OUT.write_text(generate_html(collect_departures()), encoding="utf-8")


if __name__ == "__main__":
    main()
