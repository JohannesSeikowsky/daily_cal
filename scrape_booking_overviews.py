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

def scrape_fewo(fewo_name, url, append_mode=False):
    """Scrape booking data from v-office.com URL and save to file."""
    browser = setup_browser()
    try:
        browser.get(url)
        time.sleep(3)
        spans = [span.text for span in browser.find_elements(By.TAG_NAME, "span")]
        print(spans)

        # Filter out page headers
        spans = filter_page_headers(spans) # for when PdF has 2

        rows = parse_booking_rows(spans)
        print("here2")
        print(rows)
        display_name = get_fewo_name(fewo_name)
        print(display_name)
        output_file = PROJECT_PATH / "overviews" / f"{display_name}.txt"

        # Create file regardless of whether there are rows or not
        if rows:
            new_data = "\n".join("|".join(row) for row in rows)
            if append_mode and output_file.exists():
                # Append mode: add newline separator + new data
                existing = output_file.read_text()
                output_file.write_text(existing + "\n" + new_data)
            else:
                # First URL or single URL: overwrite
                output_file.write_text(new_data)
        else:
            # No data from this URL
            print("no rows")
            if not append_mode:
                output_file.write_text("")

    except Exception as e:
        print(str(e))
        if "Res.-Nr." not in str(e):
            pass
    finally:
        browser.quit()
        time.sleep(12)

def main():
    """Scrape all properties, handling single URLs or lists of URLs."""
    for fewo_name, urls in FEWOS.items():
        # Normalize to list (handles both string and list)
        url_list = urls if isinstance(urls, list) else [urls]
        # Filter out empty strings
        url_list = [url for url in url_list if url.strip()]

        for idx, url in enumerate(url_list):
            # First URL overwrites, subsequent URLs append
            append = (idx > 0)
            scrape_fewo(fewo_name, url, append_mode=append)

if __name__ == "__main__":
    main()


