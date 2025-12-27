import os
import json
import datetime
import time
from pathlib import Path
from utils import send_email, error_email, get_email_recipients

PROJECT_PATH = Path("/home/johannes/code/fewo_new_new/")
OVERVIEWS_DIR = PROJECT_PATH / "overviews"
HISTORY_FILE = PROJECT_PATH / "prolonged_bookings_history.json"

def parse_booking(line):
    parts = line.strip().split('|')
    if len(parts) < 9 or "Belegungen" in line:
        return None
    
    booking_id, guest, arrival, departure = parts[0], parts[1], parts[2], parts[3]
    return {
        'id': booking_id,
        'guest': guest.strip(),
        'arrival': arrival.strip(),
        'departure': departure.strip(),
    }

def load_history():
    if not HISTORY_FILE.exists():
        return {}
    
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        error_email(f"Error loading history file: {str(e)}")
        return {}

def save_history(history):
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        error_email(f"Error saving history file: {str(e)}")

def find_consecutive_bookings():
    history = load_history()
    new_consecutive_bookings = []
    
    for file_path in OVERVIEWS_DIR.glob('*.txt'):
        fewo_name = file_path.stem
        
        try:
            with open(file_path, 'r') as file:
                bookings = []
                for line in file:
                    booking = parse_booking(line)
                    if booking:
                        bookings.append(booking)
                
                # Sort bookings by arrival date
                bookings.sort(key=lambda x: datetime.datetime.strptime(x['arrival'], "%d.%m.%y"))
                
                # Check for consecutive bookings by the same guest
                for i in range(len(bookings) - 1):
                    current = bookings[i]
                    next_booking = bookings[i + 1]
                    
                    # Check if same guest and consecutive dates
                    if (current['guest'] == next_booking['guest'] and 
                        current['departure'] == next_booking['arrival']):
                        
                        # Create a unique identifier for this consecutive booking pair
                        booking_pair_id = f"{fewo_name}_{current['id']}_{next_booking['id']}"
                        
                        # Check if we've already reported this consecutive booking
                        if booking_pair_id not in history:
                            consecutive_info = {
                                'fewo': fewo_name,
                                'guest': current['guest'],
                                'first_booking': {
                                    'id': current['id'],
                                    'arrival': current['arrival'],
                                    'departure': current['departure']
                                },
                                'second_booking': {
                                    'id': next_booking['id'],
                                    'arrival': next_booking['arrival'],
                                    'departure': next_booking['departure']
                                }
                            }
                            new_consecutive_bookings.append(consecutive_info)
                            
                            # Add to history so we don't report it again
                            history[booking_pair_id] = {
                                'reported_date': datetime.datetime.now().strftime("%Y-%m-%d"),
                                'details': consecutive_info
                            }
        
        except Exception as e:
            error_email(f"Error processing {fewo_name}: {str(e)}")
    
    # Save updated history
    save_history(history)
    
    return new_consecutive_bookings

def generate_email_content(consecutive_bookings):
    if not consecutive_bookings:
        return None
    
    lines = ["Doppelbuchungen Alert:", ""]
    
    for booking in consecutive_bookings:
        fewo = booking['fewo']
        guest = booking['guest']
        first = booking['first_booking']
        second = booking['second_booking']
        
        lines.append(f"Holiday Home: {fewo}")
        lines.append(f"Guest: {guest}")
        lines.append(f"First Booking: {first['arrival']} - {first['departure']}")
        lines.append(f"Second Booking: {second['arrival']} - {second['departure']}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    try:
        consecutive_bookings = find_consecutive_bookings()
        
        if consecutive_bookings:
            email_content = generate_email_content(consecutive_bookings)
            all_recipients = get_email_recipients('main') + get_email_recipients('cleaning')
            for recipient in all_recipients:
                send_email("Doppelbuchungen Alert", email_content, recipient)
                time.sleep(8)
            print(email_content)
        else:
            print("No new consecutive bookings found.")
            
    except Exception as e:
        error_email(f"Failed to check for consecutive bookings: {str(e)}")

if __name__ == "__main__":
    main()
