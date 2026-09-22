"""YouLikeHits Autobot - CLI menu."""
import sys
import time

from bot_logic.utils import YLH_BASE, setup_browser, is_browser_alive
from bot_logic import settings as settings_mod


def _setting_up():
    print("\n[*] Starting 'Setting Up' mode...")
    print("[*] The browser will open. Please log in to YouLikeHits.")
    print("[*] For YouTube Likes and SoundCloud Follows, also log in to YouTube and SoundCloud there.")
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


def parse_task_selection(answer, current):
    """Task keys chosen by `answer` ('' keeps `current`, 'all', 'none', or numbers like '1,3').

    Numbers index settings.TASKS from 1. Returns None when the answer cannot be read.
    """
    answer = (answer or "").strip().lower()
    if not answer:
        return list(current)
    if answer == "all":
        return list(settings_mod.TASK_KEYS)
    if answer == "none":
        return []
    try:
        numbers = {int(part) for part in answer.replace(",", " ").split()}
    except ValueError:
        return None
    if not numbers or any(n < 1 or n > len(settings_mod.TASKS) for n in numbers):
        return None
    return [key for i, key in enumerate(settings_mod.TASK_KEYS, start=1) if i in numbers]


def _ask_master_tasks(current):
    """Ask which tasks the master loop runs; Enter keeps the saved selection."""
    enabled = settings_mod.enabled_tasks(current)
    print("\n[*] Master loop tasks:")
    for i, (key, label) in enumerate(settings_mod.TASKS, start=1):
        print(f"    {i}. [{'x' if key in enabled else ' '}] {label}")
    answer = input("    Tasks to run, e.g. 1,2,3 or 'all' (Enter to keep): ")
    chosen = parse_task_selection(answer, enabled)
    if chosen is None:
        print("[!] Could not read that; keeping the saved selection.")
        return current
    if chosen != enabled:
        current = settings_mod.save({**current, "master_tasks": chosen})
        names = ", ".join(settings_mod.TASK_LABELS[k] for k in current["master_tasks"]) or "none"
        print(f"[*] Saved: {names}.")
    return current


def _ask_master_settings():
    """Wait range and task selection for the master loop, persisted to settings.json."""
    return _ask_master_tasks(_ask_cycle_wait())


def main_menu():
    """Display main menu."""
    while True:
        print("\n" + "=" * 50)
        print("       YOULIKEHITS AUTOBOT")
        print("=" * 50)
        print("1. Setting Up (Open browser for manual login)")
        print("2. Website Views Loop")
        print("3. YouTube Views Loop")
        print("4. YouTube Likes Loop")
        print("5. SoundCloud Plays Loop")
        print("6. SoundCloud Follows Loop")
        print("7. Daily Bonus Claimer")
        print("8. Master Loop (Cycles through the selected tasks)")
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
            from bot_logic.youtube_likes import start_youtube_likes_loop
            start_youtube_likes_loop(setup_browser)
        elif choice == "5":
            from bot_logic.soundcloud import start_soundcloud_loop
            start_soundcloud_loop(setup_browser)
        elif choice == "6":
            from bot_logic.soundcloud_follows import start_soundcloud_follows_loop
            start_soundcloud_follows_loop(setup_browser)
        elif choice == "7":
            from bot_logic.bonus import start_bonus_loop
            start_bonus_loop(setup_browser)
        elif choice == "8":
            from bot_logic.master import start_master_loop
            start_master_loop(setup_browser, settings=_ask_master_settings())
        elif choice == "0":
            print("\n[*] Exiting Autobot. Goodbye!")
            sys.exit(0)
        else:
            print("\n[!] Invalid choice. Please enter a number from 0 to 8.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n[*] Script interrupted.")
        sys.exit(0)
