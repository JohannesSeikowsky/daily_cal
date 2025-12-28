# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a holiday home (Ferienwohnung/"Fewo") management system that scrapes booking data from v-office.com partner portals, generates booking calendars, and sends automated email reports. It manages 18+ vacation rental properties.

## Core Architecture

### Data Flow
1. **Scraping** (`scrape_booking_overviews.py`): Selenium scrapes booking data from v-office.com URLs → saves to `overviews/*.txt`
2. **Calendar Generation** (`visual_cal.py`): Reads `overviews/*.txt` → generates interactive `calendar.html`
3. **Email Reports**: Multiple scripts read `overviews/*.txt` → generate and send email summaries

### Key Components

**Booking Data Sources**
- `overviews/*.txt`: Plain text booking data scraped from v-office.com (one file per property)
- Format: `booking_id|guest|arrival|departure|days|people|pets|revenue1|revenue2|apartment`
- Dates in DD.MM.YY format

**Calendar System** (`visual_cal.py`)
- Generates password-protected HTML calendar from booking data
- Tracks "new" bookings (added within last 7 days) via `seen_bookings.json`
- Supports blocked-out dates from `blocked_out_dates.txt`
- Auto-refresh and cache-busting for live deployments
- Same-day turnover detection (departure day = next arrival day)

**Email Reports**
- `daily_update.py`: Daily arrivals and departures
- `bookings_overview.py`: Full booking overview with v-office admin links
- `departures_and_arrivals.py`: 36-day departure report with next arrival info
- `double_bookings.py`: Alerts for consecutive bookings by same guest

**Utilities** (`utils.py`)
- `get_email_recipients(category)`: Load email recipients from .env (categories: 'main', 'cleaning', 'test', 'errors')
- `send_email()`: Yahoo SMTP email sender
- `error_email()`: Send error notifications
- Date formatting helpers (`prepend_weekday()`, `order_by_date()`)
- Property name transformations (`get_fewo_name()`)

## Common Commands

### Run Scrapers
```bash
python scrape_booking_overviews.py  # Scrape all properties (takes ~4 min)
```

**Adding second URLs per property:**
All entries in FEWOS dictionary are lists with second element as empty string placeholder:
```python
"Property": ["url1", ""]  # Paste second URL to replace empty string
```
Empty URLs are automatically skipped during scraping.

### Generate Calendar
```bash
python visual_cal.py  # Creates calendar.html
```

### Generate Reports
```bash
python daily_update.py              # Today's arrivals/departures
python bookings_overview.py         # Full booking overview
python departures_and_arrivals.py   # 36-day departure report
python double_bookings.py           # Check for consecutive bookings
```

### Git Workflow
```bash
git status                # Check changes
git add <files>          # Stage changes
git commit -m "message"  # Commit with concise message
git push origin master   # Push to remote
```

Note: `calendar.html` is generated and tracked in git for deployment purposes.

## Critical Details

**Property List** (`HOMES_ORDER` in `visual_cal.py`)
- Defines display order for all 18 properties
- Keep synchronized across files when adding/removing properties

**Hardcoded Paths**
- Project path: `/home/johannes/code/fewo_new_new/`
- Firefox binary: `/usr/bin/firefox`
- geckodriver: `/home/johannes/Desktop/geckodriver`

**Email Configuration**
- SMTP: Yahoo (smtp.mail.yahoo.com:587)
- Credentials in `.env` (SMTP_USERNAME, SMTP_PASSWORD)
- Email recipients configured in `.env` (EMAIL_RECIPIENTS_MAIN, EMAIL_RECIPIENT_CLEANING)

**Date Handling**
- Input format: DD.MM.YY (from v-office.com)
- Parse with: `datetime.strptime(date_str, "%d.%m.%y")`
- Booking end dates are inclusive (checkout day)

**Scraper Details**
- Uses headless Firefox with Selenium
- Parses v-office.com "print stats" pages (span elements)
- Supports multiple URLs per property: FEWOS dictionary accepts either a single URL string or a list of URLs
- Multiple URLs for same property are merged into single output file
- Special handling for "Bös Lütte Stuuv" (different page structure)
- 12-second delay between all URL fetches to avoid rate limiting
- Filters out page headers for multi-page PDFs
- Summary lines ("X Belegungen") filtered by visual_cal.py and email scripts

## File Structure

```
/
├── scrape_booking_overviews.py  # Web scraper (Selenium)
├── visual_cal.py                # Calendar HTML generator
├── daily_update.py              # Daily arrival/departure report
├── bookings_overview.py         # Full booking overview email
├── departures_and_arrivals.py   # 36-day departure forecast
├── double_bookings.py           # Consecutive booking detector
├── utils.py                     # Shared utilities
├── push_calendar.sh             # Git deployment script
├── calendar.html                # Generated calendar (only file tracked by git)
├── overviews/*.txt              # Scraped booking data (not tracked)
├── seen_bookings.json           # Tracks "new" bookings for calendar
├── prolonged_bookings_history.json  # Tracks reported consecutive bookings
└── blocked_out_dates.txt        # Manual blocked dates (CSV format)
```

## Testing Notes

- No formal test suite
- Test scrapers by checking `overviews/*.txt` files are populated
- Test calendar by opening `calendar.html` in browser (default password: "REDACTED")
- Email scripts can be tested by setting EMAIL_RECIPIENT_TEST in .env

## Version Control

**Tracked:**
- All Python source files (*.py)
- Scripts (*.sh)
- Configuration files (.gitignore, CLAUDE.md, blocked_out_dates.txt)
- Generated calendar (calendar.html) for deployment

**Not Tracked:**
- Scraped booking data (overviews/*.txt)
- Runtime state (seen_bookings.json, prolonged_bookings_history.json)
- Logs (*.log)
- Virtual environment (myenv/)
- Sensitive files (calendar_password.txt, .env)

## Security Best Practices

**Never commit sensitive data to git:**
- Email addresses → Store in .env (EMAIL_RECIPIENTS_*)
- SMTP credentials → Already in .env (SMTP_USERNAME, SMTP_PASSWORD)
- API tokens → Store in urls_config.py (already gitignored)
- Passwords → Store in .env or separate config files

**Verify before committing:**
```bash
# Check for accidentally committed emails
git diff --cached | grep -E '@(gmail|yahoo|hotmail)\.com'

# Verify .env is gitignored
git check-ignore .env
```
