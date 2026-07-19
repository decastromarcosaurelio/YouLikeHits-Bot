import time
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from .utils import (
    wait_for_element, wait_for_clickable, is_logged_in,
    navigate_to, check_service_unavailable, random_delay, get_points
)


def _run_youtube_task(driver, is_stopped, log_func, update_points_func):
    """YouTube views task for GUI integration."""
    log_func("Starting YouTube views...")
    navigate_to(driver, "youtubenew2.php")
    time.sleep(2)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        if check_service_unavailable(driver):
            navigate_to(driver, "youtubenew2.php")

        # Check for captcha
        try:
            captcha = driver.find_element(By.CSS_SELECTOR, "img[src*='captchayt']")
            if captcha:
                log_func("YouTube captcha detected. Please solve manually.")
                time.sleep(30)
                continue
        except NoSuchElementException:
            pass

        points = get_points(driver)
        update_points_func(points)

        buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, a[onclick*='view'], button[onclick*='view']")
        
        if not buttons:
            log_func("No YouTube videos available. Refreshing...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)
            continue

        log_func(f"Found {len(buttons)} YouTube videos to view.")
        
        for i, button in enumerate(buttons):
            if is_stopped():
                break
            try:
                if not button.is_displayed():
                    continue
                
                log_func(f"Watching video {i+1}/{len(buttons)}...")
                button.click()
                time.sleep(2)
                
                log_func("Waiting for video timer (up to 2 minutes)...")
                time.sleep(random.uniform(90, 135))
                
                try:
                    submit_btn = driver.find_element(By.CSS_SELECTOR, "input[value='Submit']")
                    submit_btn.click()
                    time.sleep(2)
                except NoSuchElementException:
                    pass
                
                log_func("Video viewed successfully.")
                random_delay(3, 6)
                
            except WebDriverException as e:
                log_func(f"Error viewing video: {e}")
                continue

        log_func("All videos processed. Refreshing for more...")
        time.sleep(5)
        driver.refresh()
        time.sleep(3)

    log_func("YouTube views loop stopped.")


def start_youtube_loop(setup_browser_func):
    """Main loop for YouTube views automation (CLI mode)."""
    print("\n[*] Starting YouTube Views loop...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    try:
        navigate_to(driver, "youtubenew2.php")
        time.sleep(2)

        if not is_logged_in(driver):
            print("[!] Not logged in! Please use 'Setting Up' first.")
            return

        while True:
            if check_service_unavailable(driver):
                navigate_to(driver, "youtubenew2.php")

            try:
                captcha = driver.find_element(By.CSS_SELECTOR, "img[src*='captchayt']")
                if captcha:
                    print("[!] YouTube captcha detected. Please solve manually in the browser.")
                    print("[!] Waiting 30 seconds...")
                    time.sleep(30)
                    continue
            except NoSuchElementException:
                pass

            buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, a[onclick*='view'], button[onclick*='view']")
            
            if not buttons:
                print("[*] No YouTube videos available. Refreshing...")
                time.sleep(5)
                driver.refresh()
                time.sleep(3)
                continue

            print(f"[*] Found {len(buttons)} YouTube videos to view.")
            
            for i, button in enumerate(buttons):
                try:
                    if not button.is_displayed():
                        continue
                    
                    print(f"[*] Watching video {i+1}/{len(buttons)}...")
                    button.click()
                    time.sleep(2)
                    
                    print("[*] Waiting for video timer (up to 2 minutes)...")
                    time.sleep(random.uniform(90, 135))
                    
                    try:
                        submit_btn = driver.find_element(By.CSS_SELECTOR, "input[value='Submit'], button:contains('Submit')")
                        submit_btn.click()
                        time.sleep(2)
                    except NoSuchElementException:
                        pass
                    
                    print("[*] Video viewed successfully.")
                    random_delay(3, 6)
                    
                except WebDriverException as e:
                    print(f"[!] Error viewing video: {e}")
                    continue

            print("[*] All videos processed. Refreshing for more...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n[*] YouTube Views loop stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
