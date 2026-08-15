# Microsoft Rewards Points Collector

Microsoft Rewards gives you **3 points per Edge search**, up to **20 searches a day** — that's **60 points daily** for a few minutes of clicking.

This script does the clicking for you. It opens Edge, runs 20 real searches with different terms each time, and closes each tab as it goes.

No Selenium, no browser extension, no drivers. It just moves your mouse and types on your keyboard, the same way you would.

---

## What you need

- **Windows** with **Microsoft Edge** installed
- **Python 3.8 or newer** — [download here](https://www.python.org/downloads/)
  - During install, tick **"Add python.exe to PATH"**. This matters; without it, the commands below won't work.
- You should be **signed into Edge** with the Microsoft account that collects the points

---

## Setup

**1. Get the code**

```bash
git clone https://github.com/DeveloperP097nda/ms-rewards-collector.git
cd ms-rewards-collector
```

No Git? Click the green **Code** button on GitHub → **Download ZIP** → extract it anywhere.

**2. Install the two libraries it needs**

```bash
pip install -r requirements.txt
```

**3. Start it**

```bash
python ms_rewards_collector.py
```

On Windows you can also just **double-click `run.bat`** instead of typing anything.

---

## Using it

You'll see a menu:

```
    1. Set Coordinates
    2. Run Automation
    3. View Saved Coordinates
    4. Exit
```

### First time: option 1, Set Coordinates

The script clicks at fixed screen positions, so it needs to learn where three buttons live on **your** screen. This takes about 30 seconds and you only do it once.

Open Edge and arrange it **side by side** with the terminal window, so you can see both at the same time. Then pick option **1**.

It asks you for three spots, one at a time:

| # | Spot | Where it is |
|---|------|-------------|
| 1 | **New tab button** | The `+` at the end of the tab strip |
| 2 | **Close tab button** | The `x` on an open tab |
| 3 | **Search field** | The search box in the middle of a new tab page |

For each one: **hover the mouse over it and press `c`**. The live mouse position is shown as you move, so you can line it up precisely.

> **Important:** hover, don't click. This terminal window has to keep keyboard focus so it can hear the `c` key. If you click on Edge, click back on the terminal before pressing `c`.

Press `Esc` at any point to cancel without saving.

Your three positions get written to `coordinates.json`, right next to the script. Redo option 1 whenever you want to overwrite them.

### After that: option 2, Run Automation

Pick option **2**, read the summary, press Enter. You get a 5-second countdown to get your hands off the mouse, then it:

1. Opens the Start menu, types `edge`, hits Enter, and maximises the window
2. Repeats 20 times: new tab → click the search box → type a search → Enter → wait 3 seconds → close the tab

A full run takes **under 3 minutes**. Each search is printed as it happens, so you can watch the progress.

**Leave the mouse and keyboard alone while it runs.** The script drives them; fighting it will send clicks to the wrong place.

---

## Stopping it early

Three ways out, any time during a run:

| How | Notes |
|-----|-------|
| **`Ctrl` + `Shift` + `Q`** | The easiest one. Works even when Edge has focus, not the terminal. |
| **Throw the mouse into a screen corner** | PyAutoGUI's built-in failsafe. Good panic button. |
| **`Ctrl` + `C`** in the terminal | Only works if the terminal window is focused. |

However you stop it, the script tells you how many searches finished and roughly how many points that earned, then drops you back at the menu.

---

## Troubleshooting

**Clicks land in the wrong place**

Almost always means the saved positions no longer match your screen. Re-run option **1**. This happens after you change screen resolution, change display scaling, move Edge to a different monitor, or if Edge's toolbar layout changes.

The script watches for this: it stores the resolution you captured at and warns you if it doesn't match. Option **3** shows the saved positions alongside your current resolution.

**"Missing dependency" on startup**

You skipped step 2, or installed into a different Python. Run `pip install -r requirements.txt` again.

**"Python was not found" / `python` isn't recognised**

Python isn't on your PATH. Reinstall it with **"Add python.exe to PATH"** ticked, or use `py` instead of `python`.

**Edge doesn't open, or the first search goes into the Start menu**

Edge is starting slower than the script expects. Open `ms_rewards_collector.py` and raise `EDGE_LAUNCH_WAIT` near the top from `6.0` to `10.0` or more.

Opening Edge yourself before choosing option 2 also works — the script's Start-menu step will just focus the window that's already running.

**Searches run but no points appear**

Check that Edge is signed into the right Microsoft account, and that you haven't already used today's 20 searches. Points can also take a few minutes to show on the Rewards dashboard.

---

## Tuning

The timings live at the top of `ms_rewards_collector.py` and are easy to adjust:

```python
SEARCHES_PER_DAY    = 20     # searches per run
POINTS_PER_SEARCH   = 3      # only used for the points estimate
SEARCH_WAIT_SECONDS = 3      # pause on the results page
TAB_OPEN_WAIT       = 1.2    # after clicking new tab
TAB_CLOSE_WAIT      = 1.0    # after closing the tab
FIELD_FOCUS_WAIT    = 0.5    # after clicking the search box
EDGE_LAUNCH_WAIT    = 6.0    # Edge cold start
```

If searches are getting missed, raise the waits. Slower is more reliable.

Search terms are built by combining three word lists in the same file (60 adjectives × 81 nouns × 48 contexts ≈ **233,000** possible phrases), so you get natural-looking, never-repeating searches like `compact espresso machine buying guide`. Add your own words to those lists if you like.

---

## Notes

- The daily search cap and points per search are set by Microsoft and vary by country. 3 points × 20 searches reflects the common desktop setup; adjust the constants above if your region differs.
- Only desktop searches are covered here. Mobile searches earn separately and aren't part of this.
- `coordinates.json` is specific to your screen, so it's `.gitignore`d and never committed.

## Disclaimer

This is a personal automation tool, provided as-is for educational purposes. Automated searching may conflict with the [Microsoft Rewards Terms of Service](https://www.microsoft.com/rewards/terms), and accounts can be suspended for it. Use it on your own account, at your own risk.
