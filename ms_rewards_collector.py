"""Microsoft Rewards points collector.

Automates the 20 daily Edge searches that earn Microsoft Rewards points using
plain mouse/keyboard automation (no Selenium, no browser driver).
"""

import json
import os
import random
import sys
import threading
import time
from pathlib import Path

try:
    import pyautogui
    from pynput import keyboard
except ImportError as exc:
    sys.exit(
        f"Missing dependency: {exc.name}\n"
        "Install the requirements first:\n\n"
        "    pip install -r requirements.txt\n"
    )

# Moving the mouse into a screen corner aborts the run.
pyautogui.FAILSAFE = True

COORDS_FILE = Path(__file__).resolve().parent / "coordinates.json"
SEARCHES_PER_DAY = 20
POINTS_PER_SEARCH = 3

# Pause on the results page before closing the tab. Microsoft does not credit
# searches fired faster than a human could plausibly read them.
SEARCH_WAIT_SECONDS = 3
# Shorter waits for the UI to catch up between individual clicks.
TAB_OPEN_WAIT = 1.2
TAB_CLOSE_WAIT = 1.0
FIELD_FOCUS_WAIT = 0.5
EDGE_LAUNCH_WAIT = 6.0

ABORT_HOTKEY = "<ctrl>+<shift>+q"
ABORT_HOTKEY_LABEL = "Ctrl+Shift+Q"

# Each entry is (key, prompt shown while capturing).
TARGETS = [
    ("new_tab", "the Edge NEW TAB button (the '+' on the tab strip)"),
    ("close_tab", "the tab's CLOSE button (the 'x' on the tab)"),
    ("search_field", "the SEARCH FIELD in a new tab"),
]

BANNER = r"""
  __  __ ___    ___                       _
 |  \/  / __|  | _ \_____ __ ____ _ _ _ __| |___
 | |\/| \__ \  |   / -_) V  V / _` | '_/ _` (_-<
 |_|  |_|___/  |_|_\___|\_/\_/\__,_|_| \__,_/__/
      ___     _ _         _
     / __|___| | |___ __ | |_ ___ _ _
    | (__/ _ \ | / -_) _||  _/ _ \ '_|
     \___\___/_|_\___\__| \__\___/_|
"""

# Word pools for building varied, unique-looking search queries.
# The three lists multiply out, so a few dozen of each is plenty for 20 a day.
ADJECTIVES = [
    "best", "cheap", "modern", "classic", "healthy", "quick", "easy", "famous",
    "hidden", "popular", "vintage", "portable", "compact", "reliable", "quiet",
    "affordable", "lightweight", "durable", "traditional", "unusual",
    "handmade", "minimalist", "rustic", "elegant", "sturdy", "foldable",
    "waterproof", "wireless", "insulated", "adjustable", "premium", "budget",
    "beginner", "professional", "colourful", "seasonal", "organic", "local",
    "antique", "refurbished", "custom", "stackable", "collapsible", "silent",
    "energy efficient", "space saving", "eco friendly", "long lasting",
    "fast drying", "heavy duty", "small", "large", "tiny", "oversized",
    "japanese", "italian", "nordic", "coastal", "urban", "homemade",
]
NOUNS = [
    "coffee", "laptop", "bicycle", "garden", "sneakers", "headphones", "novel",
    "camera", "backpack", "keyboard", "telescope", "guitar", "recipe",
    "mountain", "podcast", "aquarium", "greenhouse", "notebook", "sandwich",
    "harbour", "festival", "museum", "trail", "kettle", "printer",
    "umbrella", "lantern", "bookshelf", "mattress", "blender", "toolbox",
    "sketchbook", "tent", "kayak", "piano", "violin", "chessboard",
    "terrarium", "birdhouse", "compost bin", "rain jacket", "hiking boots",
    "desk lamp", "office chair", "monitor stand", "microphone", "turntable",
    "espresso machine", "cast iron pan", "chef knife", "cutting board",
    "watering can", "wheelbarrow", "lawn mower", "snow shovel", "bread maker",
    "slow cooker", "air fryer", "vacuum cleaner", "sewing machine", "loom",
    "pottery wheel", "easel", "watercolour set", "fountain pen", "typewriter",
    "binoculars", "compass", "sleeping bag", "camp stove", "fishing rod",
    "surfboard", "skateboard", "roller skates", "climbing rope", "yoga mat",
    "dumbbell", "treadmill", "jump rope", "herb garden", "bonsai tree",
]
CONTEXTS = [
    "for beginners", "under 50 dollars", "reviews", "near me", "tips",
    "ideas 2025", "vs alternatives", "buying guide", "history", "explained",
    "how to choose", "maintenance", "comparison", "trends", "checklist",
    "for small spaces", "on a budget", "worth it", "pros and cons",
    "common mistakes", "care instructions", "how it works", "step by step",
    "for kids", "for travel", "storage ideas", "cleaning tips", "repair guide",
    "best brands", "what to look for", "size guide", "setup guide",
    "troubleshooting", "accessories", "alternatives", "market price",
    "durability test", "long term review", "first impressions", "upgrade path",
    "diy version", "rental options", "second hand", "warranty",
    "energy use", "safety tips", "seasonal guide", "starter kit",
]


