import time
import json
import smtplib
import ssl
import sys
import argparse
from email.message import EmailMessage
import requests 

def send_email(subject, body, config):
  """
  Sends a notification email using settings from the config file.
  """
  settings = config['email_settings']

  # Standard email
  msg = EmailMessage()
  msg.set_content(body)
  msg['Subject'] = subject
  msg['From'] = settings["sender_email"]
  msg['To'] = settings["receiver_email"]

  print(f"-> Preparing to send notification to {settings['receiver_email']}...", flush=True)

  # SMS email (optional)
  sms_target = settings.get("sms_gateway_email")
  msg_sms = None
  if sms_target:
    print(f"-> SMS gateway configured. Preparing SMS for {sms_target}...", flush=True)
    # For SMS, use the standard email subject as the message body
    sms_body = subject
    msg_sms = EmailMessage()
    msg_sms.set_content(sms_body)
    msg_sms['From'] = settings["sender_email"]
    msg_sms['To'] = sms_target

  try:
    context = ssl.create_default_context()
    with smtplib.SMTP(settings["smtp_server"], settings["smtp_port"]) as server:
      server.starttls(context=context)
      server.login(settings["sender_email"], settings["sender_password"])

      # Send standard email
      server.send_message(msg)
      print(f"-> Email sent successfully to {settings['receiver_email']}.", flush=True)

      # Send SMS email if it exists
      if msg_sms:
        server.send_message(msg_sms)
        print(f"-> SMS notification sent successfully to {sms_target}.", flush=True)

  except Exception as e:
    print(f"-> Failed to send notification(s): {e}", flush=True)

def check_course_api(course, config, session, debug_mode=False):
  """
  Checks a course's status by first POSTing the term to authorize the session,
  then GETting the search results.
  """
  course_name = f"{course['subject']} {course['course_number']} (CRN: {course['crn']})"
  print(f"  -> Checking {course_name}...")

  # Construct URLs from the config file
  uni_settings = config['university_settings']
  base_url = uni_settings['base_url'].rstrip('/') # Remove trailing slash if present
  term_search_url = base_url + uni_settings['term_search_endpoint']
  api_url = base_url + uni_settings['course_search_endpoint']

  try:
    # Authorize the session for the term
    term_payload = {'term': course['term_id']}
    term_response = session.post(term_search_url, data=term_payload, params={'mode': 'search'}, timeout=30)
    term_response.raise_for_status()
    
    # Search for the course
    search_params = {
      'txt_subject': course['subject'],
      'txt_courseNumber': course['course_number'],
      'txt_term': course['term_id'],
      'pageOffset': 0,
      'pageMaxSize': 50
    }

    response = session.get(api_url, params=search_params, timeout=30)
    response.raise_for_status()
    
    data = response.json()

    if debug_mode:
      print("  -> Debug: Full JSON response received:")
      print(json.dumps(data, indent=2))

    if not data.get('success') or data.get('totalCount') == 0:
      print(f"  -> No sections found for {course['subject']} {course['course_number']}. The course might not be offered this term.")
      return True 

    target_section = next((s for s in data.get('data', []) if s.get('courseReferenceNumber') == course['crn']), None)
    
    if not target_section:
      print(f"  -> CRN {course['crn']} not found in search results for this term.")
      return True

    seats_available = target_section.get('seatsAvailable', 0)
    capacity = target_section.get('maximumEnrollment', 0)
    status = "Full" if seats_available <= 0 else "Available"

    print(f"  -> Status: {seats_available} seats available out of {capacity} [{status}]")

    if seats_available > 0:
      print("\n  Seat found! Preparing notification...")
      subject = f"Seat available for {course_name}"
      body = (
        f"A spot has opened up for {course_name}\n\n"
        f"Seats available: {seats_available}\n"
        f"Total capacity: {capacity}\n\n"
        "Register as soon as possible!"
      )
      send_email(subject, body, config)
      return False

    return True

  except requests.exceptions.RequestException as e:
    print(f"  -> Network or HTTP error for {course_name}: {e}")
    return None
  except json.JSONDecodeError:
    print(f"  -> Failed to decode JSON response for {course_name}.")
    return None

def main():
  """
  The main process that schedules checks and handles errors.
  """
  parser = argparse.ArgumentParser(description="Check for available seats in a university course.")
  parser.add_argument('--debug', action='store_true', help='Enable debug mode for verbose output and to send a test email.')
  args = parser.parse_args()
  debug_mode = args.debug

  try:
    with open('config.json', 'r') as f:
      config = json.load(f)
  except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error: Could not load or parse config.json. Details: {e}")
    return
  
  if debug_mode:
    print("--- Debug mode enabled ---")
    print("-> Sending a test email to verify configuration...")
    send_email(
      "Course Checker - Test email", 
      "This is a test of your email notification settings. If you received this, the script can send emails successfully.", 
      config
    )

  settings = config['script_settings']
  consecutive_errors = 0
  
  session = requests.Session()
  session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
  })
  
  while True:
    print(f"--- Starting new check cycle at {time.strftime('%Y-%m-%d %H:%M:%S')} ---", flush=True)
    for course in config['courses_to_check']:
      if 'term_id' not in course:
        print(f"Error: 'term_id' (e.g., '202509') not found for course {course['crn']} in config.json. Skipping.")
        continue

      result = check_course_api(course, config, session, debug_mode)

      if result is None:
        consecutive_errors += 1
        print(f"  -> Consecutive error count: {consecutive_errors}", flush=True)
      elif not result:
        print("--- Seat found and notification sent. Exiting script. ---")
        return
      else:
        consecutive_errors = 0

      if consecutive_errors >= settings['consecutive_error_limit']:
        print(f"-> Reached {settings['consecutive_error_limit']} consecutive errors. Sending alert and exiting.", flush=True)
        subject = "Course Checker script has failed"
        body = f"The script has failed {settings['consecutive_error_limit']} times in a row and is shutting down. Please check the logs."
        send_email(subject, body, config)
        return
      
      time.sleep(settings['inter_course_delay_seconds'])

    print(f"--- Cycle complete. Waiting {settings['main_interval_seconds']}s for next cycle. ---", flush=True)
    time.sleep(settings['main_interval_seconds'])

if __name__ == "__main__":
  main()
