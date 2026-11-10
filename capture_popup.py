"""A compact, silent answer popup that never activates its window.

Two layouts: `compact` for multiple-choice answers (small fixed box) and
`paragraph` for written answers, where the box grows to fit the whole text.
"""
import argparse
import ctypes
from ctypes import wintypes as w
import os
import sys
import textwrap


def show_popup(title='Answer: C', duration_ms=2000, *, detail='', preview=False,
               corner='bottom-left', scale=100, layout='compact', on_show=None):
    if sys.platform != 'win32':
        return
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    pointer = ctypes.c_void_p
    result_type = ctypes.c_ssize_t
    callback_type = ctypes.WINFUNCTYPE(result_type, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

    class WindowClass(ctypes.Structure):
        _fields_ = [('style', w.UINT), ('procedure', callback_type),
                    ('class_extra', ctypes.c_int), ('window_extra', ctypes.c_int),
                    ('instance', w.HINSTANCE), ('icon', w.HICON),
                    ('cursor', w.HANDLE), ('background', w.HBRUSH),
                    ('menu_name', w.LPCWSTR), ('class_name', w.LPCWSTR)]

    def bind(library, name, result, *arguments):
        function = getattr(library, name)
        function.restype = result
        function.argtypes = list(arguments)
        return function

    create = bind(user32, 'CreateWindowExW', w.HWND, w.DWORD, w.LPCWSTR,
                  w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                  ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, pointer)
    default = bind(user32, 'DefWindowProcW', result_type, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    register = bind(user32, 'RegisterClassW', w.ATOM, ctypes.POINTER(WindowClass))
    destroy = bind(user32, 'DestroyWindow', w.BOOL, w.HWND)
    quit_loop = bind(user32, 'PostQuitMessage', None, ctypes.c_int)
    set_timer = bind(user32, 'SetTimer', ctypes.c_size_t, w.HWND, ctypes.c_size_t, w.UINT, pointer)
    kill_timer = bind(user32, 'KillTimer', w.BOOL, w.HWND, ctypes.c_size_t)
    get_message = bind(user32, 'GetMessageW', w.BOOL, ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT)
    translate = bind(user32, 'TranslateMessage', w.BOOL, ctypes.POINTER(w.MSG))
    dispatch = bind(user32, 'DispatchMessageW', result_type, ctypes.POINTER(w.MSG))
    position = bind(user32, 'SetWindowPos', w.BOOL, w.HWND, w.HWND,
                    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.UINT)
    system_metrics = bind(user32, 'SystemParametersInfoW', w.BOOL, w.UINT,
                          w.UINT, pointer, w.UINT)
    send = bind(user32, 'SendMessageW', result_type, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
    draw_text = bind(user32, 'DrawTextW', ctypes.c_int, w.HDC, w.LPCWSTR,
                     ctypes.c_int, ctypes.POINTER(w.RECT), w.UINT)
    instance = bind(kernel32, 'GetModuleHandleW', w.HMODULE, w.LPCWSTR)(None)
    brush = bind(gdi32, 'CreateSolidBrush', w.HBRUSH, w.DWORD)(0xF5F5F5)
    delete_object = bind(gdi32, 'DeleteObject', w.BOOL, w.HANDLE)
    set_text_color = bind(gdi32, 'SetTextColor', w.DWORD, w.HDC, w.DWORD)
    set_background_mode = bind(gdi32, 'SetBkMode', ctypes.c_int, w.HDC, ctypes.c_int)
    create_font = bind(gdi32, 'CreateFontW', w.HFONT,
                       *([ctypes.c_int] * 5), *([w.DWORD] * 8), w.LPCWSTR)
    create_dc = bind(gdi32, 'CreateCompatibleDC', w.HDC, w.HDC)
    select_object = bind(gdi32, 'SelectObject', w.HGDIOBJ, w.HDC, w.HGDIOBJ)
    delete_dc = bind(gdi32, 'DeleteDC', w.BOOL, w.HDC)
    text_colors = {}

    @callback_type
    def procedure(hwnd, message, wp, lp):
        if message == 0x138:  # WM_CTLCOLORSTATIC
            set_text_color(wp, text_colors.get(lp, 0x111111))
            set_background_mode(wp, 1)  # TRANSPARENT
            return brush
        if message == 0x113:  # WM_TIMER
            kill_timer(hwnd, 1)
            destroy(hwnd)
            return 0
        if message == 0x2:  # WM_DESTROY
            quit_loop(0)
            return 0
        if message == 0x21:  # WM_MOUSEACTIVATE
            return 3  # MA_NOACTIVATE
        return default(hwnd, message, wp, lp)

    def measure(text, font, width):
        """Height in pixels that `text` needs at `width` (word wrapped)."""
        dc = create_dc(None)
        previous = select_object(dc, font)
        rect = w.RECT(0, 0, max(20, width), 0)
        draw_text(dc, text, -1, ctypes.byref(rect), 0x0400 | 0x0010 | 0x0800)
        select_object(dc, previous)
        delete_dc(dc)
        return max(1, rect.bottom)

    class_name = f'CaptureStatus_{os.getpid()}'
    definition = WindowClass(0, procedure, 0, 0, instance, None, None, brush, None, class_name)
    if not register(ctypes.byref(definition)):
        raise ctypes.WinError(ctypes.get_last_error())

    factor = max(0.5, min(2.0, float(scale) / 100.0))
    fonts = []

    def make_font(size):
        handle = create_font(-size, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, 'Segoe UI')
        fonts.append(handle)
        return handle

    # Usable desktop first: paragraph layout is capped to its height.
    work = w.RECT(0, 0, 0, 0)
    if not system_metrics(0x0030, 0, ctypes.byref(work), 0):  # SPI_GETWORKAREA
        work = w.RECT(0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    span_x = work.right - work.left
    span_y = work.bottom - work.top

    if layout == 'paragraph':
        width = max(220, int(round(360 * factor)))
        pad = max(6, int(round(10 * factor)))
        title_size = max(9, int(round(13 * factor)))
        detail_size = max(9, int(round(10 * factor)))
        title_height = title_size + max(4, int(round(8 * factor)))
        align = 0x0  # SS_LEFT
        inner = width - 2 * pad
        text = ' '.join(detail.split())
        limit = int(span_y * 0.72)
        title_font = make_font(title_size)
        detail_font = None
        text_height = 0
        for size in range(detail_size, 6, -1):
            candidate = make_font(size)
            needed = measure(text, candidate, inner)
            if pad + title_height + needed + pad <= limit:
                detail_font, text_height = candidate, needed
                break
        if detail_font is None:
            detail_font = make_font(7)
            words = text.split()
            while words and (pad + title_height
                             + measure(' '.join(words) + ' …', detail_font, inner)
                             + pad) > limit:
                words.pop()
            text = ' '.join(words) + ' …'
            text_height = measure(text, detail_font, inner)
        detail = text
        height = pad + title_height + text_height + pad
        title_top = pad
        detail_top = pad + title_height
        detail_height = text_height + 2
    else:
        width = max(64, int(round(104 * factor)))
        height = max(36, int(round(58 * factor)))
        pad = max(2, int(round(3 * factor)))
        title_top = max(2, int(round(4 * factor)))
        title_height = max(14, int(round(22 * factor)))
        detail_top = max(title_top + title_height, int(round(26 * factor)))
        detail_height = max(14, int(round(26 * factor)))
        title_size = max(9, int(round((17 if len(title) <= 10 else 12) * factor)))
        detail_size = max(7, int(round(9 * factor)))
        wrap = max(8, int(round(18 * factor)))
        detail = textwrap.fill(' '.join(detail.split()), width=wrap,
                               max_lines=2, placeholder='…')
        align = 0x1  # SS_CENTER
        title_font = make_font(title_size)
        detail_font = make_font(detail_size)

    margin = max(4, int(round(8 * factor)))
    # TOPMOST | NOACTIVATE | TRANSPARENT; TOOLWINDOW hides the popup from Alt+Tab.
    extended_style = 0x8 if preview else (0x08000000 | 0x8 | 0x20 | 0x80)
    window_style = 0x00CF0000 if preview else 0x80000000
    outer = w.RECT(0, 0, width, height)
    bind(user32, 'AdjustWindowRectEx', w.BOOL, ctypes.POINTER(w.RECT), w.DWORD,
         w.BOOL, w.DWORD)(ctypes.byref(outer), window_style, False, extended_style)
    outer_width = outer.right - outer.left
    outer_height = outer.bottom - outer.top

    if corner == 'top-left':
        x, y = work.left + margin, work.top + margin
    elif corner == 'top-right':
        x, y = work.right - outer_width - margin, work.top + margin
    elif corner == 'center':
        x = work.left + max(0, (span_x - outer_width) // 2)
        y = work.top + max(0, (span_y - outer_height) // 2)
    elif corner == 'bottom-right':
        x, y = work.right - outer_width - margin, work.bottom - outer_height - margin
    else:  # bottom-left is the default
        x, y = work.left + margin, work.bottom - outer_height - margin

    hwnd = create(extended_style, class_name, 'Question Answer',
                  window_style, x, y, outer_width, outer_height,
                  None, None, instance, None)
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        for text, top, control_height, font, color in (
                (title, title_top, title_height, title_font, 0x111111),
                (detail, detail_top, detail_height, detail_font, 0x5C3400)):
            label = create(0, 'STATIC', text, 0x40000000 | 0x10000000 | 0x80 | align,
                           pad, top, width - 2 * pad, control_height,
                           hwnd, None, instance, None)
            if not label:
                raise ctypes.WinError(ctypes.get_last_error())
            text_colors[label] = color
            send(label, 0x30, font, 1)  # WM_SETFONT
        # Show directly with SWP_NOACTIVATE; no GUI toolkit can request focus afterward.
        if not position(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, 0x53):
            raise ctypes.WinError(ctypes.get_last_error())
        if not set_timer(hwnd, 1, max(1, duration_ms), None):
            raise ctypes.WinError(ctypes.get_last_error())
        if on_show:
            on_show(hwnd)
        message = w.MSG()
        while True:
            status = get_message(ctypes.byref(message), None, 0, 0)
            if status == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            if status == 0:
                break
            translate(ctypes.byref(message))
            dispatch(ctypes.byref(message))
    finally:
        destroy(hwnd)
        for font in fonts:
            delete_object(font)
        bind(user32, 'UnregisterClassW', w.BOOL, w.LPCWSTR, w.HINSTANCE)(class_name, instance)
        delete_object(brush)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--title', default='Answer: C')
    parser.add_argument('--detail', default='')
    parser.add_argument('--duration-ms', type=int, default=2000)
    parser.add_argument('--corner', default='bottom-left',
                        choices=['bottom-left', 'bottom-right', 'top-left',
                                 'top-right', 'center'])
    parser.add_argument('--scale', type=int, default=100)
    parser.add_argument('--layout', default='compact',
                        choices=['compact', 'paragraph'])
    parser.add_argument('--preview', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    show_popup(args.title, args.duration_ms, detail=args.detail,
               preview=args.preview, corner=args.corner, scale=args.scale,
               layout=args.layout)
    return 0


if __name__ == '__main__':
    sys.exit(main())