# --------------------------------------------------------------------------
# Console helpers
# --------------------------------------------------------------------------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def prompt(message=""):
    """input() that exits cleanly instead of raising when stdin is closed."""
    try:
        return input(message)
    except EOFError:
        print("\n\n  No input available - exiting.\n")
        raise SystemExit(0)


def show_banner():
    clear_screen()
    print(BANNER)
    print(f"  Earn {SEARCHES_PER_DAY * POINTS_PER_SEARCH} points a day "
          f"({SEARCHES_PER_DAY} searches x {POINTS_PER_SEARCH} points)\n")


def drain_stdin():
    """Discard keystrokes typed during a capture so they don't reach input()."""
    try:
        import msvcrt
    except ImportError:
        return
    while msvcrt.kbhit():
        msvcrt.getwch()


def countdown(seconds, message, abort=None):
    """Count down on one line. Returns True if the abort event fired."""
    for remaining in range(seconds, 0, -1):
        print(f"\r  {message} {remaining}... ", end="", flush=True)
        if abort is not None:
            if abort.wait(1):
                print("\r" + " " * 60 + "\r", end="")
                return True
        else:
            time.sleep(1)
    print("\r" + " " * 60 + "\r", end="")
    return False


def paused(abort, seconds):
    """Wait `seconds`. Returns True if the abort hotkey fired during the wait."""
    return abort.wait(seconds)


# --------------------------------------------------------------------------
# Coordinate storage
# --------------------------------------------------------------------------

