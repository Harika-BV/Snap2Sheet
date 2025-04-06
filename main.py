import os
import re
import json
import time
import base64
import openai
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from selenium.webdriver.common.action_chains import ActionChains
from datetime import datetime, date, timedelta
# Load OpenAI key from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Snap2Sheet").sheet1

# Time window
message_date = date(2025, 4, 6)
start = datetime(2025, 4, 6, 16, 0)   # 7:00 PM
end = datetime(2025, 4, 6, 17, 0)    # 8:00 PM

# Chrome options
chrome_options = Options()
chrome_options.add_argument("--user-data-dir=chrome-data")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Use webdriver-manager to install correct ChromeDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

driver.get("https://web.whatsapp.com")
input("📲 Scan QR code and press Enter to continue...")

# Make sure download folder exists
os.makedirs("downloads", exist_ok=True)


def scroll_up_until_start_time(driver, start_time, end_time, message_date):
    print("🔃 Scrolling down to find messages within time range...")
    last_msg_text = None
    attempts = 0
    max_attempts = 100
    previous_msg_time = None

    while attempts < max_attempts:
        messages = driver.find_elements(By.CSS_SELECTOR, "div.message-in")
        if not messages:
            print("⚠️ No messages found.")
            break

        last_msg = messages[-1]  # bottom-most message on screen

        # Try to extract time of the message
        try:
            time_span = last_msg.find_element(By.CSS_SELECTOR, "span.x1rg5ohu")
            time_text = time_span.text.strip()
            msg_time = datetime.strptime(time_text, "%I:%M %p").time()
            
            # Detect midnight rollover
            if previous_msg_time and msg_time < previous_msg_time:
                message_date += timedelta(days=1)
                print(f"🔁 Detected day rollover, updated date: {message_date}")
            previous_msg_time = msg_time

            msg_datetime = datetime.combine(message_date, msg_time)
            print(f"⏱️ Last visible message time: {msg_datetime}")

            if msg_datetime > end_time:
                print("✅ Reached message just after end_time.")
                break
            else:
                print("⏬ Not yet past end_time, keep scrolling down...")
        except Exception as e:
            print(f"⚠️ Error reading time from message: {e}")

        # Scroll to the message to load more below
        try:
            ActionChains(driver).move_to_element(last_msg).perform()
            driver.execute_script("arguments[0].scrollIntoView(false);", last_msg)
        except Exception as e:
            print(f"⚠️ Scroll error: {e}")

        time.sleep(1.5)

        # Prevent infinite loop
        current_msg_text = last_msg.text.strip()
        if current_msg_text == last_msg_text:
            attempts += 1
        else:
            attempts = 0
        last_msg_text = current_msg_text



def is_message_in_time_range(msg_element, start_time, end_time, message_date):
    """
    Check if the message timestamp (from 'x1rg5ohu' span) is within the given datetime range.
    
    Parameters:
        msg_element (WebElement): The message DOM element.
        start_time (datetime): Start datetime (inclusive).
        end_time (datetime): End datetime (inclusive).
        message_date (datetime.date): The actual date of the message (passed in manually).

    Returns:
        bool: True if in range, False otherwise.
    """
    try:
        # Extract time from span with class x1rg5ohu
        time_span = msg_element.find_element(By.CSS_SELECTOR, "span.x1rg5ohu")
        time_text = time_span.text.strip()
        time_text = time_text.replace("Edited","")
        print("🕒 Extracted time text:", time_text)

        # Combine the manually provided date with the extracted time
        msg_time_only = datetime.strptime(time_text, "%I:%M %p").time()
        msg_datetime = datetime.combine(message_date, msg_time_only)

        print("📆 Full message datetime:", msg_datetime)

        return start_time <= msg_datetime <= end_time, msg_datetime
    except Exception as e:
        print(f"⚠️ Error checking message time: {e}")
        return False, None

