from pathlib import Path
import datetime as dt
from collections import defaultdict

ROOT = Path(__file__).parent
SRC = ROOT / "overviews"
OUT = ROOT / "repeat_guests.txt"

def parse_date(s: str) -> dt.date:
    """Parse date in DD.MM.YY or DD.MM.YYYY format."""
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s}")

def collect_guest_visits():
    """Collect all visits per guest name."""
    guest_visits = defaultdict(list)

    for fp in sorted(SRC.glob("*.txt")):
        home = fp.stem
        lines = [ln for ln in fp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        lines = [ln for ln in lines if "Belegungen" not in ln]

        for line in lines:
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 4:
                continue

            try:
                guest = parts[1]
                start = parse_date(parts[2])
                end = parse_date(parts[3])
            except Exception:
                continue

            if end < start:
                continue

            guest_visits[guest].append({
                'home': home,
                'start': start,
                'end': end
            })

    return guest_visits

def main():
    """Find and display repeat guests."""
    guest_visits = collect_guest_visits()

    # Filter for guests with multiple visits
    repeat_guests = {guest: visits for guest, visits in guest_visits.items()
                     if len(visits) > 1}

    if not repeat_guests:
        msg = "No repeat guests found."
        print(msg)
        OUT.write_text(msg, encoding="utf-8")
        return

    # Sort by number of visits (descending), then by guest name
    sorted_guests = sorted(repeat_guests.items(),
                          key=lambda x: (-len(x[1]), x[0]))

    lines = []
    lines.append(f"Found {len(repeat_guests)} guests with multiple visits:\n")

    for guest, visits in sorted_guests:
        lines.append(f"{guest} ({len(visits)} visits):")
        # Sort visits by start date
        for visit in sorted(visits, key=lambda v: v['start']):
            lines.append(f"  - {visit['home']}: {visit['start'].strftime('%d.%m.%Y')} - {visit['end'].strftime('%d.%m.%Y')}")
        lines.append("")

    output = "\n".join(lines)
    print(output)
    OUT.write_text(output, encoding="utf-8")
    print(f"\nResults saved to {OUT}")

if __name__ == "__main__":
    main()
