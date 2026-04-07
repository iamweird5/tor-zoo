import os
import requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# ---------------- CONFIG ----------------
LOGIN_URL = "https://quipugroup.net"
MAIN_URL = "https://quipugroup.net"

# Environment Variables
USERNAME = os.environ.get("LIBRARY_USER")
PASSWORD = os.environ.get("LIBRARY_PASS")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

last_status = None

# ---------------- TELEGRAM ----------------
def send_telegram(msg):
    url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
        print("📲 Telegram alert sent!")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# ---------------- DRIVER ----------------
def get_driver():
    options = Options()
    # Essential for Render/Docker environments
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Critical flags for remote debugging and bot detection bypass
    options.add_argument("--remote-debugging-port=9222") 
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Path to the Chrome binary installed by your Dockerfile
    options.binary_location = "/usr/bin/google-chrome"
    
    return webdriver.Chrome(options=options)

# ---------------- CHECK FUNCTION ----------------
def check():
    global last_status
    driver = get_driver()
    status = "UNKNOWN"

    try:
        # 1. LOGIN
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 20)
        
        user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_field.send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)

        login_btn = driver.find_element(By.XPATH, "//button[contains(., 'Login')]")
        driver.execute_script("arguments[0].click();", login_btn)

        # Wait for the dashboard to confirm login
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
        print("✅ LOGIN SUCCESS")

        # 2. NAVIGATE TO MAIN PAGE
        driver.get(MAIN_URL)
        
        # 3. FIND TORONTO ZOO CARD
        # This targets the card specifically containing the 'Toronto Zoo' text
        zoo_card_xpath = "//div[contains(@class,'card')][descendant::*[contains(text(), 'Toronto Zoo')]]"
        zoo_card = wait.until(EC.presence_of_element_located((By.XPATH, zoo_card_xpath)))

        # 4. DETECT AVAILABILITY
        # Logic: If 'Show' or 'Reserve' button is present within the Zoo card, it is available.
        try:
            # We look for the button element specifically inside the zoo_card
            zoo_card.find_element(By.XPATH, ".//button[contains(., 'Show') or contains(., 'Reserve')]")
            status = "AVAILABLE"
        except:
            # Fallback to text check if button is missing
            card_text = zoo_card.text.lower()
            if "no passes available" in card_text or "reserved" in card_text:
                status = "NOT AVAILABLE"
            else:
                status = "UNKNOWN"

        print(f"📊 Toronto Zoo Status: {status}")

        # 5. NOTIFY ON CHANGE
        if status != last_status:
            last_status = status
            if status == "AVAILABLE":
                send_telegram("🚨 TORONTO ZOO PASS AVAILABLE! Book it now!")
            elif status == "NOT AVAILABLE":
                print("Status changed to Not Available.")

        return status

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"ERROR: {str(e)}"
    finally:
        driver.quit()

# ---------------- WEB ROUTES ----------------
@app.route("/")
def home():
    return "Toronto Zoo Monitor is running. Ping /check to scan."

@app.route("/check")
def run_check():
    res = check()
    return f"Check complete. Status: {res}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
