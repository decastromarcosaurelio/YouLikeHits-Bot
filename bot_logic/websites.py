import time
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from .utils import (
    wait_for_element, wait_for_clickable, is_logged_in,
    navigate_to, check_service_unavailable, random_delay, get_points
)

YLH_BASE = "https://www.youlikehits.com"


def _run_website_task(driver, is_stopped, log_func, update_points_func):
    """Website views task for GUI integration."""
    log_func("Starting website views...")
    navigate_to(driver, "websites.php")
    time.sleep(2)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    while not is_stopped():
        if check_service_unavailable(driver):
            navigate_to(driver, "websites.php")

        try:
            body = driver.find_element(By.TAG_NAME, "body").text
            if "no websites currently" in body.lower() or "no websites visitable" in body.lower():
                log_func("No websites available. Waiting 2 minutes...")
                time.sleep(120)
                navigate_to(driver, "websites.php")
                continue
        except Exception:
            pass

        points = get_points(driver)
        update_points_func(points)

        buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, .viewbutton, a[onclick*='view'], button[onclick*='view']")
        
        if not buttons:
            log_func("No view buttons found. Refreshing...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)
            continue

        log_func(f"Found {len(buttons)} websites to view.")
        
        for i, button in enumerate(buttons):
            if is_stopped():
                break
            try:
                if not button.is_displayed():
                    continue
                
                log_func(f"Viewing website {i+1}/{len(buttons)}...")
                original_window = driver.current_window_handle
                button.click()
                time.sleep(1)
                
                windows = driver.window_handles
                if len(windows) > 1:
                    new_window = [w for w in windows if w != original_window][0]
                    driver.switch_to.window(new_window)
                    log_func("Waiting for website timer...")
                    time.sleep(random.uniform(12, 35))
                    driver.close()
                    driver.switch_to.window(original_window)
                    log_func("Website viewed successfully.")
                
                random_delay(2, 5)
                
            except WebDriverException as e:
                log_func(f"Error viewing website: {e}")
                try:
                    if len(driver.window_handles) > 1:
                        driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
                continue

        log_func("All websites viewed. Refreshing for more...")
        time.sleep(5)
        driver.refresh()
        time.sleep(3)

    log_func("Website views loop stopped.")


def start_website_loop(setup_browser_func):
    """Main loop for website views automation (CLI mode)."""
    print("\n[*] Starting Website Views loop...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    try:
        navigate_to(driver, "websites.php")
        time.sleep(2)

        if not is_logged_in(driver):
            print("[!] Not logged in! Please use 'Setting Up' first.")
            return

        while True:
            if check_service_unavailable(driver):
                navigate_to(driver, "websites.php")

            try:
                body = driver.find_element(By.TAG_NAME, "body").text
                if "no websites currently" in body.lower() or "no websites visitable" in body.lower():
                    print("[*] No websites available. Waiting 2 minutes...")
                    time.sleep(120)
                    navigate_to(driver, "websites.php")
                    continue
            except Exception:
                pass

            buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, .viewbutton, a[onclick*='view'], button[onclick*='view']")
            
            if not buttons:
                print("[*] No view buttons found. Refreshing...")
                time.sleep(5)
                driver.refresh()
                time.sleep(3)
                continue

            print(f"[*] Found {len(buttons)} websites to view.")
            
            for i, button in enumerate(buttons):
                try:
                    if not button.is_displayed():
                        continue
                    
                    print(f"[*] Viewing website {i+1}/{len(buttons)}...")
                    original_window = driver.current_window_handle
                    button.click()
                    time.sleep(1)
                    
                    windows = driver.window_handles
                    if len(windows) > 1:
                        new_window = [w for w in windows if w != original_window][0]
                        driver.switch_to.window(new_window)
                        print("[*] Waiting for website timer...")
                        time.sleep(random.uniform(12, 35))
                        driver.close()
                        driver.switch_to.window(original_window)
                        print("[*] Website viewed successfully.")
                    
                    random_delay(2, 5)
                    
                except WebDriverException as e:
                    print(f"[!] Error viewing website: {e}")
                    try:
                        if len(driver.window_handles) > 1:
                            driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                    except Exception:
                        pass
                    continue

            print("[*] All websites viewed. Refreshing for more...")
            time.sleep(5)
            driver.refresh()
            time.sleep(3)

    except KeyboardInterrupt:
        print("\n[*] Website Views loop stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
