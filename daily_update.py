import os
import datetime
import time
from pathlib import Path
from collections import defaultdict
from utils import send_email, error_email, get_email_recipients

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")
OVERVIEWS_DIR = PROJECT_PATH / "overviews"

def get_todays_events():
    """Get all arrivals and departures happening today across all holiday homes"""
    today = datetime.datetime.today().date()
    today_str = today.strftime("%d.%m.%y")
    
    arrivals = []
    departures = []
    
    for file in os.listdir(OVERVIEWS_DIR):
        if not file.endswith(".txt"):
            continue
        
        home_name = file[:-4]  # Remove .txt extension
        file_path = OVERVIEWS_DIR / file
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("Belegungen"):
                        continue
                    
                    parts = line.split('|')
                    if len(parts) < 4:
                        continue
                    
                    arrival_str = parts[2].strip()
                    departure_str = parts[3].strip()
                    
                    if arrival_str == today_str:
                        arrivals.append(home_name)
                    
                    if departure_str == today_str:
                        departures.append(home_name)
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    return sorted(arrivals), sorted(departures)

def generate_email():
    """Generate email content with today's arrivals and departures"""
    arrivals, departures = get_todays_events()
    
    today = datetime.datetime.today().strftime("%d.%m.%y")
    subject = f"Daily"
    
    content = []
    
    content.append("Departures")
    if departures:
        for home in departures:
            content.append(f"- {home}")
    else:
        content.append("-")
    
    content.append("")
    
    content.append("Arrivals")
    if arrivals:
        for home in arrivals:
            content.append(f"- {home}")
    else:
        content.append("-")
    
    return subject, "\n".join(content)

def main():
    """Generate and send today's arrivals and departures email"""
    try:
        subject, content = generate_email()
        print(content)
        
        try:
            recipients = get_email_recipients('main')
            for recipient in recipients:
                send_email(subject, content, recipient)
                time.sleep(8)
        except Exception as e:
            error_email(f"Failed to send 'the daily mail' email: {e}")

    except Exception as e:
        error_msg = f"Error generating daily update email: {str(e)}"
        print(error_msg)
        error_email(error_msg)

if __name__ == "__main__":
    main()
