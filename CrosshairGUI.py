import sys
import os
import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QPushButton, QColorDialog, QGroupBox, QGridLayout,
    QComboBox, QLineEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QPixmap, QPainter, QBrush

# =======================
# CONFIG + TRVALÉ ÚDAJE
# =======================
CONFIG = {
    "color": QColor("#67FF26"),  # ✅ default zelená
    "arm_length": 12,
    "arm_thickness": 2,
    "gap": 4,
    "toggle_key": "c",
    "offset_x": 0,
    "offset_y": 0,
}

# ✅ Cesta podľa tvojej požiadavky
SLOTS_DIR = Path("C:/krosherG")
SLOTS_FILE = SLOTS_DIR / "crosshair_slots.json"

# =======================
# CrosshairOverlay
# =======================
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
        # Pravý
        painter.drawRect(center + gap, center - half, al, th)
        # Horný
        painter.drawRect(center - half, center - gap - al, th, al)
        # Dolný
        painter.drawRect(center - half, center + gap, th, al)

    def refresh(self):
        self.update_geometry()
        self.update()
        if self.isVisible():
            self.raise_()


# =======================
# Náhľad crosshairu pre sloty
# =======================
class CrosshairPreviewWidget(QLabel):
    def __init__(self, config, size=80):
        super().__init__()
        self.config = config.copy()
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_preview()

    def update_preview(self, new_config=None):
        if new_config:
            self.config = new_config.copy()
        self.setPixmap(self._render_pixmap())

    def _render_pixmap(self):
        size = self.width()
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        c = QColor(self.config["color"])
        al = int(self.config["arm_length"] * 0.6)
        th = max(1, int(self.config["arm_thickness"] * 0.8))
        gap = int(self.config["gap"] * 0.6)
        center = size // 2
        half = th // 2

        painter.setBrush(QBrush(c))

        painter.drawRect(center - gap - al, center - half, al, th)  # Ľ
        painter.drawRect(center + gap, center - half, al, th)         # P
        painter.drawRect(center - half, center - gap - al, th, al)    # H
        painter.drawRect(center - half, center + gap, th, al)         # D

        painter.end()
        return pixmap


# =======================
# HotkeyManager (pynput)
# =======================
try:
    from pynput import keyboard as pkeyboard
except ImportError:
    pkeyboard = None

class HotkeyManager:
    def __init__(self, toggle_callback):
        self.toggle_callback = toggle_callback
        self.listener = None
        self.current_key = "f12"
        if pkeyboard:
            self.start("f12")

    def start(self, key_name):
        self.stop()
        self.current_key = key_name.lower().strip()
        if not pkeyboard:
            return

        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char == self.current_key:
                    self.toggle_callback()
                    return
                key_map = {
                    'f12': pkeyboard.Key.f12,
                    'f11': pkeyboard.Key.f11,
                    'f10': pkeyboard.Key.f10,
                    'insert': pkeyboard.Key.insert,
                    'c': 'c',
                }
                target = key_map.get(self.current_key)
                if target and key == target:
                    self.toggle_callback()
            except Exception:
                pass

        try:
            self.listener = pkeyboard.Listener(on_press=on_press)
            self.listener.start()
        except Exception as e:
            print(f"[Hotkey] Chyba: {e}")

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None


