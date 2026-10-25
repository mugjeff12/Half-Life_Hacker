# Half-Life Hacker — NAYGN McMaster workshop (desktop edition)

A desktop version of the *Half-Life Hacker* notebook: nuclear decay chains, the
I-135 → Xe-135 xenon transient, decay heat, and Cs-137 / Sr-90 waste. Instead of
Jupyter you get a branded app with a lesson pane, a real code editor, live plots,
sliders, hints and automatic ✓/✗ checks. It runs the **exact code cells** from the
notebook.

Branding: NAYGN logo + palette (dark pink `#7E0237`, black, white, grey).

## Run from source

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Headless smoke test (runs every step with its solution, optional screenshots):

```bash
python main.py --selftest --shots shots/ --size 1280x800
```

## Build an executable

PyInstaller **cannot cross-compile**. Build on the OS you want to ship for.

| Target  | How |
|---------|-----|
| Windows | double-click `build_windows.bat` → `dist\HalfLifeHacker\HalfLifeHacker.exe` + `dist\HalfLifeHacker-Windows.zip` |
| macOS / Linux | `./build.sh` → `dist/HalfLifeHacker/` + zip |
| All three, no local setup | push to GitHub; the **Build** workflow (`.github/workflows/build.yml`) builds Windows, macOS and Linux and uploads zips as artifacts (Actions tab → latest run) |

**Mac test workflow** (`.github/workflows/mac-test.yml`, manual): builds on real Apple Silicon + Intel runners, unzips the zip the way a student would (adds the quarantine flag), checks the CPU architecture, runs the self-test and uploads a screenshot of every step. It can't show the Gatekeeper prompt, so still try one real Mac.

`python build.py --test` builds and then runs the frozen app's self-test.
Other flags: `--onefile`, `--no-zip`.

The bundle is large (~200 MB zipped) because it ships Qt, numpy, scipy and matplotlib.

**Unsigned app warnings.** Windows SmartScreen ("More info → Run anyway") and macOS
Gatekeeper will complain, since the app isn't code-signed.

**Mac students.** Apple Silicon and Intel Macs need different builds (the workflow makes both:
`HalfLifeHacker-macOS` = M-series, `HalfLifeHacker-macOS-Intel`). Unzip, drag `HalfLifeHacker.app` into
Applications, double-click it; when macOS refuses, open **System Settings → Privacy & Security**, scroll down
and click **Open Anyway**. Fallback: in Terminal run
`xattr -dr com.apple.quarantine /Applications/HalfLifeHacker.app`.

## Sharing with students

Students **do not** run the `.bat` / build scripts — those are only for whoever creates the app (once).

1. Build once on a Windows PC (`build_windows.bat`, or the GitHub Actions workflow).
2. Send students **`dist\HalfLifeHacker-Windows.zip`** (a download link is easiest, it's ~200 MB).
3. They unzip it and double-click `HalfLifeHacker.exe`. No Python install needed.

Prefer a single file? Run `build_windows.bat --onefile`; students get one `HalfLifeHacker.exe`
(simplest to hand out, but it takes a few extra seconds to start each time).

## Using the app

* Left sidebar: sections (Rungs). Bottom bar: Back / Next (Next glows when the step is done).
* **Run** (F5 or Ctrl+Enter) runs your code; the console shows ✓/✗ checks and friendly errors.
* **Hint** gives a ladder of nudges; **Reset** restores the starter code. The 👁 **Solution** button is hidden in the student build — instructors can bring it back by launching with the environment variable `HLH_INSTRUCTOR=1` (e.g. `set HLH_INSTRUCTOR=1 && HalfLifeHacker.exe` on Windows, `HLH_INSTRUCTOR=1 ./HalfLifeHacker` on macOS/Linux).
* **⤢ Expand plot** (or Ctrl+E) opens the plot in its own big window with zoom / pan / save; it keeps updating as you run or move sliders.
* Sliders re-run a simulation live; prediction steps lock in your guess before revealing.
* Progress and your code auto-save to your user data folder.
* File → *Export my code* writes everything you've typed to a `.py` file; *Reset all progress* starts over.

| Shortcut | Action |
|----------|--------|
| F5 / Ctrl+Enter | Run |
| Ctrl + `=` / `−` / `0` | Zoom text in / out / reset |
| Ctrl+B | Toggle sidebar |
| F11 | Full screen |

## Updating the lessons from the notebook

```bash
python tools/extract_cells.py half_life_hacker.ipynb   # regenerates hlh/cells.py
python tools/engine_test.py                            # headless check of every step
```

Lesson text, solutions and auto-checks live in `hlh/content.py` (solutions are asserted-unique
string replacements on notebook cells, so a changed cell fails loudly instead of silently).

## Layout

```
main.py            entry point (+ --selftest)
build.py           PyInstaller driver
hlh/
  theme.py         palette, QSS, matplotlib style
  session.py       persistent exec namespace, check(), error translation
  content.py       steps, sections, solutions, hidden checks
  cells.py         AUTO-GENERATED notebook cells
  editor.py        code editor + highlighter
  widgets.py       lesson view, console, plot panel
  stepview.py      one step's UI + run logic
  mainwindow.py    window, sidebar, menus
  mathimg.py       equations -> PNG (mathtext)
  state.py         progress persistence
  selftest.py      headless tests
assets/            logo, icons, workshop photos
tools/             extract_cells.py, make_assets.py, engine_test.py
```

Fonts: DejaVu Sans / Mono (from matplotlib) are bundled so the app looks the same everywhere.
