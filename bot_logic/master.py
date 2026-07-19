import time
import random
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from .utils import (
    wait_for_element, wait_for_clickable, is_logged_in,
    navigate_to, check_service_unavailable, random_delay, get_points
)

YLH_BASE = "https://www.youlikehits.com"


def _run_master_task(driver, is_stopped, log_func, update_points_func):
    """Master loop task for GUI integration."""
    log_func("Starting master loop...")
    driver.get(YLH_BASE)
    time.sleep(2)

    if not is_logged_in(driver):
        log_func("Not logged in! Please log in first.")
        return

    cycle = 0
    while not is_stopped():
        cycle += 1
        log_func(f"=== Master Loop Cycle {cycle} ===")

        # 1. Daily bonus
        log_func("Checking daily bonus...")
        try:
            navigate_to(driver, "bonuspoints.php")
            time.sleep(2)
            body = driver.find_element(By.TAG_NAME, "body").text
            if "you have made" not in body.lower():
                try:
                    claim_btn = driver.find_element(By.CSS_SELECTOR, ".buybutton, button[onclick*='buy']")
                    if claim_btn.is_displayed():
                        log_func("Claiming daily bonus...")
                        claim_btn.click()
                        time.sleep(3)
                except NoSuchElementException:
                    pass
        except Exception as e:
            log_func(f"Bonus check error: {e}")

        # 2. Website views
        log_func("Processing website views...")
        try:
            navigate_to(driver, "websites.php")
            time.sleep(2)
            body = driver.find_element(By.TAG_NAME, "body").text
            if "no websites currently" not in body.lower():
                buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, .viewbutton")
                if buttons:
                    log_func(f"Found {len(buttons)} websites to view.")
                    for button in buttons[:3]:
                        if is_stopped():
                            break
                        try:
                            original_window = driver.current_window_handle
                            button.click()
                            time.sleep(1)
                            windows = driver.window_handles
                            if len(windows) > 1:
                                new_window = [w for w in windows if w != original_window][0]
                                driver.switch_to.window(new_window)
                                time.sleep(random.uniform(12, 35))
                                driver.close()
                                driver.switch_to.window(original_window)
                                random_delay(2, 5)
                        except Exception:
                            try:
                                if len(driver.window_handles) > 1:
                                    driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            except Exception:
                                pass
        except Exception as e:
            log_func(f"Website views error: {e}")

        # 3. YouTube views
        log_func("Processing YouTube views...")
        try:
            navigate_to(driver, "youtubenew2.php")
            time.sleep(2)
            buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton")
            if buttons:
                log_func(f"Found {len(buttons)} YouTube videos.")
                for button in buttons[:2]:
                    if is_stopped():
                        break
                    try:
                        button.click()
                        time.sleep(2)
                        log_func("Waiting for video timer...")
                        time.sleep(random.uniform(90, 135))
                        try:
                            submit_btn = driver.find_element(By.CSS_SELECTOR, "input[value='Submit']")
                            submit_btn.click()
                            time.sleep(2)
                        except NoSuchElementException:
                            pass
                        random_delay(3, 6)
                    except Exception:
                        continue
        except Exception as e:
            log_func(f"YouTube views error: {e}")

        # 4. SoundCloud plays
        log_func("Processing SoundCloud plays...")
        try:
            navigate_to(driver, "soundcloudplays.php")
            time.sleep(2)
            buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton")
            if buttons:
                log_func(f"Found {len(buttons)} SoundCloud tracks.")
                for button in buttons[:2]:
                    if is_stopped():
                        break
                    try:
                        button.click()
                        time.sleep(2)
                        log_func("Waiting for track to play...")
                        time.sleep(random.uniform(30, 60))
                        random_delay(2, 5)
                    except Exception:
                        continue
        except Exception as e:
            log_func(f"SoundCloud plays error: {e}")

        # Points update
        points = get_points(driver)
        update_points_func(points)

        wait_time = random.uniform(60, 180)
        log_func(f"Cycle {cycle} complete. Waiting {wait_time/60:.1f} minutes...")
        time.sleep(wait_time)

    log_func("Master loop stopped.")


