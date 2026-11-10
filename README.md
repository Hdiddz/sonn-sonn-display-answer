# sonnsonn

![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)

**Press a hotkey, get the answer for the question on your screen.** sonnsonn
takes a screenshot, asks a vision model, and signals the answer two ways:
a row of **CapsLock flashes** (A = 1 flash … F = 6) and an optional compact
popup in the corner.

![sonnsonn answering a multiple-choice question](docs/demo.png)

## What it does

- **One hotkey** — press **F9**, the primary monitor is captured and sent to
  the model. Nothing is written to disk.
- **CapsLock answers** — A–F map to 1–6 flashes, so the answer is readable at a
  glance without looking at another window. Unlabeled options use their
  displayed order (top to bottom, then left to right).
- **Optional popup** — 104 × 58 px by default, in any of five corners, at
  50–200 % scale. It never takes keyboard focus and closes by itself.
- **Written answers** — essays and a/b/c subquestions are answered in the same
  language and saved to `latest-answer.txt`.
- **Thinking mode** — off / low / high / max reasoning effort (default `high`),
  which makes arithmetic and multi-step questions noticeably more reliable.
- **Web grounding** — when a question depends on current facts, sonnsonn checks
  the DeepSeek Search API and answers from the results.
- **Bring your own model** — any OpenAI-compatible endpoint that accepts images
  and JSON mode works.

## Requirements

| | |
|---|---|
| OS | Windows 10 or 11 (the hotkey and CapsLock control are Windows-only) |
| Python | 3.10 or newer (only for the source install; the zip still needs Python) |
| Account | A DeepSeek API key, or any OpenAI-compatible vision endpoint |

## Quick install (recommended)

1. Open **[Releases](https://github.com/Hdiddz/sonn-sonn-display-answer/releases/latest)**
   and download **`sonnsonn.zip`**.
2. Extract it into a normal writable folder — for example
   `C:\Users\<you>\Documents\sonnsonn`. Avoid `C:\Program Files`.
3. Double-click **`sonnsonn.cmd`**. The first run creates `.venv` and installs
   the two dependencies (about a minute, needs internet).
4. In the console menu choose **`[6] API key`** and paste your DeepSeek key
   (typing is hidden). It is stored in `.env` next to the scripts.
5. Choose **`[1]`** to start, then press **F9** on any question.

The monitor keeps running in the background; the console window closes once it
has started. `stop.cmd` stops it.

## Manual install from source

```powershell
git clone https://github.com/Hdiddz/sonn-sonn-display-answer.git
cd sonn-sonn-display-answer
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\sonnsonn.cmd
```

Or configure it by hand: copy `.env.example` to `.env` and fill in your key,
then run `start.cmd`.

## Usage

| Action | How |
|---|---|
| Capture and answer | press **F9** |
| Read a written answer | double-click `open-answer.cmd` |
| Stop the monitor | double-click `stop.cmd` |
| Change settings | double-click `sonnsonn.cmd` again (control menu) |

Each capture sends the **entire primary screen** to the API and uses credit.
Wait for the answer before pressing F9 again; a written answer can take up to
90 seconds. Holding **Alt** suppresses a capture.

## Settings console

Starting the app while it is stopped opens the full menu:

```
  CapsLock Monitor
    popup    : on
    position : bottom-left    scale: 100%
    thinking : high
    api key  : sk-4...e246
    model    : deepseek-flash  (https://api.deepseek.com)

    [1] Start - answer box + CapsLock flashes
    [2] Start - CapsLock flashes only
    [3] Popup position
    [4] Popup size
    [5] Thinking effort (off/low/high/max)
    [6] API key
    [7] Model / API base URL
    [8] Exit
```

Starting it while already running opens a **control menu** instead: stop the
monitor, hide/show the box, move it, resize it, or change thinking effort — all
without restarting.

Settings live in `.monitor-settings` and are re-read for every answer, which is
why changes take effect immediately:

```ini
popup=on
position=bottom-left
scale=100
thinking=high
```

Allowed positions: `bottom-left`, `bottom-right`, `top-left`, `top-right`,
`center`. Scale: `50`–`200`.

## Answer signals

| Letter | CapsLock flashes |
|---|---|
| A | 1 |
| B | 2 |
| C | 3 |
| D | 4 |
| E | 5 |
| F | 6 |

Written answers and "no readable question" use a distinct long/short tone when
sound is enabled; the default build is silent.

## Models and providers

- Default: `deepseek-flash` on `https://api.deepseek.com`.
- **Thinking** maps to DeepSeek's `thinking: enabled` plus `reasoning_effort`
  (`low` / `high` / `max`). It raises the reply budget to 8192 tokens because
  reasoning counts toward the output. Thinking is DeepSeek-only.
- **Other providers**: set the base URL (menu `[7]`, or `DEEPSEEK_BASE_URL` in
  `.env`). The endpoint must accept `image_url` content and
  `response_format: json_object`. Thinking and the search tool are skipped
  there.

```ini
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## Web grounding

When the model decides a question needs current information, sonnsonn calls the
DeepSeek Search API once, feeds the top results back, and re-answers. Costs one
search request ($0.75 per 1,000) plus one text-only follow-up. If search fails,
the first answer is kept. Disable with `DEEPSEEK_SEARCH=off` in `.env`.

## Troubleshooting

**F9 does nothing.** Start the app from **your own** Explorer window or a normal
terminal. Processes started by an automation/sandbox context can run at *low
integrity*, where Windows blocks keyboard reads. `monitor.log` prints the
integrity level at startup — it must say `integrity medium`. Also try
**Fn+F9**: on many laptops the function row is in media mode.

**"Monitor exited during startup".** Check `monitor.log` and
`monitor-error.log` in the project folder. The usual cause is a missing or
invalid API key.

**No answer box.** The setting `popup=off` hides it (CapsLock flashes still
work). Turn it back on from the running control menu, option `[3]`.

**HTTP 401 / 402.** 401 is a bad key; 402 means the account is out of balance.

**Wrong answers on math.** Raise thinking to `max` with menu `[5]`.

## Privacy

Screenshots are held in memory and posted to the model provider you configured;
they are never written to disk unless you pass `--save-dir`. The last answer is
stored in `latest-answer.txt`, and your API key is kept in `.env` (both are
git-ignored).

## Responsible use

sonnsonn is a screen-reading and accessibility helper. Use it only where
outside assistance is allowed — not in exams, certifications, or assessments
that forbid it, and not in a way that breaks your provider's terms. You are
responsible for how you use it and for the answers it produces; AI answers can
be wrong.

## Development

```powershell
.\.venv\Scripts\python.exe -m unittest test_monitor.py   # 38 tests, no network
.\.venv\Scripts\python.exe monitor.py --selftest          # quick logic check
```

`run_tests.py` is the low-level library suite and **toggles the real CapsLock /
NumLock LEDs** while it runs.

| File | Purpose |
|---|---|
| `monitor.py` | hotkey loop, capture, API calls, search, answer signals |
| `capture_popup.py` | the Win32 popup (position, scale, no-activate) |
| `control.ps1` | settings and control console behind `sonnsonn.cmd` |
| `sonnsonn.cmd` / `start.cmd` / `stop.cmd` | launchers |
| `open-answer.cmd` | opens the last answer |
| `demo.py` | flashes arbitrary text in Morse on the lock LEDs |
| `test_monitor.py` | unit tests |

## License

No license has been added yet. Until one is, the code is all rights reserved by
the author.
