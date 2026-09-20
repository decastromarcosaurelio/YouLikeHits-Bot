"""Shared helpers: browser factory, waits, login/points detection.

`setup_browser` is the ONLY browser factory in the project.
"""
import os
import re
import random
import subprocess
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

YLH_BASE = "https://www.youlikehits.com"

# Selectors verified against the live site on 2026-09-20.
LOGOUT_LINK = "#logoutlink"            # present only when logged in
LOGGED_OUT_MARKER = "#ylhloggedout"    # injected into AJAX replies when the session died
POINTS_SPAN = "#currentpoints"         # live points balance (updated by the site's JS)

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILE_DIR = os.path.join(PROJECT_DIR, "chrome_profile")


# ── Chrome version detection ──────────────────────────────────────────

def parse_chrome_major(version_output):
    """Extract the major version from `chrome --version` output.

    >>> parse_chrome_major("Google Chrome 153.0.8010.52 ")
    153
    >>> parse_chrome_major("Chromium 128.0.6613.84 snap")
    128
    >>> parse_chrome_major("garbage") is None
    True
    """
    if not version_output:
        return None
    match = re.search(r"(\d+)\.\d+\.\d+", version_output)
    return int(match.group(1)) if match else None


def detect_chrome_major(executable_path=None):
    """Return the installed Chrome major version, or None if it can't be read.

    undetected-chromedriver must download a chromedriver whose major matches
    the browser. Pinning a number in code breaks every time Chrome updates;
    asking the binary is always right.
    """
    try:
        binary = executable_path or uc.find_chrome_executable()
        if not binary:
            return None
        out = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=10
        ).stdout
        return parse_chrome_major(out)
    except Exception:
        return None


def setup_browser(profile_dir=None):
    """Initialize a persistent Chrome browser instance.

    Returns the driver, or None on failure (error is printed).
    """
    if profile_dir is None:
        profile_dir = DEFAULT_PROFILE_DIR
    print(f"[*] Initializing browser with profile: {profile_dir}...")

    major = detect_chrome_major()
    if major:
        print(f"[*] Detected Chrome major version: {major}")
    else:
        print("[!] Could not detect Chrome version; letting chromedriver auto-detect.")

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--disable-popup-blocking")
    try:
        return uc.Chrome(options=options, version_main=major)
    except Exception as e:
        print(f"[!] Error initializing Chrome: {e}")
        return None


# ── Waiting ───────────────────────────────────────────────────────────

def wait_unless_stopped(seconds, is_stopped=None, step=1.0):
    """Sleep up to `seconds`, waking early if `is_stopped()` becomes true.

    Returns True if the full duration elapsed, False if interrupted.
    """
    if is_stopped is None:
        time.sleep(seconds)
        return True
    deadline = time.monotonic() + seconds
    while True:
        if is_stopped():
            return False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        time.sleep(min(step, remaining))


def wait_until(predicate, timeout, is_stopped=None, step=1.0):
    """Poll `predicate()` until it is truthy, the timeout passes, or we are stopped.

    Returns the truthy value, or None on timeout/stop.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            value = predicate()
        except Exception:
            value = None
        if value:
            return value
        if is_stopped and is_stopped():
            return None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(step, remaining))


def close_extra_windows(driver, keep):
    """Close every window except `keep` and switch back to it."""
    try:
        for handle in list(driver.window_handles):
            if handle != keep:
                driver.switch_to.window(handle)
                driver.close()
        driver.switch_to.window(keep)
    except Exception:
        try:
            driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass


def seconds_from_text(text, default):
    """Pull the first integer out of 'wait 20 seconds' / 'Watching 0 / 124 s'; else default."""
    if not text:
        return default
    nums = re.findall(r"/\s*(\d+)\s*s|(\d+)\s*seconds?", text)
    for a, b in nums:
        return int(a or b)
    return default


def random_delay(min_sec=2, max_sec=5, is_stopped=None):
    """Wait a random duration between actions (interruptible)."""
    delay = random.uniform(min_sec, max_sec)
    wait_unless_stopped(delay, is_stopped)
    return delay


def wait_for_element(driver, by, value, timeout=10):
    """Wait for an element and return it, or None on timeout."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        return None


def wait_for_clickable(driver, by, value, timeout=10):
    """Wait for an element to be clickable and return it, or None on timeout."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    except TimeoutException:
        return None


# ── Page helpers ──────────────────────────────────────────────────────

def body_text(driver):
    """Lowercased page body text, or '' if unavailable."""
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return ""


def is_browser_alive(driver):
    """True while the browser session answers; False once it's been closed."""
    if driver is None:
        return False
    try:
        _ = driver.window_handles
        return True
    except Exception:
        return False


def is_logged_in(driver):
    """True when the page shows the Logout link (only rendered for a live session)."""
    try:
        if driver.find_elements(By.CSS_SELECTOR, LOGGED_OUT_MARKER):
            return False
        return bool(driver.find_elements(By.CSS_SELECTOR, LOGOUT_LINK))
    except Exception:
        return False


def get_points(driver):
    """Read the live points balance from the header. Returns int or None."""
    try:
        text = driver.find_element(By.CSS_SELECTOR, POINTS_SPAN).text
        digits = re.sub(r"[^0-9]", "", text)
        return int(digits) if digits else None
    except NoSuchElementException:
        pass
    except Exception:
        return None
    try:
        match = re.search(r"(\d[\d,]*)\s*[Pp]oints?", driver.find_element(By.TAG_NAME, "body").text)
        if match:
            return int(match.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def navigate_to(driver, path, settle=2):
    """Navigate to a YLH page and give it a moment to settle."""
    driver.get(f"{YLH_BASE}/{path}")
    time.sleep(settle)


def check_service_unavailable(driver):
    """Detect a 503 page and reload. Returns True if a reload happened."""
    text = body_text(driver)
    if "503" in text or "service unavailable" in text:
        print("[!] 503 Service Unavailable. Reloading...")
        time.sleep(5)
        driver.refresh()
        time.sleep(3)
        return True
    return False


def run_cli_task(title, setup_browser_func, task_func):
    """Open a browser and run a GUI-style task in the terminal until Ctrl+C.

    `task_func(driver, is_stopped, log_func, update_points_func)` is the
    same function the GUI calls, so CLI and GUI never diverge.
    """
    print(f"\n[*] Starting {title}...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    def log(msg):
        print(f"[*] {msg}")

    def update_points(points):
        if points is not None:
            print(f"[*] Points: {points}")

    try:
        task_func(driver, lambda: False, log, update_points)
    except KeyboardInterrupt:
        print(f"\n[*] {title} stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def wait_for_manual_captcha(driver, log, is_stopped=None, selector="img[src*='captcha']", seconds=30):
    """If a captcha image is on the page, pause so the user can solve it.

    YLH captchas are not solved automatically. Returns True if a captcha was
    present (caller should re-check the page afterwards).
    """
    try:
        driver.find_element(By.CSS_SELECTOR, selector)
    except NoSuchElementException:
        return False
    except Exception:
        return False
    log(f"Captcha detected. Please solve it in the browser window ({seconds}s pause)...")
    wait_unless_stopped(seconds, is_stopped)
    return True
