import os
import time
import datetime
from pathlib import Path
from utils import send_email, prepend_weekday, error_email, get_email_recipients
from urls_config import ADMIN_URLS

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")
OVERVIEWS_DIR = PROJECT_PATH / "overviews"

order = ["Sonnenwende 2a", "Dämmerlicht 2b", "Regenbogen 2c", "Wolke7 2d", "Küstenzauber 4a", "Strandliebe 4b", "Wellengang 4c", "Lüdde Wattwurm 4d", "Kl. Austernfischer", "Austernfischer", "Dat Lütte Huus1", "Dat Lütte Huus2", "Lütte Stuuv", "Fischers Huus", "Michels Koje", "Fietes Kajüte", "Fietes Lütte Huus", "Bös Lütte Stuuv"]


def format_booking(parts):
    _, guest, arrival, departure, _, people, *_ = parts
    
    arrival_with_day = prepend_weekday(arrival)
    departure_with_day = prepend_weekday(departure)
    
    adults, kids, babies = [int(x.strip()) for x in people.split('/')]
    
    people_info = f"{adults} Erwachsene"
    if kids > 0: people_info += f" | {kids} Kinder"
    if babies > 0: people_info += f" | {babies} Babies"
    
    return f"{arrival_with_day} - {departure_with_day} | {guest} | {people_info}"

def is_relevant_booking(arrival_date, departure_date):
    today = datetime.datetime.today()
    arrival = datetime.datetime.strptime(arrival_date.strip(), "%d.%m.%y")
    departure = datetime.datetime.strptime(departure_date.strip(), "%d.%m.%y")
    
    # Include bookings that:
    # 1. Start in the future, or
    # 2. Are currently active (started in the past but end in the future)
    return arrival >= today - datetime.timedelta(days=1) or (arrival < today and departure >= today)

def generate_email():
    fewo_data = []
    errors = []
    
    for fewo_name in order:
        filename = fewo_name + ".txt"
        file_path = OVERVIEWS_DIR / filename
        
        if not file_path.exists():
            continue
            
        try:
            with open(file_path, 'r') as file:
                bookings = []
                for line in file:
                    line = line.strip()
                    if not line or "Belegungen" in line:
                        continue
                        
                    parts = line.split('|')
                    if len(parts) >= 9:
                        arrival_date = parts[2]
                        departure_date = parts[3]
                        
                        if is_relevant_booking(arrival_date, departure_date):
                            bookings.append(format_booking(parts))
                
                if bookings:
                    fewo_data.append(f"{fewo_name}\n{'\n'.join(bookings)}")
                    
        except Exception as e:
            errors.append(f"Error processing {fewo_name}: {str(e)}")
    
    if errors:
        error_email("\n".join(["Error generating booking email:"] + errors))
    
    return "\n\n".join(fewo_data)


def add_vpartner_links(email_body):
    email_body += "\n\nAdmin Bereich 1 - Muddi & Vaddi\n" + ADMIN_URLS["admin_url_1"]
    email_body += "\n\nAdmin Bereich 2 - Vaddi\n" + ADMIN_URLS["admin_url_2"]
    email_body +=  "\n\nAdmin Bereich 3 - Muddi\n" + ADMIN_URLS["admin_url_3"]
    email_body += "\n\nAdmin Bereich 4 - Westend\n" + ADMIN_URLS["admin_url_4"]
    email_body += "\n\nAdmin Bereich 5 - Alex\n" + ADMIN_URLS["admin_url_5"]
    email_body += "\n\nAdmin Bereich 6 - Oma\n" + ADMIN_URLS["admin_url_6"]
    return email_body


def main():
    try:
        email_body = generate_email()
        email_body = add_vpartner_links(email_body)
        recipients = get_email_recipients('main')
        for recipient in recipients:
            send_email(f"Bookings Overview", email_body, recipient)
            time.sleep(8)
        print(email_body)
    except Exception as e:
        error_email(f"Failed to generate or send booking email: {str(e)}")

if __name__ == "__main__":
    main()