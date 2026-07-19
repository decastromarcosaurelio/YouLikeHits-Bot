import time
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from .utils import (
    wait_for_element, wait_for_clickable, is_logged_in,
    navigate_to, check_service_unavailable, random_delay, get_points
)


def _run_soundcloud_task(driver, is_stopped, log_func, update_points_func):
    """SoundCloud plays task for GUI integration."""
    log_func("Starting SoundCloud plays...")
    navigate_to(driver, "soundcloudplays.php")
    time.sleep(2)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        if check_service_unavailable(driver):
            navigate_to(driver, "soundcloudplays.php")

        points = get_points(driver)
        update_points_func(points)

        buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, a[onclick*='view'], button[onclick*='view']")
        
        if not buttons:
            log_func("No SoundCloud tracks available. Refreshing...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)
            continue

        log_func(f"Found {len(buttons)} SoundCloud tracks to play.")
        
        for i, button in enumerate(buttons):
            if is_stopped():
                break
            try:
                if not button.is_displayed():
                    continue
                
                log_func(f"Playing track {i+1}/{len(buttons)}...")
                button.click()
                time.sleep(2)
                
                log_func("Waiting for track to play...")
                time.sleep(random.uniform(30, 60))
                
                log_func("Track played successfully.")
                random_delay(2, 5)
                
            except WebDriverException as e:
                log_func(f"Error playing track: {e}")
                continue

        log_func("All tracks processed. Refreshing for more...")
        time.sleep(5)
        driver.refresh()
        time.sleep(3)

    log_func("SoundCloud plays loop stopped.")


def start_soundcloud_loop(setup_browser_func):
    """Main loop for SoundCloud plays automation (CLI mode)."""
    print("\n[*] Starting SoundCloud Plays loop...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    try:
        navigate_to(driver, "soundcloudplays.php")
        time.sleep(2)

        if not is_logged_in(driver):
            print("[!] Not logged in! Please use 'Setting Up' first.")
            return

        while True:
            if check_service_unavailable(driver):
                navigate_to(driver, "soundcloudplays.php")

            buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, a[onclick*='view'], button[onclick*='view']")
            
            if not buttons:
                print("[*] No SoundCloud tracks available. Refreshing...")
                time.sleep(5)
                driver.refresh()
                time.sleep(3)
                continue

            print(f"[*] Found {len(buttons)} SoundCloud tracks to play.")
            
            for i, button in enumerate(buttons):
                try:
                    if not button.is_displayed():
                        continue
                    
                    print(f"[*] Playing track {i+1}/{len(buttons)}...")
                    button.click()
                    time.sleep(2)
                    
                    print("[*] Waiting for track to play...")
                    time.sleep(random.uniform(30, 60))
                    
                    print("[*] Track played successfully.")
                    random_delay(2, 5)
                    
                except WebDriverException as e:
                    print(f"[!] Error playing track: {e}")
                    continue

            print("[*] All tracks processed. Refreshing for more...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n[*] SoundCloud Plays loop stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
