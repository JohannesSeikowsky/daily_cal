# utils
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed, will use os.environ directly


project_path = "/home/johannes/code/fewo_new_new/"
fewos = ["Sonnenwende", "Dämmerlicht", "Regenbogen", "Wolke 7", "Küstenzauber", "Strandliebe",  "Wellengang", "Lüdde Wattwurm", "Kl. Austernfischer", "Austernfischer", "Dat Lütte Huus1", "Dat Lütte Huus2", "Lütte Stuuv", "Groote Stuuv", "Fischers Huus", "Michels Koje", "Fietes Kajüte", "Fietes Lütte Huus", "Bös Lütte Stuuv"]


def read_file(path):
    with open(path, "r") as f:
        content = f.read()
    return content


def get_fewo_name(fewo):
    """ transforms the technical name of a fewo into a more suitable display name.
        Adding the Jebensweg Addresse to the Fewo nickname for instance. """
    names = {fewo: fewo for fewo in fewos} # set defaults
    # add Jebensweg addresses to nicknames
    jebens_fewos = [["Sonnenwende", "2a"], 
                    ["Dämmerlicht", "2b"], 
                    ["Regenbogen", "2c"],
                    ["Wolke 7", "2d"],
                    ["Küstenzauber", "4a"], 
                    ["Strandliebe", "4b"],
                    ["Wellengang", "4c"],
                    ["Lüdde Wattwurm", "4d"]]
    for each in jebens_fewos:
        name, address = each[0], each[1]
        names[name] = name + " " + address
    #print(names)
    names["Wolke 7"] = "Wolke7 2d" # special case
    return names[fewo]
#get_fewo_name("Wellengang")


def get_email_recipients(category='main'):
	"""Load email recipients from .env file."""
	if category == 'main':
		recipients = os.environ.get("EMAIL_RECIPIENTS_MAIN", "").split(',')
	elif category == 'cleaning':
		recipients = os.environ.get("EMAIL_RECIPIENT_CLEANING", "").split(',')
	elif category == 'test':
		recipients = [os.environ.get("EMAIL_RECIPIENT_TEST", "")]
	elif category == 'errors':
		recipients = [os.environ.get("EMAIL_RECIPIENT_ERRORS", "")]
	else:
		return []
	return [r.strip() for r in recipients if r.strip()]


def send_email(subject, content, recipient):
  SMTP_SERVER = "smtp.mail.yahoo.com"
  SMTP_PORT = 587
  SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
  SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
  EMAIL_FROM = os.environ.get("SMTP_USERNAME", "")
  EMAIL_TO = recipient

  msg = MIMEText(content)
  msg['Subject'] = subject
  msg['From'] = EMAIL_FROM
  msg['To'] = EMAIL_TO
  debuglevel = True
  mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
  mail.set_debuglevel(debuglevel)
  mail.starttls()
  mail.login(SMTP_USERNAME, SMTP_PASSWORD)
  mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
  mail.quit()


def error_email(error_message):
	"""Send error notification email."""
	recipients = get_email_recipients('errors')
	if recipients:
		send_email("Error in Fewo Code", error_message, recipients[0])


def order_by_date(bookings):
	"Order set of booking bookings by their respective starting dates."
	def order_by_start_date(booking):
		start_date = booking[0].split(" ")[1].strip()
		return datetime.strptime(start_date, "%d.%m.%y")
	return sorted(bookings, key=order_by_start_date)


def prepend_weekday(date):
	""" Prepend weekday abbreviation to a date passed in as a string.
	'28.05.21' --> 'Fr. 28.05.21 """
	weekdays = {0: "Mo.", 1: "Di.", 2: "Mi.", 3: "Do.", 4: "Fr.", 5: "Sa.", 6: "So."}
	weekday = datetime.strptime(date, '%d.%m.%y').weekday()
	weekday = weekdays[weekday]
	return weekday + " " + date


def order_email(email):
	""" Put the Fewos that are in the composed Email in the order preffered by Muddi. """
	preffered_order = ["Sonnenwende", "Dämmerlicht", "Regenbogen", "Wolke 7", "Küstenzauber", "Strandliebe",  "Wellengang", "Lüdde Wattwurm", 
				"Kl. Austernfischer", "Austernfischer", "Doras & Hannes Hus", "Dat Lütte Huus1", "Dat Lütte Huus2", "Lütte Stuuv", "Groote Stuuv"]

	# Go over the Fewos in the Email and order them in accordance with the preffered order.
	fewos = email.split("\n\n")
	ordered_fewos = []

	for part in preffered_order:
		for fewo in fewos:
			fewo_name = fewo.split("\n")[0]
			if part == fewo_name:
				ordered_fewos.append(fewo)

	ordered_email = "\n\n".join(ordered_fewos)
	return ordered_email


def format_booking(booking):
	"""Take in booking in this format: 'Matic, Andrea|06.09.21|11.09.21|5|2 / 0 / 0|0|Dämmerlicht' and
	format it into a more human-friendly version."""
	ref, name, arr, dep, days, persons, pets, revenue1, revenue2,  apartment = booking.split("|")
	adults, kids, babies = persons.split(" / ")
	booking_formatted = "|".join([name, arr, dep, apartment, adults + " Erwachsene", kids + " Kinder", babies + " Babies", pets + " Haustiere"])
	return booking_formatted