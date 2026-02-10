"""Generate a Quick Overview HTML page showing current occupancy of all properties."""

from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).parent
SRC = ROOT / "overviews"
OUT = ROOT / "quick_overview.html"

WEEKDAYS = {0: "Mo.", 1: "Di.", 2: "Mi.", 3: "Do.", 4: "Fr.", 5: "Sa.", 6: "So."}

HOMES = [
    "Sonnenwende 2a", "Dämmerlicht 2b", "Regenbogen 2c", "Wolke7 2d",
    "Küstenzauber 4a", "Strandliebe 4b", "Wellengang 4c", "Lüdde Wattwurm 4d",
    "Kl. Austernfischer", "Austernfischer",
    "Dat Lütte Huus1", "Dat Lütte Huus2",
    "Lütte Stuuv", "Fischers Huus", "Michels Koje",
    "Fietes Kajüte", "Fietes Lütte Huus", "Bös Lütte Stuuv",
]


def parse_date(s):
    """Parse date string in DD.MM.YY or DD.MM.YYYY format."""
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")


def get_status():
    """Return dict {home: tagged tuple} for all properties."""
    today = date.today()
    status = {}
    for home in HOMES:
        fp = SRC / f"{home}.txt"
        if not fp.exists():
            status[home] = ("empty",)
            continue
        current = None
        next_arrival = None
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line.strip() or "Belegungen" in line or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue
            try:
                arrival = parse_date(parts[2])
                departure = parse_date(parts[3])
            except ValueError:
                continue
            if arrival <= today <= departure and current is None:
                try:
                    nums = [int(n) for n in parts[5].split("/")]
                    guest_count = nums[0] + (nums[1] if len(nums) > 1 else 0)
                except (ValueError, IndexError):
                    guest_count = None
                current = ("occupied", guest_count, (departure - today).days)
            if arrival > today:
                if next_arrival is None or arrival < next_arrival:
                    next_arrival = arrival
        if current:
            status[home] = current
        elif next_arrival:
            status[home] = ("vacant", (next_arrival - today).days)
        else:
            status[home] = ("empty",)
    return status


def generate_html(status):
    """Build minimal HTML table showing occupancy status of all properties."""
    today = date.today()
    wd = WEEKDAYS[today.weekday()]
    lines = [
        "<html>",
        "<head><meta charset='utf-8'></head>",
        "<body>",
        f"<h1>{wd} {today.strftime('%d.%m.%Y')} - Quick Overview</h1>",
        "<table>",
    ]
    for home in HOMES:
        info = status[home]
        tag = info[0]
        if tag == "occupied":
            count, remaining = info[1], info[2]
            ppl = f"{count} Pers." if count else "? Pers."
            if remaining == 0:
                text = f"{ppl}, Abreise heute"
            elif remaining == 1:
                text = f"{ppl}, noch 1 Tag"
            else:
                text = f"{ppl}, noch {remaining} Tage"
        elif tag == "vacant":
            days = info[1]
            if days == 1:
                text = "— arrival in 1 day"
            else:
                text = f"— arrival in {days} days"
        else:
            text = "— keine Buchungen"
        lines.append(f"<tr><td><b>{home}</b></td><td>{text}</td></tr>")
    lines += ["</table>", "</body>", "</html>"]
    return "\n".join(lines)


def main():
    """Generate quick overview HTML page."""
    OUT.write_text(generate_html(get_status()), encoding="utf-8")


if __name__ == "__main__":
    main()
