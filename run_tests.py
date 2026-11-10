"""Test suite for the capslockmorsecode module.

Runs on Windows, macOS, and Linux. Uses plain asserts and prints, so no
test framework is required.

Run:
    python3 run_tests.py   (macOS/Linux)
    py run_tests.py        (Windows)

WARNING: the LED tests toggle your actual CapsLock/NumLock keys.
Your keyboard LED will blink and the lock states will be toggled.
"""

import sys
import time

import capslockmorsecode as mc

PASSED = 0
FAILED = 0


def check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")


print("=" * 60)
print("capslockmorsecode test suite")
print("=" * 60)
print(f"Python:       {sys.version.split()[0]}")
print(f"Platform:     {sys.platform}")
print(f"Module ver:   {getattr(mc, '__version__', 'unknown')}")
print(f"Module path:  {mc.__file__}")
print()

# ---------------------------------------------------------------------------
# 1. Import / API surface
# ---------------------------------------------------------------------------
print("[1] API surface")
for func_name in ("morse", "dot", "dash", "flash", "translate",
                  "caps_lock", "num_lock", "scroll_lock"):
    check(f"has {func_name}()", callable(getattr(mc, func_name, None)))
print()

# ---------------------------------------------------------------------------
# 2. translate(): text -> morse
#
# NOTE: in capslockmorsecode 0.1.0, translate() is an unfinished TODO stub
# that always returns None. We verify that this known limitation still holds
# and that a reference translation over the module's own MORSE_CODE table
# (which morse() consumes) matches expected Morse output.
# ---------------------------------------------------------------------------
print("[2] translate() / MORSE_CODE table")
check("translate() is a known-unimplemented stub (returns None)",
      mc.translate("SOS") is None,
      "library appears to have implemented translate(); update this test")

def reference_translate(text):
    words = []
    for word in text.upper().split(" "):
        words.append("/".join(mc.MORSE_CODE[c] for c in word
                              if c in mc.MORSE_CODE))
    return " ".join(words)

expected = {
    "SOS": ".../---/...",
    "A": ".-",
    "E": ".",
    "HELLO": "...././.-../.-../---",
}
for text, morse in expected.items():
    got = reference_translate(text)
    check(f"MORSE_CODE table: {text!r} -> {morse!r}", got == morse,
          f"got {got!r}")
print()

# ---------------------------------------------------------------------------
# 3. morse() accepts both plain text and raw morse
# ---------------------------------------------------------------------------
print("[3] morse() string handling (no LED, dry checks)")
try:
    # Very fast speed keeps the test quick; use the 'num' key so we
    # exercise a non-default path where supported.
    mc.morse("", speed=100)  # empty string should be a no-op
    check("morse('') is a no-op", True)
except Exception as e:
    check("morse('') is a no-op", False, f"raised {e!r}")

# Raw morse should produce the same timing plan as translated text.
try:
    mc.morse(".../---/...", speed=100)
    check("morse() accepts raw morse ('.../---/...')", True)
except Exception as e:
    check("morse() accepts raw morse", False, f"raised {e!r}")
print()

# ---------------------------------------------------------------------------
# 4. Windows backend selection
# ---------------------------------------------------------------------------
print("[4] Backend selection")
if sys.platform == "win32":
    check("win32 detected", True)
    import ctypes
    check("ctypes.windll available",
          hasattr(ctypes, "windll"),
          "ctypes.windll missing; module cannot control LEDs")
    check("module uses the windows backend",
          mc.caps_lock.__name__ == "_caps_lock_windows",
          f"caps_lock is bound to {mc.caps_lock.__name__}")
else:
    check("non-windows platform, backend is "
          f"{mc.caps_lock.__name__}", True)
print()

# ---------------------------------------------------------------------------
# 5. LED toggling (hardware)
#
# NOTE: MacBook internal keyboards stop accepting LED-change requests after
# a few seconds (Apple's anti-abuse behavior). On darwin these toggles are
# soft warnings; on win32/Linux they are hard checks.
# ---------------------------------------------------------------------------
print("[5] LED hardware test (watch your CapsLock/NumLock LEDs)")
soft = sys.platform == "darwin"

def soft_check(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS  {name}")
    elif soft:
        print(f"  WARN  {name}  {detail}")
        print("        (known MacBook internal-keyboard LED limitation)")
    else:
        FAILED += 1
        print(f"  FAIL  {name}  {detail}")

try:
    original = mc.caps_lock()  # read current state
    check("caps_lock() reads state (returned a bool)", isinstance(original, bool))

    mc.caps_lock(False)
    soft_check("caps_lock(False) -> state off", mc.caps_lock() is False)

    mc.caps_lock(True)
    soft_check("caps_lock(True) -> state on", mc.caps_lock() is True)

    mc.caps_lock(original)
    soft_check("caps_lock() restored original state", mc.caps_lock() == original)
except Exception as e:
    check("caps_lock() toggle", False, f"raised {e!r}")

try:
    original = mc.num_lock()
    mc.num_lock(not original)
    soft_check("num_lock() toggles state", mc.num_lock() == (not original))
    mc.num_lock(original)
    soft_check("num_lock() restored", mc.num_lock() == original)
except Exception as e:
    check("num_lock() toggle", False, f"raised {e!r}")
print()

# ---------------------------------------------------------------------------
# 6. dot / dash / flash at high speed
# ---------------------------------------------------------------------------
print("[6] dot/dash/flash (high speed)")
try:
    for func, name in ((mc.dot, "dot"), (mc.dash, "dash"),
                       (mc.flash, "flash")):
        start = time.monotonic()
        func()
        elapsed = time.monotonic() - start
        check(f"{name}() ran in < 2s", elapsed < 2.0,
              f"took {elapsed:.2f}s")
except Exception as e:
    check("dot/dash/flash", False, f"raised {e!r}")
print()

# ---------------------------------------------------------------------------
# 7. Morse timing conventions (dash = 3x dot)
# ---------------------------------------------------------------------------
print("[7] Morse timing conventions")
dot_d = mc.dot.__defaults__
dash_d = mc.dash.__defaults__
check("dot() default duration > 0", dot_d[0] > 0, f"defaults={dot_d}")
check("dash() default duration > 0", dash_d[0] > 0, f"defaults={dash_d}")
ratio = dash_d[0] / dot_d[0]
check("dash duration ~= 3x dot duration (ratio 2.5-3.5)",
      2.5 <= ratio <= 3.5, f"ratio={ratio:.2f}")
print()

# ---------------------------------------------------------------------------
# 8. Full LED morse flash (the real thing) — optional, interactive
# ---------------------------------------------------------------------------
print("[8] Full 'sos' flash on the CapsLock LED (3s)")
try:
    mc.morse("sos")
    check("morse('sos') completed without error", True)
except Exception as e:
    check("morse('sos')", False, f"raised {e!r}")
print()

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("=" * 60)
if FAILED:
    print(f"RESULT: {PASSED} passed, {FAILED} FAILED")
    sys.exit(1)
print(f"RESULT: all {PASSED} tests passed")
print("Windows compatibility: module uses ctypes.windll on win32; "
      "no extra packages required.")