def read_config():
    """Return {"points": {...}, "screen": (w, h) or None}, or None if unusable."""
    if not COORDS_FILE.exists():
        return None
    try:
        data = json.loads(COORDS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None

    points = {}
    for key, _ in TARGETS:
        point = data.get(key)
        if (not isinstance(point, dict)
                or not isinstance(point.get("x"), int)
                or not isinstance(point.get("y"), int)):
            return None
        points[key] = (point["x"], point["y"])

    screen = data.get("screen")
    if (isinstance(screen, dict)
            and isinstance(screen.get("width"), int)
            and isinstance(screen.get("height"), int)):
        saved_screen = (screen["width"], screen["height"])
    else:
        saved_screen = None

    return {"points": points, "screen": saved_screen}


def save_coordinates(points):
    """Create the coordinates file, or overwrite it if it already exists."""
    width, height = pyautogui.size()
    data = {key: {"x": x, "y": y} for key, (x, y) in points.items()}
    data["screen"] = {"width": width, "height": height}
    COORDS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def resolution_warning(saved_screen):
    """Return a warning string if the screen no longer matches the capture."""
    if saved_screen is None:
        return None
    current = tuple(pyautogui.size())
    if tuple(saved_screen) == current:
        return None
    return (f"  WARNING: coordinates were captured at "
            f"{saved_screen[0]}x{saved_screen[1]}, but this screen is "
            f"{current[0]}x{current[1]}.\n"
            f"  The clicks will land in the wrong place - "
            f"re-run Set Coordinates.")


# --------------------------------------------------------------------------
# Menu option 1: Set Coordinates
# --------------------------------------------------------------------------

def capture_point(description):
    """Track the mouse until 'c' is pressed. Returns (x, y), or None if cancelled."""
    print(f"\n  Move the mouse over {description}.")
    print("  Press 'c' to capture, or ESC to cancel.")

    result = {}
    done = threading.Event()

    def on_press(key):
        if key == keyboard.Key.esc:
            done.set()
            return False
        if getattr(key, "char", None) and key.char.lower() == "c":
            result["point"] = pyautogui.position()
            done.set()
            return False
        return None

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    try:
        while not done.is_set():
            x, y = pyautogui.position()
            print(f"\r    mouse: X={x:<6} Y={y:<6}", end="", flush=True)
            time.sleep(0.05)
    finally:
        listener.stop()
        listener.join()
        drain_stdin()

    point = result.get("point")
    if point is None:
        print("\r    cancelled." + " " * 20)
        return None
    print(f"\r    captured: X={point.x:<6} Y={point.y:<6}")
    return int(point.x), int(point.y)


def set_coordinates():
    show_banner()
    print("  -- Set Coordinates --")
    print("\n  Open Edge and put it side by side with this window so all three")
    print("  spots stay visible while you capture them.")
    print("\n  Move the mouse over each spot WITHOUT clicking - this window")
    print("  needs to keep keyboard focus so it can read the 'c' key.")
    prompt("\n  Press Enter when you are ready...")

    points = {}
    for key, description in TARGETS:
        point = capture_point(description)
        if point is None:
            print("\n  Setup cancelled - nothing was saved.")
            prompt("\n  Press Enter to return to the menu...")
            return
        points[key] = point

    save_coordinates(points)
    print(f"\n  Saved to {COORDS_FILE.name}:")
    for key, _ in TARGETS:
        x, y = points[key]
        print(f"    {key:<14} X={x:<6} Y={y}")
    prompt("\n  Press Enter to return to the menu...")


# --------------------------------------------------------------------------
# Menu option 2: Run Automation
# --------------------------------------------------------------------------

def generate_queries(count):
    """Build `count` distinct search strings."""
    queries = set()
    while len(queries) < count:
        queries.add(
            f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} "
            f"{random.choice(CONTEXTS)}"
        )
    query_list = list(queries)
    random.shuffle(query_list)
    return query_list


def launch_edge(abort):
    """Open and maximise Edge. Returns True if aborted."""
    print("  Launching Edge...")
    pyautogui.press("win")
    if paused(abort, 1.5):
        return True
    pyautogui.write("edge", interval=0.08)
    if paused(abort, 1.5):
        return True
    pyautogui.press("enter")
    if paused(abort, EDGE_LAUNCH_WAIT):  # Edge cold start
        return True
    pyautogui.hotkey("win", "up")  # maximise
    return paused(abort, 2)


def run_search_loop(points, queries, abort):
    """Run the search loop. Returns the number of completed searches."""
    completed = 0
    for index, query in enumerate(queries, start=1):
        print(f"  [{index:>2}/{len(queries)}] {query}")

        pyautogui.click(points["new_tab"])
        if paused(abort, TAB_OPEN_WAIT):
            break

        pyautogui.click(points["search_field"])
        if paused(abort, FIELD_FOCUS_WAIT):
            break

        pyautogui.write(query, interval=0.05)
        pyautogui.press("enter")
        if paused(abort, SEARCH_WAIT_SECONDS):
            break

        pyautogui.click(points["close_tab"])
        completed = index
        if paused(abort, TAB_CLOSE_WAIT):
            break

    return completed


