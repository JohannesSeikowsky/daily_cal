import os
import datetime
import sys
import time
from pathlib import Path
from collections import defaultdict
from utils import send_email, error_email, get_email_recipients

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")
OVERVIEWS_DIR = PROJECT_PATH / "overviews"

def parse_date(date_str):
    """Convert string date in DD.MM.YY format to datetime object"""
    try:
        return datetime.datetime.strptime(date_str.strip(), "%d.%m.%y")
    except ValueError:
        return None

def format_date(date):
    """Format datetime object as DD.MM.YY string"""
    if not date:
        return "keine"
    return date.strftime("%d.%m.%y")

def format_people_info(people_str):
    """Format people information (adults/children/babies)"""
    try:
        adults, kids, babies = [int(x.strip()) for x in people_str.split('/')]
        
        people_info = f"{adults} Erwachsene"
        if kids > 0: people_info += f" | {kids} Kinder"
        if babies > 0: people_info += f" | {babies} Babies"
        
        return people_info
    except (ValueError, IndexError):
        return "Unbekannt"

def get_next_arrival_info(home_name, departure_date):
    """Find earliest arrival date and people info after or on the same day as specified date"""
    file_path = OVERVIEWS_DIR / f"{home_name}.txt"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}", file=sys.stderr)
        return "keine", None
    
    # Debug: Print the dates we're looking at
    print(f"Finding next arrival for {home_name} after {departure_date.strftime('%d.%m.%y')}", file=sys.stderr)
    
    next_arrival = None
    next_people_info = None
    
    try:
        with open(file_path, 'r') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line or "Belegungen" in line:
                    continue
                
                parts = line.split('|')
                if len(parts) < 6:  # Need ref, guest, arrival, departure, days, people info
                    continue
                
                # Get arrival date (index 2) and people info (index 5)
                arrival_str = parts[2].strip()
                people_str = parts[5].strip()
                
                # Debug information
                print(f"  Line {line_num}: Arrival date: '{arrival_str}', People: '{people_str}'", file=sys.stderr)
                
                try:
                    arrival_date = datetime.datetime.strptime(arrival_str, "%d.%m.%y")
                    
                    # Debug: Print the date comparison
                    print(f"  Comparing: arrival {arrival_date.date()} >= departure {departure_date.date()} = {arrival_date.date() >= departure_date.date()}", file=sys.stderr)
                    
                    # Include arrivals on the same day as departures
                    if arrival_date.date() >= departure_date.date():
                        if next_arrival is None or arrival_date < next_arrival:
                            next_arrival = arrival_date
                            next_people_info = people_str
                            print(f"  Found potential next arrival: {arrival_date.strftime('%d.%m.%y')}, People: {people_str}", file=sys.stderr)
                except ValueError as e:
                    print(f"  Error parsing date '{arrival_str}': {e}", file=sys.stderr)
                    continue
    except Exception as e:
        print(f"Error reading {home_name}: {e}", file=sys.stderr)
    
    if next_arrival:
        print(f"Next arrival for {home_name}: {next_arrival.strftime('%d.%m.%y')}", file=sys.stderr)
        return format_date(next_arrival), format_people_info(next_people_info) if next_people_info else "Unbekannt"
    
    print(f"No next arrival found for {home_name}", file=sys.stderr)
    return "keine", None

def get_departures_for_period(start_date, days):
    """Collect all departures organized by date for the specified period for all holiday homes"""
    departures_by_day = defaultdict(list)
    
    if not os.path.exists(OVERVIEWS_DIR):
        print(f"Error: Directory {OVERVIEWS_DIR} not found", file=sys.stderr)
        return departures_by_day
    
    for file in os.listdir(OVERVIEWS_DIR):
        if not file.endswith(".txt"):
            continue
        
        home_name = file[:-4]  # Remove .txt extension
        file_path = os.path.join(OVERVIEWS_DIR, file)
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or "Belegungen" in line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) < 4:
                        continue
                    
                    # Get departure date (index 3)
                    departure_str = parts[3].strip()
                    try:
                        departure_date = datetime.datetime.strptime(departure_str, "%d.%m.%y")
                        
                        # Check if departure is within our period
                        delta = (departure_date.date() - start_date.date()).days
                        if 0 <= delta < days:
                            departures_by_day[departure_date.date()].append(home_name)
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error processing {file}: {e}", file=sys.stderr)
    
    return departures_by_day

def generate_report():
    """Create a 35-day report showing departures and next arrivals for each holiday home"""
    today = datetime.datetime.today()
    days = 36
    
    departures = get_departures_for_period(today, days)
    
    result = []
    for day_offset in range(days):
        current_date = today.date() + datetime.timedelta(days=day_offset)
        weekday = current_date.strftime("%A")
        date_str = current_date.strftime("%d.%m.%y")
        
        result.append(f"{weekday} ({date_str})")
        
        if current_date in departures and departures[current_date]:
            for home in departures[current_date]:
                # Convert date objects to datetime for consistency
                current_datetime = datetime.datetime.combine(current_date, datetime.time.min)
                next_arrival_date, people_info = get_next_arrival_info(home, current_datetime)
                
                if people_info:
                    result.append(f"{home} | next arrival: {next_arrival_date} | {people_info}")
                else:
                    result.append(f"{home} | next arrival: {next_arrival_date}")
        else:
            result.append("-")
        
        result.append("")  # Empty line between days
    
    return "\n".join(result)

def main():
    """Generate and print the departures and next arrivals report and send via email"""
    try:
        report = generate_report()
        subject = f"Departures and Arrivals"
        print(report)
        try:
            all_recipients = get_email_recipients('main') + get_email_recipients('cleaning')
            for recipient in all_recipients:
                send_email(subject, report, recipient)
                time.sleep(8)
        except Exception as e:
            error_msg = f"Failed to send departures report by email: {str(e)}"
            print(error_msg, file=sys.stderr)
            error_email(error_msg)
            
    except Exception as e:
        error_msg = f"Fatal error generating departures report: {str(e)}"
        print(error_msg, file=sys.stderr)
        error_email(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
