import time
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from .utils import (
    wait_for_element, wait_for_clickable, is_logged_in,
    navigate_to, check_service_unavailable, random_delay, get_points
)


def _run_bonus_task(driver, is_stopped, log_func, update_points_func):
    """Daily bonus task for GUI integration."""
    log_func("Starting daily bonus claimer...")
    navigate_to(driver, "bonuspoints.php")
    time.sleep(2)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        if check_service_unavailable(driver):
            navigate_to(driver, "bonuspoints.php")

        points = get_points(driver)
        update_points_func(points)

        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            if "you have made" in body.lower() and "hits out of" in body.lower():
                log_func("Daily bonus already claimed or not enough hits yet.")
                log_func("Waiting 5 minutes before checking again...")
                time.sleep(300)
                driver.refresh()
                time.sleep(3)
                continue
        except Exception:
            pass

        try:
            claim_btn = driver.find_element(By.CSS_SELECTOR, ".buybutton, button[onclick*='buy'], a[onclick*='buy']")
            if claim_btn and claim_btn.is_displayed():
                log_func("Claim button found! Clicking...")
                claim_btn.click()
                time.sleep(3)
                log_func("Daily bonus claimed!")
                random_delay(2, 5)
                continue
        except NoSuchElementException:
            pass

        log_func("No claim button available. Waiting 2 minutes...")
        time.sleep(120)
        driver.refresh()
        time.sleep(3)

    log_func("Daily bonus claimer stopped.")


def start_bonus_loop(setup_browser_func):
    """Main loop for daily bonus points claiming (CLI mode)."""
    print("\n[*] Starting Daily Bonus Claimer...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    try:
        navigate_to(driver, "bonuspoints.php")
        time.sleep(2)

        if not is_logged_in(driver):
            print("[!] Not logged in! Please use 'Setting Up' first.")
            return

        while True:
            if check_service_unavailable(driver):
                navigate_to(driver, "bonuspoints.php")

            try:
                body = driver.find_element(By.TAG_NAME, "body").text
                if "you have made" in body.lower() and "hits out of" in body.lower():
                    print("[*] Daily bonus already claimed or not enough hits yet.")
                    print("[*] Waiting 5 minutes before checking again...")
                    time.sleep(300)
                    driver.refresh()
                    time.sleep(3)
                    continue
            except Exception:
                pass

            try:
                claim_btn = driver.find_element(By.CSS_SELECTOR, ".buybutton, button[onclick*='buy'], a[onclick*='buy']")
                if claim_btn and claim_btn.is_displayed():
                    print("[*] Claim button found! Clicking...")
                    claim_btn.click()
                    time.sleep(3)
                    print("[*] Daily bonus claimed!")
                    random_delay(2, 5)
                    continue
            except NoSuchElementException:
                pass

            print("[*] No claim button available. Waiting 2 minutes...")
            time.sleep(120)
            driver.refresh()
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n[*] Daily Bonus Claimer stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
