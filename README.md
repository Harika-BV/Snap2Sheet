# Snap2Sheet

Automate data entry from WhatsApp into structured Google Sheets using Python, Selenium, and GPT Vision. Built to save weekends, sanity, and your Ctrl+C fingers.

## 📦 What It Does

During a large ophthalmology conference, our team was collecting leads via a WhatsApp group — including:
- Text messages  
- Photos of badges
- Names, phone numbers, places, and comments  

Instead of manually entering hundreds of entries, this script:
1. Opens WhatsApp Web using Selenium  
2. Scrolls through messages within a given time range  
3. Extracts structured data (including from images!) using OpenAI Vision  
4. Logs everything to a Google Sheet  

## 🔧 Tech Stack

- **Python**  
- **Selenium** – Web automation  
- **OpenAI Vision + GPT-4** – For parsing message content  
- **Google Sheets API** – For storing results  

## 📂 Output

Each row in Google Sheets includes:
- `Name`  
- `Phone`  
- `Place`  
- `Employee` (sender)  
- `Comments`  
- `Datetime`  

## 🚀 Getting Started

### Prerequisites

- Python 3.10+  
- Chrome + ChromeDriver  
- OpenAI API Key  
- Google Sheets API credentials (OAuth2)  

### Installation

```bash
git clone https://github.com/yourusername/whatsapp-lead-extractor.git
cd whatsapp-lead-extractor
pip install -r requirements.txt
```

### 🛠️ Configuration

1. **Set up environment variables** (via `.env` or config dictionary):
   - `OPENAI_API_KEY` – Your OpenAI GPT-4 Vision API key
   
2. **Set up Google Sheets API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the **Google Sheets API**.
   - Create credentials for a **desktop app**.
   - Download `credentials.json` and place it in the project folder.
   - The script will open a browser on first run to authorize access.

3. **WhatsApp Web Login**:
   - The script opens a Chrome window using Selenium.
   - To preserve your session, use a persistent user data directory:
     ```bash
     --user-data-dir=./chrome-data
     ```
   - This avoids having to scan the QR code each time.

---

### ▶️ Running the Script

```bash
python main.py
```

### ✅ Output Format

Each row in the Google Sheet will contain:

- **Name** – Person’s name (parsed from message)
- **Phone** – Mobile number if mentioned
- **Place** – City or location if available
- **Employee** – The name of the sender (from WhatsApp)
- **Comments** – Additional notes from the message
- **Timestamp** – Date and time when the message was sent

---

### 🧪 Example Output

| Name         | Phone       | Place     | Employee | Comments               | Timestamp           |
|--------------|-------------|-----------|----------|------------------------|---------------------|
| Dr. Anjali R | 9876543210  | Pune      | Sneha    | Interested in demo     | 2025-04-04 10:14:02 |
| Mr. Sharma   | 9123456789  | Hyderabad | Arjun    | Asked to follow up Wed | 2025-04-04 11:40:18 |

---

### 🛑 Known Limitations

- Needs stable internet and Chrome session
- Vision API may occasionally misread handwriting or messy formats
- Date tracking works best if message timestamps are consistent
- Some messages may require manual correction

---

### ✨ Pro Tips

- Add `--user-data-dir=./chrome-profile` to persist WhatsApp session between runs
- If scrolling doesn't behave correctly, check for stale DOM or re-assign element references inside loops
- Use `print()` logs with emojis for visual debugging 🧠🧾
- Customize the OpenAI prompt to suit your message format better
