import sys
import ctypes
import ctypes.wintypes
from pathlib import Path
import json
import time
from threading import Thread
import win32gui
import win32con
import win32api
import win32ui

# =======================
# STEALTH CONFIG
# =======================
CONFIG = {
    "color": (103, 255, 38),  # RGB namiesto QColor
    "arm_length": 12,
    "arm_thickness": 2,
    "gap": 4,
    "offset_x": 0,
    "offset_y": 0,
    "enabled": False,
    "toggle_key": 0x43,  # 'C' VK code
}

SLOTS_DIR = Path("C:/krosherG")
SLOTS_FILE = SLOTS_DIR / "slots.json"

# Windows API constants
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x00000008
GCL_HBRBACKGROUND = -10
WS_EX_NOACTIVATE = 0x08000000

class StealthCrosshair:
    def __init__(self):
        self.hwnd = None
        self.enabled = False
        self.running = False
        self.hook_id = None
        
    def create_overlay(self):
        """Vytvorí stealth overlay cez WinAPI"""
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = "CrosshairOverlay"
        wc.lpfnWndProc = self.wnd_proc
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.hbrBackground = win32gui.GetStockObject(win32con.NULL_BRUSH)
        class_atom = win32gui.RegisterClass(wc)
        
        # Stealth window flags
        style = 0
        ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE
        
        # Centrálna pozícia
        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        size = 2 * (CONFIG["arm_length"] + CONFIG["gap"] + CONFIG["arm_thickness"])
        if size % 2: size += 1
        x = (screen_w - size) // 2 + CONFIG["offset_x"]
        y = (screen_h - size) // 2 + CONFIG["offset_y"]
        
        self.hwnd = win32gui.CreateWindowEx(
            ex_style, class_atom, "Overlay", style,
            x, y, size, size, 0, 0, wc.hInstance, None
        )
        
        # Nastav vrstvu (50% priehľadnosť)
        win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 128, win32con.LWA_ALPHA)
        self.update_crosshair()
        
    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_PAINT:
            self.paint_crosshair()
            return 0
        elif msg == win32con.WM_DESTROY:
            self.running = False
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
    
    def paint_crosshair(self):
        """Nakreslí crosshair priamo do DC"""
        if not self.hwnd:
            return
            
        hdc = win32gui.BeginPaint(self.hwnd)[1]
        mem_dc = win32ui.CreateDCFromHandle(hdc)
        mem_dc_patBlt = win32ui.CreateDCFromHandle(hdc)
        
        # Vyčisti priehľadne
        rect = win32gui.GetClientRect(self.hwnd)
        mem_dc.FillRect(rect, win32gui.CreateSolidBrush(0))
        
        # Crosshair geometria
        center = (rect[2] // 2, rect[3] // 2)
        al, th, gap = CONFIG["arm_length"], CONFIG["arm_thickness"], CONFIG["gap"]
        r, g, b = CONFIG["color"]
        
        brush = win32gui.CreateSolidBrush(win32api.RGB(r, g, b))
        old_brush = win32gui.SelectObject(mem_dc.GetSafeHdc(), brush)
        
        half = th // 2
        
        # 4 ramená (stealth rects)
        win32gui.Rectangle(mem_dc.GetSafeHdc(), 
            center[0]-gap-al, center[1]-half, center[0]-gap, center[1]+half)
        win32gui.Rectangle(mem_dc.GetSafeHdc(), 
            center[0]+gap, center[1]-half, center[0]+gap+al, center[1]+half)
        win32gui.Rectangle(mem_dc.GetSafeHdc(), 
            center[0]-half, center[1]-gap-al, center[0]+half, center[1]-gap)
        win32gui.Rectangle(mem_dc.GetSafeHdc(), 
            center[0]-half, center[1]+gap, center[0]+half, center[1]+gap+al)
        
        win32gui.SelectObject(mem_dc.GetSafeHdc(), old_brush)
        win32gui.DeleteObject(brush)
        win32gui.EndPaint(self.hwnd, None)
    
    def update_crosshair(self):
        """Refresh pozície + redraw"""
        if not self.hwnd:
            return
            
        screen_w = win32api.GetSystemMetrics(0)
        screen_h = win32api.GetSystemMetrics(1)
        size = 2 * (CONFIG["arm_length"] + CONFIG["gap"] + CONFIG["arm_thickness"])
        if size % 2: size += 1
        x = (screen_w - size) // 2 + CONFIG["offset_x"]
        y = (screen_h - size) // 2 + CONFIG["offset_y"]
        
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 
                            x, y, size, size, 
                            win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW)
        win32gui.InvalidateRect(self.hwnd, None, True)
    
    def toggle(self):
        """Stealth toggle"""
        self.enabled = not self.enabled
        if self.enabled:
            if not self.hwnd:
                self.create_overlay()
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNA)
        else:
            if self.hwnd:
                win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
    
    def cleanup(self):
        """Čistenie"""
        if self.hwnd:
            win32gui.DestroyWindow(self.hwnd)
            self.hwnd = None
        if self.hook_id:
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook_id)

# Low-level keyboard hook (bez pynput!)
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

HOOKPROC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)
LowLevelKeyboardProc = HOOKPROC(lambda nCode, wParam, lParam: 
    globals()['hook_callback'](nCode, wParam, lParam))

def hook_callback(nCode, wParam, lParam):
    if nCode >= 0 and wParam == 0x0100:  # WM_KEYDOWN
        vk_code = ctypes.windll.user32.GetAsyncKeyState(0x43)  # VK_C
        if vk_code & 0x8000:
            crosshair.toggle()
            time.sleep(0.1)  # Debounce
    return user32.CallNextHookEx(globals()['hook_id'], nCode, wParam, lParam)

# =======================
# GUI (minimal, bez PyQt)
# =======================
def simple_gui():
    """Text-based stealth GUI"""
    print("=== STEALTH CROSSHAIR v3.0 ===")
    print("C = Toggle | ESC = Exit")
    
    global crosshair, hook_id
    crosshair = StealthCrosshair()
    
    # Spusti hook
    hook_id = user32.SetWindowsHookExW(13, LowLevelKeyboardProc, 
                                     kernel32.GetModuleHandleW(None), 0)
    
    msg = ctypes.wintypes.MSG()
    while True:
        if user32.GetMessageW(ctypes.byref(msg), None, 0, 0) <= 0:
            break
        
        # Check ESC
        if win32api.GetAsyncKeyState(0x1B) & 0x8000:  # VK_ESCAPE
            break
            
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    
    crosshair.cleanup()
    user32.UnhookWindowsHookEx(hook_id)

# =======================
# SLOTS (zachované)
# =======================
def load_slots():
    SLOTS_DIR.mkdir(exist_ok=True)
    if SLOTS_FILE.exists():
        try:
            with open(SLOTS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_slots(slots):
    SLOTS_DIR.mkdir(exist_ok=True)
    with open(SLOTS_FILE, 'w') as f:
        json.dump(slots, f, indent=2)

if __name__ == "__main__":
    simple_gui()
