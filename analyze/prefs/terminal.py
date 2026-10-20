# Raw keyboard input for the interactive preference editor.
#
# Single keypresses (no Enter) via msvcrt on Windows, with a termios raw-mode
# fallback elsewhere and plain input() as a last resort.
import os
import sys


def read_single_key() -> str:
    # One keypress: instant on Windows (msvcrt); elsewhere it reads a line and
    # returns its first character.
    if sys.platform == 'win32':
        try:
            import msvcrt

            ch = msvcrt.getwch()
            return ch
        except ImportError:
            pass
    raw = input()
    if raw.strip():
        return raw.strip()[:1]
    return ''


def read_key() -> str:
    # Read one logical key. Returns one of:
    # 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'ESC', 'SPACE', or the raw
    # character for printable keys. Empty string for unhandled sequences.
    if sys.platform == 'win32':
        try:
            import msvcrt
        except ImportError:
            raw = input()
            if raw:
                return raw[:1]
            return ''
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            second = msvcrt.getwch()
            return {
                'H': 'UP',
                'P': 'DOWN',
                'K': 'LEFT',
                'M': 'RIGHT',
            }.get(second, '')
        if ch in ('\r', '\n'):
            return 'ENTER'
        if ch == '\x1b':
            return 'ESC'
        if ch == ' ':
            return 'SPACE'
        return ch

    # POSIX fallback: raw tty for arrow escape sequences
    try:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                nxt = sys.stdin.read(2)
                if nxt == '[A':
                    return 'UP'
                if nxt == '[B':
                    return 'DOWN'
                if nxt == '[C':
                    return 'RIGHT'
                if nxt == '[D':
                    return 'LEFT'
                return 'ESC'
            if ch in ('\r', '\n'):
                return 'ENTER'
            if ch == ' ':
                return 'SPACE'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        raw = input()
        if raw:
            return raw[:1]
        return ''


def clear_screen() -> None:
    # Clear the terminal — used between arrow-key reorder redraws.
    if sys.platform == 'win32':
        os.system('cls')
    else:
        os.system('clear')
