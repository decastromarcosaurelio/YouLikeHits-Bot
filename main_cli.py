"""YouLikeHits Autobot - CLI menu."""
import sys
import time

from bot_logic.utils import YLH_BASE, setup_browser, is_browser_alive
from bot_logic import settings as settings_mod


def _setting_up():
    print("\n[*] Starting 'Setting Up' mode...")
    print("[*] The browser will open. Please log in to YouLikeHits.")
    print("[*] Close the browser window when you are done to return to this menu.")
    driver = setup_browser()
    if not driver:
        return
    driver.get(f"{YLH_BASE}/login.php")
    try:
        while is_browser_alive(driver):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    print("[*] Browser closed. Returning.")
    try:
        driver.quit()
    except Exception:
        pass


def _ask_cycle_wait():
    """Ask for the wait between master cycles; Enter keeps the saved value."""
    current = settings_mod.load()
    lo, hi = current["cycle_wait_min_minutes"], current["cycle_wait_max_minutes"]
    print(f"\n[*] Wait between cycles is {lo:g}-{hi:g} minutes (random in that range).")
    answer = input("    New min-max in minutes, e.g. 2-5 (Enter to keep): ").strip()
    if answer:
        parts = answer.replace(",", "-").split("-")
        try:
            new_lo = float(parts[0])
            new_hi = float(parts[1]) if len(parts) > 1 and parts[1] else new_lo
            current = settings_mod.save({**current, "cycle_wait_min_minutes": new_lo,
                                         "cycle_wait_max_minutes": new_hi})
            print(f"[*] Saved: {current['cycle_wait_min_minutes']:g}-{current['cycle_wait_max_minutes']:g} minutes.")
        except (ValueError, IndexError):
            print("[!] Could not read that; keeping the saved value.")
    return current


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
            _setting_up()
        elif choice == "2":
            from bot_logic.websites import start_website_loop
            start_website_loop(setup_browser)
        elif choice == "3":
            from bot_logic.youtube import start_youtube_loop
            start_youtube_loop(setup_browser)
        elif choice == "4":
            from bot_logic.soundcloud import start_soundcloud_loop
            start_soundcloud_loop(setup_browser)
        elif choice == "5":
            from bot_logic.bonus import start_bonus_loop
            start_bonus_loop(setup_browser)
        elif choice == "6":
            from bot_logic.master import start_master_loop
            start_master_loop(setup_browser, settings=_ask_cycle_wait())
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