def extract_sender_name(msg_element):
    global last_sender
    try:
        sender_span = msg_element.find_element(By.CSS_SELECTOR, "span.x1ypdohk")
        sender = sender_span.text.strip()
        if sender:
            last_sender = sender  # update tracker
            print("👤 Sender:", sender)
            return sender
    except Exception as e:
        pass  # Not a real error — likely just missing due to consecutive messages

    return "Unknown"


def extract_text(msg_element):
    try:
        text_els = msg_element.find_elements(By.CSS_SELECTOR, "span.selectable-text.copyable-text")
        return " ".join([el.text for el in text_els if el.text.strip()]) if text_els else ""
    except Exception as e:
        print("extract_text Exception:", e)
        return ""

def extract_image(msg_element, index):
    try:
        # Find the image element
        img_el = msg_element.find_element(By.CSS_SELECTOR, "img[src^='blob:']")
        
        # Scroll into view (optional but helps ensure it's rendered)
        msg_element.location_once_scrolled_into_view

        # Screenshot the element
        path = f"downloads/image_{index}.png"
        img_el.screenshot(path)
        return path
    except Exception as e:
        return None

def send_to_openai(image_path, text, sender):
    image_input = []
    if image_path:
        with open(image_path, "rb") as img_file:
            base64_img = base64.b64encode(img_file.read()).decode()
            image_input.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })

    prompt = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"""Extract the following fields from this message and/or image:
- Doctor Name
- Place of work (e.g. Hospital)
- Phone number (if present)
- Comments (any extra info)
- The sender is the employee who submitted the entry.
- "**Important Instructions:**\n"
            "- Do NOT treat Asia Specific, AIOS, APAO, APAC, or similar as the place name — they are event names.\n"
            "- Do NOT add these as comments - Delegate at the APAO event, April 03-06, 2025, Yashobhoomi, New Delhi (India).\n"
            "- Extract actual organizations (e.g. hospitals, trusts, companies) as place names.\n"
            "- If information is missing, use empty strings."

Message Text: "{text}"
Sender: {sender}

- If anyone of the following fields are empty, return those fields as "<To be checked>"

Respond in JSON format:
{{
  "name": "",
  "place": "",
  "phone": "",
  "employee": "",
  "comments": ""
}}"""
            }
        ] + image_input
    }

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You extract structured data from ID card images and WhatsApp message text."},
                prompt
            ],
            max_tokens=500,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(json)?\n", "", content)
            content = content.rstrip("```")

        # Parse as JSON safely
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print("⚠️ JSON Decode Error:", e)
            return {}
    except Exception as e:
        print(f"⚠️ OpenAI error: {e}")
        return {}

# Start processing
print("🔍 Reading messages...")
scroll_up_until_start_time(driver, start, end, message_date)
messages = driver.find_elements(By.CSS_SELECTOR, "div.message-in")
row_index = 1

for i, msg in enumerate(messages):
    try:
        is_message_in_time_range_bool, msg_datetime = is_message_in_time_range(msg, start, end, message_date)
        if not is_message_in_time_range_bool:
            continue
        sender = extract_sender_name(msg)
        text = extract_text(msg)
        image_path = extract_image(msg, i)

        print(f"\n📩 Message {i+1} from {sender}")
        print(f"📜 Text: {text}")
        if image_path:
            print(f"🖼️ Image: {image_path}")

        extracted = send_to_openai(image_path, text, sender)
        if extracted:
            sheet.append_row([
                extracted.get("name", "<To be checked>"),
                extracted.get("phone", "<To be checked>"),
                extracted.get("employee", ""),
                extracted.get("comments", "<To be checked>"),
                msg_datetime.strftime("%Y-%m-%d %H:%M:%S") if msg_datetime else "<To be checked>"
            ])
            print(f"✅ Added to Sheet: {extracted}")
            row_index += 1
        else:
            print("⚠️ No data extracted.")
    except Exception as e:
        print(f"❌ Error on message {i+1}: {e}")
print("✅ All done. Closing browser.")
driver.quit()
