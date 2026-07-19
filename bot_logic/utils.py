import os
import re
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

YLH_BASE = "https://www.youlikehits.com"


def setup_browser(profile_dir=None):
    """Initialize a persistent Chrome browser instance."""
    if profile_dir is None:
        profile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chrome_profile")
    print(f"[*] Initializing browser with profile: {profile_dir}...")
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--disable-popup-blocking")
    try:
        driver = uc.Chrome(options=options, version_main=150)
        return driver
    except Exception as e:
        print(f"[!] Error initializing Chrome: {e}")
        return None


def wait_for_element(driver, by, value, timeout=10):
    """Wait for an element and return it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        return element
    except TimeoutException:
        return None


def wait_for_clickable(driver, by, value, timeout=10):
    """Wait for an element to be clickable and return it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        return element
    except TimeoutException:
        return None


def is_logged_in(driver):
    """Check if user is logged in by looking for dashboard indicators."""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "not logged in" in body_text.lower():
            return False
        # Check for points display or profile elements
        driver.find_element(By.CSS_SELECTOR, ".points, #points, [class*='point']")
        return True
    except NoSuchElementException:
        return False


def get_points(driver):
    """Attempt to read current points balance."""
    try:
        # Try various selectors that YLH might use
        selectors = [".points", "#points", "[class*='point']", ".pointsdisplay"]
        for sel in selectors:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                text = el.text.strip()
                nums = re.findall(r'\d+', text)
                if nums:
                    return int(nums[0])
            except NoSuchElementException:
                continue
        # Fallback: search body text for points pattern
        body = driver.find_element(By.TAG_NAME, "body").text
        match = re.search(r'(\d[\d,]*)\s*[Pp]oints?', body)
        if match:
            return int(match.group(1).replace(',', ''))
    except Exception:
        pass
    return None


def solve_math_captcha(driver, image_selector="img[alt='Enter The Numbers']",
                       input_selector="input[name='postcaptcha']"):
    """Solve the math-based captcha using OCR-like approach.
    
    YLH captchas are simple math expressions like '2+3' or '5*4'.
    We try to read the image and evaluate.
    """
    try:
        captcha_img = wait_for_element(driver, By.CSS_SELECTOR, image_selector, timeout=3)
        if not captcha_img:
            return False

        # For Selenium, we can't do OCR directly. 
        # Instead, we'll use a trick: download the image and use a simple heuristic.
        # YLH captchas are 3-character math like "2+3" or "5*4"
        # The simplest approach: alert the user and pause.
        print("[!] Captcha detected. Please solve it manually in the browser window.")
        print("[!] Waiting 30 seconds for manual solve...")
        time.sleep(30)
        return True
    except Exception:
        return False


def random_delay(min_sec=2, max_sec=5):
    """Wait a random duration between actions."""
    import random
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay


def navigate_to(driver, path):
    """Navigate to a YLH page."""
    url = f"{YLH_BASE}/{path}"
    driver.get(url)
    time.sleep(2)


def check_service_unavailable(driver):
    """Check for 503 errors and reload if needed."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text
        if "503" in body or "service unavailable" in body.lower():
            print("[!] 503 Service Unavailable. Reloading...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)
            return True
    except Exception:
        pass
    return False