def start_master_loop(setup_browser_func):
    """Master loop that cycles through all available tasks (CLI mode)."""
    print("\n[*] Starting Master Loop...")
    driver = setup_browser_func()
    if not driver:
        print("[!] Failed to initialize browser.")
        return

    try:
        driver.get(YLH_BASE)
        time.sleep(2)

        if not is_logged_in(driver):
            print("[!] Not logged in! Please use 'Setting Up' first.")
            return

        cycle = 0
        while True:
            cycle += 1
            print(f"\n[*] === Master Loop Cycle {cycle} ===")

            # 1. Daily bonus
            print("\n[*] Checking daily bonus...")
            try:
                navigate_to(driver, "bonuspoints.php")
                time.sleep(2)
                body = driver.find_element(By.TAG_NAME, "body").text
                if "you have made" not in body.lower():
                    try:
                        claim_btn = driver.find_element(By.CSS_SELECTOR, ".buybutton, button[onclick*='buy']")
                        if claim_btn.is_displayed():
                            print("[*] Claiming daily bonus...")
                            claim_btn.click()
                            time.sleep(3)
                    except NoSuchElementException:
                        pass
            except Exception as e:
                print(f"[!] Bonus check error: {e}")

            # 2. Website views
            print("\n[*] Processing website views...")
            try:
                navigate_to(driver, "websites.php")
                time.sleep(2)
                body = driver.find_element(By.TAG_NAME, "body").text
                if "no websites currently" not in body.lower():
                    buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton, .viewbutton")
                    if buttons:
                        print(f"[*] Found {len(buttons)} websites to view.")
                        for button in buttons[:3]:
                            try:
                                original_window = driver.current_window_handle
                                button.click()
                                time.sleep(1)
                                windows = driver.window_handles
                                if len(windows) > 1:
                                    new_window = [w for w in windows if w != original_window][0]
                                    driver.switch_to.window(new_window)
                                    time.sleep(random.uniform(12, 35))
                                    driver.close()
                                    driver.switch_to.window(original_window)
                                    random_delay(2, 5)
                            except Exception:
                                try:
                                    if len(driver.window_handles) > 1:
                                        driver.close()
                                    driver.switch_to.window(driver.window_handles[0])
                                except Exception:
                                    pass
            except Exception as e:
                print(f"[!] Website views error: {e}")

            # 3. YouTube views
            print("\n[*] Processing YouTube views...")
            try:
                navigate_to(driver, "youtubenew2.php")
                time.sleep(2)
                buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton")
                if buttons:
                    print(f"[*] Found {len(buttons)} YouTube videos.")
                    for button in buttons[:2]:
                        try:
                            button.click()
                            time.sleep(2)
                            print("[*] Waiting for video timer...")
                            time.sleep(random.uniform(90, 135))
                            try:
                                submit_btn = driver.find_element(By.CSS_SELECTOR, "input[value='Submit']")
                                submit_btn.click()
                                time.sleep(2)
                            except NoSuchElementException:
                                pass
                            random_delay(3, 6)
                        except Exception:
                            continue
            except Exception as e:
                print(f"[!] YouTube views error: {e}")

            # 4. SoundCloud plays
            print("\n[*] Processing SoundCloud plays...")
            try:
                navigate_to(driver, "soundcloudplays.php")
                time.sleep(2)
                buttons = driver.find_elements(By.CSS_SELECTOR, ".followbutton")
                if buttons:
                    print(f"[*] Found {len(buttons)} SoundCloud tracks.")
                    for button in buttons[:2]:
                        try:
                            button.click()
                            time.sleep(2)
                            print("[*] Waiting for track to play...")
                            time.sleep(random.uniform(30, 60))
                            random_delay(2, 5)
                        except Exception:
                            continue
            except Exception as e:
                print(f"[!] SoundCloud plays error: {e}")

            wait_time = random.uniform(60, 180)
            print(f"\n[*] Cycle {cycle} complete. Waiting {wait_time/60:.1f} minutes before next cycle...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print("\n[*] Master Loop stopped.")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
