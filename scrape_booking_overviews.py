from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from utils import send_email, order_by_date, prepend_weekday, order_email, get_fewo_name
from urls_config import FEWOS
import datetime
import time
from pathlib import Path

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")

def setup_browser():
    options = Options()
    options.binary_location = "/usr/bin/firefox"
    options.add_argument("--headless")
    service = Service(executable_path="/home/johannes/Desktop/geckodriver")
    return webdriver.Firefox(options=options, service=service)

def is_future(date_str):
    date = datetime.datetime.strptime(date_str.strip(), "%d.%m.%y")
    return date >= datetime.datetime.today() - datetime.timedelta(days=1)

def parse_booking_rows(spans):
    try:
        start_idx = spans.index("Einnahmen") + 1
        spans = [span for span in spans[start_idx:-4] if span.strip() and "Storno" not in span]
        return [spans[i:i+9] for i in range(0, len(spans), 9)]
    except ValueError:
        # Fallback for Bös Lütte Stuuv - find res numbers directly
        res_nums = []
        for i, span in enumerate(spans):
            if span.strip().isdigit() and len(span.strip()) >= 5:
                res_nums.append(i)
        
        rows = []
        for idx in res_nums:
            if idx + 16 < len(spans):
                row = []
                for j in range(0, 18, 2):
                    if idx + j < len(spans):
                        row.append(spans[idx + j])
                if len(row) == 9:
                    rows.append(row)
        print(rows)
        return rows

def filter_page_headers(spans):
    filtered_spans = []
    skip_until_index = -1
    
    for i, span in enumerate(spans):
        if i <= skip_until_index:
            continue
            
        if span.startswith("Belegungsübersicht"):
            # Find the "Seite X von Y" span
            for j in range(i, min(i + 10, len(spans))):
                if "Seite" in spans[j] and "von" in spans[j]:
                    skip_until_index = j
                    break
        else:
            filtered_spans.append(span)
            
    return filtered_spans

def scrape_fewo(fewo_name, url):
    """Fetch one URL and return parsed rows, or None on failure."""
    browser = setup_browser()
    try:
        browser.get(url)
        time.sleep(3)
        spans = [span.text for span in browser.find_elements(By.TAG_NAME, "span")]
        print(spans)
        spans = filter_page_headers(spans)
        rows = parse_booking_rows(spans)
        print("here2")
        print(rows)
        return rows
    except Exception as e:
        print(str(e))
        return None
    finally:
        browser.quit()
        time.sleep(12)

def main():
    """Scrape all properties; only overwrite the overview file if data was retrieved."""
    for fewo_name, urls in FEWOS.items():
        url_list = urls if isinstance(urls, list) else [urls]
        url_list = [url for url in url_list if url.strip()]

        all_rows = []
        for url in url_list:
            rows = scrape_fewo(fewo_name, url)
            if rows:
                all_rows.extend(rows)

        # Only write if we got data. Preserves previous file on full failure,
        # preventing the cascade where an empty file wipes seen_bookings.json
        # and causes all bookings to be re-flagged as "new" next run.
        if all_rows:
            display_name = get_fewo_name(fewo_name)
            output_file = PROJECT_PATH / "overviews" / f"{display_name}.txt"
            output_file.write_text("\n".join("|".join(row) for row in all_rows))
            print(f"wrote {len(all_rows)} rows to {display_name}.txt")
        else:
            print(f"no rows for {fewo_name}; leaving existing file untouched")

if __name__ == "__main__":
    main()