# =======================
# GUI: SettingsPanel
# =======================
class SettingsPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom Crosshair Designer v2.8.0")
        self.resize(460, 720)

        self.overlay = CrosshairOverlay()
        self.hotkey_mgr = HotkeyManager(self.toggle_overlay_silent)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ===== Farba =====
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
        btn_pick.clicked.connect(self.pick_color_safe)

        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_hex)
        color_layout.addWidget(btn_pick)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # ===== Parametre =====
        params_group = QGroupBox("⚙️ Parametre crosshairu")
        grid = QGridLayout()
        row = 0

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
        add_slider("Medzera", 0, 20, CONFIG["gap"],
                   lambda v: self.update("gap", v))

        params_group.setLayout(grid)
        layout.addWidget(params_group)

        # ===== Klávesa =====
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

        # ===== Sloty =====
        slots_group = QGroupBox("📁 Uložené profily")
        slots_layout = QVBoxLayout()

        self.slots_list = QListWidget()
        self.slots_list.setFixedHeight(180)
        self.slots_list.itemDoubleClicked.connect(self.load_slot)
        self.slots_list.itemSelectionChanged.connect(self.update_slot_buttons)
        self.slots_list.keyPressEvent = self.slots_key_handler
        slots_layout.addWidget(self.slots_list)

        slots_btn_layout = QHBoxLayout()
        self.btn_save_slot = QPushButton("💾 Uložiť")
        self.btn_save_slot.clicked.connect(self.save_slot)
        self.btn_load_slot = QPushButton("📂 Načítať")
        self.btn_load_slot.setEnabled(False)
        self.btn_load_slot.clicked.connect(self.load_selected_slot)
        self.btn_delete_slot = QPushButton("🗑️")
        self.btn_delete_slot.setFixedWidth(40)
        self.btn_delete_slot.setEnabled(False)
        self.btn_delete_slot.clicked.connect(self.delete_selected_slot)

        slots_btn_layout.addWidget(self.btn_save_slot)
        slots_btn_layout.addWidget(self.btn_load_slot)
        slots_btn_layout.addWidget(self.btn_delete_slot)
        slots_layout.addLayout(slots_btn_layout)

        slots_group.setLayout(slots_layout)
        layout.addWidget(slots_group)

        # ===== Tlačidlá =====
        btn_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("👁️ Zobraziť/Skryť")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.clicked.connect(self.toggle_overlay)
        btn_test = QPushButton("🧪 Test (2s)")
        btn_test.clicked.connect(self.test_overlay)
        btn_layout.addWidget(self.btn_toggle)
        btn_layout.addWidget(btn_test)
        layout.addLayout(btn_layout)

        # ===== Posun (joystick) =====
        move_group = QGroupBox("Posun (px)")
        mg = QGridLayout()
        def move(dx, dy):
            CONFIG["offset_x"] += dx
            CONFIG["offset_y"] += dy
            self.overlay.refresh()
            self.lbl_pos.setText(f"X: {CONFIG['offset_x']}, Y: {CONFIG['offset_y']}")

        btn_up = QPushButton("↑"); btn_up.clicked.connect(lambda: move(0, -1))
        btn_down = QPushButton("↓"); btn_down.clicked.connect(lambda: move(0, +1))
        btn_left = QPushButton("←"); btn_left.clicked.connect(lambda: move(-1, 0))
        btn_right = QPushButton("→"); btn_right.clicked.connect(lambda: move(+1, 0))
        self.lbl_pos = QLabel("X: 0, Y: 0")
        self.lbl_pos.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mg.addWidget(btn_up, 0, 1)
        mg.addWidget(btn_left, 1, 0)
        mg.addWidget(self.lbl_pos, 1, 1)
        mg.addWidget(btn_right, 1, 2)
        mg.addWidget(btn_down, 2, 1)
        move_group.setLayout(mg)
        layout.addWidget(move_group)

        # ===== Reset =====
        btn_reset = QPushButton("↩️ Reset pozície")
        btn_reset.clicked.connect(self.reset_position)
        layout.addWidget(btn_reset)

        # ===== Info =====
        info = QLabel(
            "<small>Simple usage • No admin required • v2.8.0<br>"
            "Sloty sa ukladajú do <code>~/.crosshair_slots.json</code></small>"
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # ===== Štýl =====
        self.setStyleSheet("""
            QMainWindow { background: #2a2a2a; color: white; }
            QGroupBox { font-weight: bold; border: 1px solid #555; margin-top: 1ex; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
            QPushButton { padding: 5px 12px; }
            QListWidget { border: 1px solid #555; background: #1e1e1e; }
            QListWidget::item { padding: 4px; }
            QListWidget::item:selected { background: #005f5f; }
            QLineEdit, QComboBox { background: #333; color: white; border: 1px solid #555; }
        """)

        # ===== Inicializácia =====
        self.update_color_preview()
        self.load_slots()
        self.hotkey_mgr.start(CONFIG["toggle_key"])

    # ===== Sloty =====
    def get_current_config_snapshot(self):
        return {
            "color": CONFIG["color"].name(),
            "arm_length": CONFIG["arm_length"],
            "arm_thickness": CONFIG["arm_thickness"],
            "gap": CONFIG["gap"],
            "toggle_key": CONFIG["toggle_key"],
            "offset_x": CONFIG["offset_x"],
            "offset_y": CONFIG["offset_y"],
        }

    def apply_config_snapshot(self, snap):
        CONFIG["color"] = QColor(snap["color"])
        CONFIG["arm_length"] = snap["arm_length"]
        CONFIG["arm_thickness"] = snap["arm_thickness"]
        CONFIG["gap"] = snap["gap"]
        CONFIG["toggle_key"] = snap["toggle_key"]
        CONFIG["offset_x"] = snap["offset_x"]
        CONFIG["offset_y"] = snap["offset_y"]
        self.update_color_preview()
        self.key_combo.setCurrentText(snap["toggle_key"])
        self.lbl_pos.setText(f"X: {CONFIG['offset_x']}, Y: {CONFIG['offset_y']}")
        self.overlay.refresh()

    def save_slot(self):
        snap = self.get_current_config_snapshot()
        i = 1
        while True:
            name = f"crosshair_{i}"
            if not any(self.slots_list.item(j).data(Qt.ItemDataRole.UserRole).get("name") == name
                       for j in range(self.slots_list.count())):
                break
            i += 1

        self._add_slot_item(name, snap)
        self.save_slots()

    def _add_slot_item(self, name, snap):
        widget = QWidget()
        hlayout = QHBoxLayout(widget)
        hlayout.setContentsMargins(6, 3, 6, 3)

        preview = CrosshairPreviewWidget(snap, size=48)
        label = QLabel(name)
        label.setStyleSheet("font-weight: bold;")

        hlayout.addWidget(preview)
        hlayout.addWidget(label, 1)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, {"name": name, **snap})
        item.setSizeHint(widget.sizeHint())
        self.slots_list.addItem(item)
        self.slots_list.setItemWidget(item, widget)

    def load_slot(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        self.apply_config_snapshot(data)

    def load_selected_slot(self):
        items = self.slots_list.selectedItems()
        if items:
            self.load_slot(items[0])

    def delete_selected_slot(self):
        items = self.slots_list.selectedItems()
        if items:
            row = self.slots_list.row(items[0])
            self.slots_list.takeItem(row)
            self.save_slots()
            self.update_slot_buttons()

    def update_slot_buttons(self):
        has_sel = bool(self.slots_list.selectedItems())
        self.btn_load_slot.setEnabled(has_sel)
        self.btn_delete_slot.setEnabled(has_sel)

    def slots_key_handler(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.load_selected_slot()
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_selected_slot()
        else:
            # Forward to default handler
            QListWidget.keyPressEvent(self.slots_list, event)

    def load_slots(self):
        # ✅ Vytvor priečinok, ak neexistuje
        try:
            SLOTS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[Sloty] Nepodarilo sa vytvoriť priečinok {SLOTS_DIR}: {e}")
            # Pokračuj, len ukladanie bude nefunkčné

        self.slots_list.clear()
        if SLOTS_FILE.exists():
            try:
                with open(SLOTS_FILE, 'r', encoding='utf-8') as f:
                    slots = json.load(f)
                for name, snap in slots.items():
                    self._add_slot_item(name, snap)
            except Exception as e:
                print(f"[Sloty] Chyba pri načítaní {SLOTS_FILE}: {e}")
        # Ak žiadne sloty, vytvor Default
        if self.slots_list.count() == 0:
            default_snap = {
                "color": "#67FF26",
                "arm_length": 12,
                "arm_thickness": 2,
                "gap": 4,
                "toggle_key": "c",
                "offset_x": 0,
                "offset_y": 0,
            }
            self._add_slot_item("Default Green", default_snap)
            self.save_slots()  # teraz už vie ukladať do C:\krosherG\

    def save_slots(self):
        try:
            SLOTS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[Sloty] Nepodarilo sa zabezpečiť priečinok {SLOTS_DIR}: {e}")
            return

        slots = {}
        for i in range(self.slots_list.count()):
            item = self.slots_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            name = data.pop("name")
            slots[name] = data
        try:
            with open(SLOTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(slots, f, indent=2)
            print(f"[✓] Sloty uložené do: {SLOTS_FILE}")
        except Exception as e:
            print(f"[Sloty] Chyba pri ukladaní do {SLOTS_FILE}: {e}")

    # ===== UI Callbacks =====
    def pick_color_safe(self):
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
            c = QColor(text)
            if c.isValid():
                CONFIG["color"] = c
                self.overlay.refresh()
                self.color_preview.setStyleSheet(f"background: {text}; border:1px solid #555;")

    def update(self, key, value):
        CONFIG[key] = value
        self.overlay.refresh()

    def on_key_change(self, key):
        CONFIG["toggle_key"] = key
        self.hotkey_mgr.start(key)

    def toggle_overlay(self):
        self.overlay.setVisible(not self.overlay.isVisible())
        self.btn_toggle.setChecked(self.overlay.isVisible())

    def toggle_overlay_silent(self):
        QTimer.singleShot(0, self.toggle_overlay)

    def test_overlay(self):
        self.overlay.show()
        self.btn_toggle.setChecked(True)
        QTimer.singleShot(2000, lambda: (self.overlay.hide(), self.btn_toggle.setChecked(False)))

    def reset_position(self):
        CONFIG["offset_x"] = CONFIG["offset_y"] = 0
        self.lbl_pos.setText("X: 0, Y: 0")
        self.overlay.refresh()

    def closeEvent(self, event):
        self.hotkey_mgr.stop()
        self.overlay.close()
        self.save_slots()
        event.accept()


# =======================
# MAIN
# =======================
if __name__ == "__main__":
    if not pkeyboard:
        print("❌ Chýba 'pynput'. Nainštaluj: pip install pynput")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = SettingsPanel()
    win.show()
    sys.exit(app.exec())
