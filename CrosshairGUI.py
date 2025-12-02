import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QColorDialog, QGroupBox, QGridLayout,
    QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor

# Globálne nastavenia
CONFIG = {
    "color": QColor(255, 255, 255),
    "arm_length": 12,
    "arm_thickness": 2,
    "gap": 4,
    "toggle_key": "f12",
    "offset_x": 0,
    "offset_y": 0,
}

# === Overlay ===
class CrosshairOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFixedSize(200, 200)
        self.update_geometry()
        self.hide()

    def update_geometry(self):
        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        center_x = geo.center().x() + CONFIG["offset_x"]
        center_y = geo.center().y() + CONFIG["offset_y"]

        size = 2 * (CONFIG["arm_length"] + CONFIG["gap"] + CONFIG["arm_thickness"])
        if size % 2:
            size += 1
        self.setFixedSize(size, size)
        self.move(center_x - size // 2, center_y - size // 2)

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QBrush
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        c = CONFIG["color"]
        al = CONFIG["arm_length"]
        th = CONFIG["arm_thickness"]
        gap = CONFIG["gap"]
        center = self.width() // 2
        half = th // 2

        painter.setBrush(QBrush(c))

        # Ľavý
        painter.drawRect(center - gap - al, center - half, al, th)
        # ✅ Pravý +1 px doprava
        painter.drawRect(center + gap + 1, center - half, al, th)
        # Horný
        painter.drawRect(center - half, center - gap - al, th, al)
        # Dolný
        painter.drawRect(center - half, center + gap +1, th, al)

    def refresh(self):
        self.update_geometry()
        self.update()
        if self.isVisible():
            self.raise_()


# === Globálny hotkey pomocou pynput (BEZPEČNÝ) ===
from pynput import keyboard as pkeyboard

from pynput import keyboard as pkeyboard

class HotkeyManager:
    def __init__(self, toggle_callback):
        self.toggle_callback = toggle_callback
        self.listener = None
        self.current_key = "f12"
        self.start("f12")

    def start(self, key_name):
        self.stop()
        self.current_key = key_name.lower().strip()

        def on_press(key):
            try:
                # Pre písmená/čísla: key.char (napr. 'c')
                if hasattr(key, 'char') and key.char == self.current_key:
                    self.toggle_callback()
                    return  # zabráni viacnásobnému spusteniu pri dlhom stlačení
                # Pre špeciálne klávesy: key == Key.XXX
                key_map = {
                    'f12': pkeyboard.Key.f12,
                    'f11': pkeyboard.Key.f11,
                    'f10': pkeyboard.Key.f10,
                    'insert': pkeyboard.Key.insert,
                    'c': 'c',  # už ošetrené vyššie cez char
                }
                target = key_map.get(self.current_key)
                if target and key == target:
                    self.toggle_callback()
            except Exception as e:
                print(f"[Debug] On press error: {e}")

        try:
            self.listener = pkeyboard.Listener(on_press=on_press)
            self.listener.start()
        except Exception as e:
            print(f"[Hotkey] Nepodarilo sa spustiť listener: {e}")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None


# === GUI ===
class SettingsPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom Crosshair Designer v2.7.8")
        self.resize(440, 640)

        self.overlay = CrosshairOverlay()
        self.hotkey_mgr = HotkeyManager(self.toggle_overlay_silent)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Farba
        color_group = QGroupBox("🎨 Farba")
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(40, 40)
        self.color_preview.setStyleSheet("border:1px solid #555; background:#fff;")
        self.color_hex = QLineEdit("#67FF26")
        self.color_hex.setMaxLength(7)
        self.color_hex.setInputMask(">Hhhhhh")
        self.color_hex.textChanged.connect(self.on_hex_change)
        btn_pick = QPushButton("Vybrať...")
        btn_pick.clicked.connect(self.pick_color_safe)  # ✅ bezpečný picker

        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_hex)
        color_layout.addWidget(btn_pick)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # === Parametre ===
        params_group = QGroupBox("⚙️ Parametre crosshairu")
        grid = QGridLayout()

        row = 0  # ✅ Explicitný riadkový čítač

        def add_slider(name, min_v, max_v, default, callback):
            nonlocal row
            lbl = QLabel(f"{name}: {default}")
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_v, max_v)
            slider.setValue(default)
            slider.valueChanged.connect(
                lambda v: (lbl.setText(f"{name}: {v}"), callback(v))
            )
            grid.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(slider, row, 1)
            row += 1

        add_slider("Dĺžka ramien", 1, 30, CONFIG["arm_length"],
                   lambda v: self.update("arm_length", v))
        add_slider("Hrúbka", 1, 10, CONFIG["arm_thickness"],
                   lambda v: self.update("arm_thickness", v))
        add_slider("Medzera (vnútorná veľkosť)", 0, 20, CONFIG["gap"],
                   lambda v: self.update("gap", v))

        params_group.setLayout(grid)
        layout.addWidget(params_group)

        # === Klávesa pre toggle ===
        key_group = QGroupBox("⌨️ Klávesa pre toggle")
        key_layout = QHBoxLayout()
        self.key_combo = QComboBox()
        self.key_combo.addItems(["f12", "f11", "f10", "insert", "c"])
        self.key_combo.setCurrentText(CONFIG["toggle_key"])
        self.key_combo.currentTextChanged.connect(self.on_key_change)
        key_layout.addWidget(QLabel("Stlačiť:"))
        key_layout.addWidget(self.key_combo)
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)

        # Rozšírený zoznam vrátane písmen a čísel
        keys = [
            "f9", "f10", "f11", "f12", "insert"
        ]
        # Tlačidlá
        btn_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("👁️ Zobraziť/Skryť")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self.toggle_overlay)
        btn_test = QPushButton("🧪 Test (2s)")
        btn_test.clicked.connect(self.test_overlay)
        btn_layout.addWidget(self.btn_toggle)
        btn_layout.addWidget(btn_test)
        layout.addLayout(btn_layout)

        # Joystick
        move_group = QGroupBox("Posun (px)")
        mg = QGridLayout()
        def move(dx, dy):
            CONFIG["offset_x"] += dx
            CONFIG["offset_y"] += dy
            self.overlay.refresh()
            self.lbl_pos.setText(f"X: {CONFIG['offset_x']}, Y: {CONFIG['offset_y']}")

        btn_up = QPushButton("UP"); btn_up.clicked.connect(lambda: move(0, -1))
        btn_down = QPushButton("DOWN"); btn_down.clicked.connect(lambda: move(0, +1))
        btn_left = QPushButton("LEFT"); btn_left.clicked.connect(lambda: move(-1, 0))
        btn_right = QPushButton("RIGHT"); btn_right.clicked.connect(lambda: move(+1, 0))
        self.lbl_pos = QLabel("X: 0, Y: 0"); self.lbl_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mg.addWidget(btn_up, 0, 1)
        mg.addWidget(btn_left, 1, 0)
        mg.addWidget(self.lbl_pos, 1, 1)
        mg.addWidget(btn_right, 1, 2)
        mg.addWidget(btn_down, 2, 1)
        move_group.setLayout(mg)
        layout.addWidget(move_group)

        # Reset
        btn_reset = QPushButton("↩️ Reset pozície")
        btn_reset.clicked.connect(self.reset_position)
        layout.addWidget(btn_reset)

        # Info
        info = QLabel(
            "Simple usage"
            "No admin required to start<br>"
            "official released version</small>"
        )
        info.setWordWrap(True); info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Inicializácia
        self.update_color_preview()
        self.hotkey_mgr.start(CONFIG["toggle_key"])

    def pick_color_safe(self):
        # Použi nepodvláknuvý mód (Qt.Dialog) pre väčšiu stabilitu
        dialog = QColorDialog(CONFIG["color"], self)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        if dialog.exec():
            CONFIG["color"] = dialog.selectedColor()
            self.update_color_preview()

    def update_color_preview(self):
        c = CONFIG["color"]
        hex_code = c.name().upper()
        self.color_hex.setText(hex_code)
        self.color_preview.setStyleSheet(f"background: {hex_code}; border:1px solid #555;")
        self.overlay.refresh()

    def on_hex_change(self, text):
        if len(text) == 7 and text[0] == '#':
            try:
                c = QColor(text)
                if c.isValid():
                    CONFIG["color"] = c
                    self.overlay.refresh()
                    self.color_preview.setStyleSheet(f"background: {text}; border:1px solid #555;")
            except:
                pass

    def update(self, key, value):
        CONFIG[key] = value
        self.overlay.refresh()

    def on_key_change(self, key):
        CONFIG["toggle_key"] = key
        self.hotkey_mgr.start(key)  # ✅ reštartuje listener s novou klávesou

    def toggle_overlay(self):
        self.overlay.setVisible(not self.overlay.isVisible())
        self.btn_toggle.setChecked(self.overlay.isVisible())

    def toggle_overlay_silent(self):
        # Volané z globálneho hotkeyu (pynput beží v inom vlákne → musíme ísť cez Qt)
        QTimer.singleShot(0, self.toggle_overlay)

    def test_overlay(self):
        self.overlay.show(); self.btn_toggle.setChecked(True)
        QTimer.singleShot(2000, lambda: (self.overlay.hide(), self.btn_toggle.setChecked(False)))

    def reset_position(self):
        CONFIG["offset_x"] = CONFIG["offset_y"] = 0
        self.lbl_pos.setText("X: 0, Y: 0")
        self.overlay.refresh()

    def closeEvent(self, event):
        self.hotkey_mgr.stop()
        self.overlay.close()
        event.accept()


# ===== HLAVNÝ PROGRAM =====
if __name__ == "__main__":
    # Nainštaluj pynput, ak chýba: pip install pynput
    try:
        import pynput
    except ImportError:
        print("❌ Chýba 'pynput'. Nainštaluj: pip install pynput")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # stabilnejší vzhľad

    win = SettingsPanel()
    win.show()
    sys.exit(app.exec())
