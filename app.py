import os
import requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)

# --- CONFIG ---
LOGIN_URL = "https://quipugroup.net"
MAIN_URL = "https://quipugroup.net"
USERNAME = os.environ.get("LIBRARY_USER")
PASSWORD = os.environ.get("LIBRARY_PASS")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

last_status = None

def send_telegram(msg):
    url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Point to the Chrome binary installed by Docker
    options.binary_location = "/usr/bin/google-chrome"
    return webdriver.Chrome(options=options)

def check():
    global last_status
    driver = get_driver()
    status = "UNKNOWN"
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 20)
        
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USERNAME)
        driver.find_element(By.NAME, "password").send_keys(PASSWORD)
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//button[contains(., 'Login')]"))

        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
        driver.get(MAIN_URL)
        
        # Target Toronto Zoo Card
        zoo_card_xpath = "//div[contains(@class,'card')][descendant::*[contains(text(), 'Toronto Zoo')]]"
        zoo_card = wait.until(EC.presence_of_element_located((By.XPATH, zoo_card_xpath)))

        try:
            # Look for ANY button that indicates booking is possible
            zoo_card.find_element(By.XPATH, ".//button[contains(., 'Show') or contains(., 'Reserve')]")
            status = "AVAILABLE"
        except:
            status = "NOT AVAILABLE"

        if status != last_status:
            last_status = status
            if status == "AVAILABLE":
                send_telegram("🚨 TORONTO ZOO PASS AVAILABLE! Book now!")
        
        return status
    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        driver.quit()

@app.route("/")
def home(): return "Bot Running"

@app.route("/check")
def run_check(): return f"Result: {check()}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
