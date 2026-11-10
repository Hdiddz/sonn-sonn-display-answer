"""Demo: flash a message in Morse code on your CapsLock LED.

Usage:
    python3 demo.py               # flashes "hello world"
    python3 demo.py sos           # flashes "sos"
    python3 demo.py "good morning" --num    # use the NumLock LED

Windows:
    py demo.py "your message"
"""

import sys

import capslockmorsecode as mc


def to_morse(text):
    words = []
    for word in text.upper().split(" "):
        words.append("/".join(mc.MORSE_CODE[c] for c in word if c in mc.MORSE_CODE))
    return " ".join(words)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    key = "num" if "--num" in sys.argv else "caps"

    message = " ".join(args) if args else "hello world"

    print(f"Flashing {message!r} in Morse code on the {key.upper()} lock LED...")
    print("(Press Ctrl+C to stop early.)")

    morse = to_morse(message)
    print(f"Morse: {morse}")
    print("Legend: . = dot   - = dash   / = letter gap   (space) = word gap")
    print()

    try:
        mc.morse(message, key=key)
    except KeyboardInterrupt:
        print("\nStopped.")
        return

    print("Done!")


if __name__ == "__main__":
    main()