def run_automation():
    config = read_config()
    if config is None:
        show_banner()
        print("  -- Run Automation --\n")
        print("  No saved coordinates found.")
        print("  Choose option 1 (Set Coordinates) first.")
        prompt("\n  Press Enter to return to the menu...")
        return

    show_banner()
    print("  -- Run Automation --\n")

    warning = resolution_warning(config["screen"])
    if warning:
        print(warning + "\n")

    print(f"  {SEARCHES_PER_DAY} searches will run using the saved coordinates.")
    print(f"  Each search rests {SEARCH_WAIT_SECONDS}s on the results page, so "
          f"expect roughly {estimate_runtime()} minutes.")
    print("\n  Do not touch the mouse or keyboard while it works.")
    print("  To stop early, use any of these:")
    print(f"    - press {ABORT_HOTKEY_LABEL}  (works even without window focus)")
    print("    - slam the mouse into a screen corner")
    print("    - press Ctrl+C in this window")
    prompt("\n  Press Enter to start...")

    queries = generate_queries(SEARCHES_PER_DAY)
    abort = threading.Event()
    completed = 0

    hotkey_listener = keyboard.GlobalHotKeys({ABORT_HOTKEY: abort.set})
    hotkey_listener.start()
    try:
        if countdown(5, "Starting in", abort) or launch_edge(abort):
            print("  Aborted before the searches began.")
        else:
            completed = run_search_loop(config["points"], queries, abort)
    except pyautogui.FailSafeException:
        print("\n  Aborted - mouse moved to a screen corner.")
    except KeyboardInterrupt:
        print("\n  Aborted - Ctrl+C.")
    else:
        if abort.is_set():
            print(f"\n  Aborted - {ABORT_HOTKEY_LABEL} pressed.")
        else:
            print("\n  All searches finished.")
    finally:
        hotkey_listener.stop()
        drain_stdin()

    print(f"\n  Completed {completed}/{SEARCHES_PER_DAY} searches "
          f"(~{completed * POINTS_PER_SEARCH} points).")
    prompt("\n  Press Enter to return to the menu...")


def estimate_runtime():
    """Rough minutes a full run takes, for the pre-flight summary."""
    per_search = (TAB_OPEN_WAIT + FIELD_FOCUS_WAIT + SEARCH_WAIT_SECONDS
                  + TAB_CLOSE_WAIT + 1.5)  # 1.5s allowance for typing
    total = SEARCHES_PER_DAY * per_search + EDGE_LAUNCH_WAIT + 7
    return round(total / 60, 1)


# --------------------------------------------------------------------------
# Menu option 3: View Saved Coordinates
# --------------------------------------------------------------------------

def view_coordinates():
    show_banner()
    print("  -- Saved Coordinates --\n")

    config = read_config()
    if config is None:
        print("  Nothing saved yet. Choose option 1 (Set Coordinates) first.")
        prompt("\n  Press Enter to return to the menu...")
        return

    for key, description in TARGETS:
        x, y = config["points"][key]
        print(f"    {key:<14} X={x:<6} Y={y:<6}  - {description}")

    current = pyautogui.size()
    saved = config["screen"]
    print(f"\n    captured at   {saved[0]}x{saved[1]}" if saved
          else "\n    captured at   (unknown)")
    print(f"    this screen   {current[0]}x{current[1]}")
    print(f"\n  File: {COORDS_FILE}")

    warning = resolution_warning(saved)
    if warning:
        print("\n" + warning)

    prompt("\n  Press Enter to return to the menu...")


# --------------------------------------------------------------------------
# Menu
# --------------------------------------------------------------------------

def main():
    while True:
        show_banner()
        status = "ready" if read_config() else "not set"
        print(f"  Coordinates: {status}\n")
        print("    1. Set Coordinates")
        print("    2. Run Automation")
        print("    3. View Saved Coordinates")
        print("    4. Exit")

        choice = prompt("\n  Select an option: ").strip()
        if choice == "1":
            set_coordinates()
        elif choice == "2":
            run_automation()
        elif choice == "3":
            view_coordinates()
        elif choice == "4":
            print("\n  Bye.\n")
            return
        else:
            print("\n  Enter 1, 2, 3 or 4.")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted.\n")
