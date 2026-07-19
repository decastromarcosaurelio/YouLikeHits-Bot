import sys
import time
import undetected_chromedriver as uc

YLH_BASE = "https://www.youlikehits.com"

def setup_browser(profile_dir="chrome_profile"):
    """Initialize persistent Chrome browser."""
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

def main_menu():
    """Display main menu."""
    while True:
        print("\n" + "=" * 50)
        print("       YOULIKEHITS AUTOBOT")
        print("=" * 50)
        print("1. Setting Up (Open browser for manual login)")
        print("2. Website Views Loop")
        print("3. YouTube Views Loop")
        print("4. SoundCloud Plays Loop")
        print("5. Daily Bonus Claimer")
        print("6. Master Loop (Cycles through all)")
        print("0. Exit")
        print("=" * 50)

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            print("\n[*] Starting 'Setting Up' mode...")
            print("[*] The browser will open. Please log in to YouLikeHits.")
            print("[*] Close the browser window when you are done to return to this menu.")
            driver = setup_browser()
            if driver:
                driver.get(f"{YLH_BASE}/login.php")
                try:
                    while True:
                        _ = driver.window_handles
                        time.sleep(1)
                except Exception:
                    print("[*] Browser closed. Returning.")
                    try:
                        driver.quit()
                    except:
                        pass

        elif choice == "2":
            print("\n[*] Website Views loop selected.")
            from bot_logic.websites import start_website_loop
            start_website_loop(setup_browser)

        elif choice == "3":
            print("\n[*] YouTube Views loop selected.")
            from bot_logic.youtube import start_youtube_loop
            start_youtube_loop(setup_browser)

        elif choice == "4":
            print("\n[*] SoundCloud Plays loop selected.")
            from bot_logic.soundcloud import start_soundcloud_loop
            start_soundcloud_loop(setup_browser)

        elif choice == "5":
            print("\n[*] Daily Bonus Claimer selected.")
            from bot_logic.bonus import start_bonus_loop
            start_bonus_loop(setup_browser)

        elif choice == "6":
            print("\n[*] Master Loop selected.")
            from bot_logic.master import start_master_loop
            start_master_loop(setup_browser)

        elif choice == "0":
            print("\n[*] Exiting Autobot. Goodbye!")
            sys.exit(0)
        else:
            print("\n[!] Invalid choice. Please enter a number from 0 to 6.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n[*] Script interrupted.")
        sys.exit(0)
