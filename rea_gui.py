#!/usr/bin/env python3
"""
rea_gui.py — Desktop GUI for REA (Reverse Engineering Anything)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Light-themed, modern PyQt5 desktop interface integrated with Electra AI Center:
  • Prominent Binary Browser & Drag-and-Drop Loader
  • Quick Action Bar (Inspect, Disassemble, Decompile, Strings, Security Audit, Auto-Analyze)
  • Analysis Tabs (Overview, Disassembly, Decompiled C, Strings & Symbols, Hex View)
  • Real-Time Live Execution Log with streaming stdout/stderr
  • Interactive Electra AI Copilot with multi-turn chat & reverse engineering prompts
  • Model Selection & API Settings (Defaults to Electra Nano)
"""

import os
import sys
import json
import time
import hashlib
import binascii
import subprocess
import threading
from typing import Optional, List, Dict, Any

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame, QLineEdit,
    QTextEdit, QPlainTextEdit, QScrollArea, QSizePolicy, QDialog,
    QMessageBox, QProgressBar, QSplitter, QTabWidget, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QFileDialog, QMenu, QAction, QGroupBox, QSpinBox, QDoubleSpinBox,
    QShortcut
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QCursor, QPixmap,
    QTextCursor, QTextCharFormat, QKeySequence
)

# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT CONFIGURATION & PATHS
# ─────────────────────────────────────────────────────────────────────────────

def get_rea_bin_path() -> str:
    """Dynamically resolves the path to the rea.bin executable."""
    if os.environ.get("REA_BIN_PATH") and os.path.isfile(os.environ["REA_BIN_PATH"]):
        return os.environ["REA_BIN_PATH"]

    onefile_dir = os.environ.get("NUITKA_ONEFILE_DIRECTORY")
    if onefile_dir:
        cand = os.path.join(onefile_dir, "rea.bin")
        if os.path.isfile(cand):
            try:
                os.chmod(cand, 0o755)
            except Exception:
                pass
            return cand

    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    for name in ("rea.bin", "rea"):
        cand = os.path.join(exe_dir, name)
        if os.path.isfile(cand) and cand != os.path.abspath(sys.argv[0]):
            return cand

    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ("rea.bin", "rea"):
        cand = os.path.join(script_dir, name)
        if os.path.isfile(cand) and cand != os.path.abspath(sys.argv[0]):
            return cand

    known_path = "/home/jacque/AI-center/rea/rea.bin"
    if os.path.isfile(known_path):
        return known_path

    return "rea"

def get_icon_path() -> str:
    """Resolves icon path in standalone onefile mode or development."""
    onefile_dir = os.environ.get("NUITKA_ONEFILE_DIRECTORY")
    if onefile_dir:
        cand = os.path.join(onefile_dir, "ai-icon.png")
        if os.path.isfile(cand):
            return cand
    for p in ("/home/jacque/AI-center/ai-icon.png", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai-icon.png")):
        if os.path.isfile(p):
            return p
    return ""

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REA_BIN_PATH = get_rea_bin_path()
ICON_PATH = get_icon_path()

DEFAULT_SERVER_BASE = "https://makululinux.us:2007"
FALLBACK_SERVER_BASE = "https://api.makululinux.us"
CONFIG_DIR = os.path.expanduser("~/.config/rea")
CONFIG_FILE = os.path.join(CONFIG_DIR, "gui_settings.json")
ELECTRA_AUTH_FILE = os.path.expanduser("~/.config/ai_terminal/electra_auth.json")
ELECTRA_API_KEY_FILE = os.path.expanduser("~/.config/electra/api_key")

AVAILABLE_MODELS = [
    ("electra-nano", "Electra Nano (Default - Fast / Low Latency)"),
    ("electra", "Electra AI (Cloud Flagship)"),
    ("qwen3.8-coder", "Qwen 3.8 Coder (Reverse Engineering & Code Specialist)"),
]


# ─────────────────────────────────────────────────────────────────────────────
#  CREDENTIAL DISCOVERY & SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

def discover_electra_api_key() -> str:
    """Discovers Electra API key from environment, auth file, or config."""
    # 1. Environment variable
    env_key = os.environ.get("ELECTRA_API_KEY", "").strip()
    if env_key:
        return env_key

    # 2. ~/.config/ai_terminal/electra_auth.json
    if os.path.isfile(ELECTRA_AUTH_FILE):
        try:
            with open(ELECTRA_AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("api_key", "").strip()
                if key:
                    return key
        except Exception:
            pass

    # 3. ~/.config/electra/api_key
    if os.path.isfile(ELECTRA_API_KEY_FILE):
        try:
            with open(ELECTRA_API_KEY_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass

    return ""


def load_gui_settings() -> Dict[str, Any]:
    """Loads GUI configuration from disk, defaulting model to electra-nano."""
    default_settings = {
        "server_base": DEFAULT_SERVER_BASE,
        "api_key": discover_electra_api_key(),
        "model": "electra-nano",
        "temperature": 0.3,
        "rea_bin": REA_BIN_PATH,
        "auto_scroll_log": True,
        "token_limit": 4096
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass

    if not default_settings.get("api_key"):
        default_settings["api_key"] = discover_electra_api_key()

    if not default_settings.get("model"):
        default_settings["model"] = "electra-nano"

    return default_settings


def save_gui_settings(settings: Dict[str, Any]) -> None:
    """Persists GUI configuration to disk."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[REA-GUI] Warning: could not save settings: {e}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
#  LIGHT THEME QSS STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────

LIGHT_THEME_QSS = """
/* Global Reset and Light Theme Foundation */
QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Ubuntu", "Helvetica Neue", sans-serif;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

/* Window & Panels */
QMainWindow {
    background-color: #F8FAFC;
}

QFrame[class="card"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

/* Header bar */
#HeaderFrame {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 10px 16px;
}

#AppTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1E293B;
}

#AppSubtitle {
    font-size: 11px;
    font-weight: 500;
    color: #64748B;
}

#BadgePill {
    background-color: #EFF6FF;
    color: #2563EB;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 10px;
    border: 1px solid #BFDBFE;
}

/* Base Buttons */
QPushButton {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
    color: #0F172A;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

/* Primary Vibrant Blue Buttons */
QPushButton[class="primary"], #btn_browse, #btn_hero_browse, #btn_auto_ai, #btn_send, #btn_run_cmd, #btn_save_settings, #btn_close_about {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 600;
}

QPushButton[class="primary"]:hover, #btn_browse:hover, #btn_hero_browse:hover, #btn_auto_ai:hover, #btn_send:hover, #btn_run_cmd:hover, #btn_save_settings:hover, #btn_close_about:hover {
    background-color: #1D4ED8;
    border-color: #1E40AF;
    color: #FFFFFF;
}

QPushButton[class="primary"]:pressed, #btn_browse:pressed, #btn_hero_browse:pressed, #btn_auto_ai:pressed, #btn_send:pressed, #btn_run_cmd:pressed, #btn_save_settings:pressed, #btn_close_about:pressed {
    background-color: #1E40AF;
    color: #FFFFFF;
}

/* Action Toolbar Buttons */
QPushButton[class="action"] {
    background-color: #F8FAFC;
    color: #1E293B;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    text-align: center;
}

QPushButton[class="action"]:hover {
    background-color: #EFF6FF;
    border-color: #93C5FD;
    color: #1D4ED8;
}

/* Quick Chips */
QPushButton[class="chip"] {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
}

QPushButton[class="chip"]:hover {
    background-color: #E0E7FF;
    border-color: #A5B4FC;
    color: #3730A3;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Tabs */
QTabWidget::pane {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-top: none;
    border-radius: 0 0 8px 8px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    padding: 7px 12px;
    font-weight: 600;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    border-bottom: 2px solid #2563EB;
}

QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
    color: #1E293B;
}

/* Dropdown Menu */
QMenu {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

QMenu::separator {
    height: 1px;
    background-color: #E2E8F0;
    margin: 4px 0;
}

/* Code & Log Viewers */
QPlainTextEdit[class="code-view"], QTextEdit[class="code-view"] {
    background-color: #FFFFFF;
    color: #1E293B;
    border: none;
    font-family: "DejaVu Sans Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    line-height: 1.4;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #F1F5F9;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 20px;
}

/* Splitter */
QSplitter::handle {
    background-color: #E2E8F0;
}

QSplitter::handle:horizontal {
    width: 4px;
}

QSplitter::handle:vertical {
    height: 4px;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  BACKGROUND WORKERS (Asynchronous Subprocesses & Network)
# ─────────────────────────────────────────────────────────────────────────────

class ToolExecutionWorker(QThread):
    """Executes a REA CLI command asynchronously and streams stdout/stderr."""
    log_line = pyqtSignal(str, str)     # text, level ('info', 'run', 'success', 'error')
    completed = pyqtSignal(str, str)    # command_id, output_text
    failed = pyqtSignal(str, str)       # command_id, error_message

    def __init__(self, command_id: str, cmd_args: List[str], cwd: Optional[str] = None):
        super().__init__()
        self.command_id = command_id
        self.cmd_args = cmd_args
        self.cwd = cwd or SCRIPT_DIR
        self._process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass

    def run(self):
        cmd_str = " ".join(self.cmd_args)
        self.log_line.emit(f"Running: {cmd_str}", "run")
        start_time = time.time()

        try:
            self._process = subprocess.Popen(
                self.cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.cwd
            )

            output_lines = []
            if self._process.stdout:
                for line in self._process.stdout:
                    if self._is_cancelled:
                        break
                    output_lines.append(line)
                    stripped = line.rstrip()
                    if stripped:
                        self.log_line.emit(stripped, "info")

            self._process.wait()
            ret_code = self._process.returncode

            elapsed = round(time.time() - start_time, 2)
            full_output = "".join(output_lines)

            if ret_code == 0:
                self.log_line.emit(f"Command '{self.command_id}' finished in {elapsed}s (exit code 0)", "success")
                self.completed.emit(self.command_id, full_output)
            else:
                err_text = ""
                if self._process.stderr:
                    err_text = self._process.stderr.read()
                self.log_line.emit(f"Command failed (exit code {ret_code}): {err_text.strip()}", "error")
                self.failed.emit(self.command_id, f"Exit code {ret_code}: {err_text}")

        except Exception as e:
            self.log_line.emit(f"Execution error: {e}", "error")
            self.failed.emit(self.command_id, str(e))


class ElectraAiChatWorker(QThread):
    """Sends requests to Electra AI Center and handles responses."""
    log_line = pyqtSignal(str, str)
    chunk_received = pyqtSignal(str)
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, server_base: str, api_key: str, model: str,
                 messages: List[Dict[str, str]], temperature: float = 0.3):
        super().__init__()
        self.server_base = server_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        import urllib.request
        import urllib.error

        self.log_line.emit(f"Connecting to Electra AI ({self.model}) at {self.server_base}...", "run")
        start_time = time.time()

        url = f"{self.server_base}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "stream": False
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "REA-Desktop-GUI/1.0 (Electra)")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
            req.add_header("x-goog-api-key", self.api_key)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_bytes = resp.read()
                res_json = json.loads(resp_bytes.decode("utf-8"))

                choices = res_json.get("choices", [])
                if choices and "message" in choices[0]:
                    reply = choices[0]["message"].get("content", "")
                else:
                    reply = str(res_json)

                elapsed = round(time.time() - start_time, 2)
                self.log_line.emit(f"Electra AI response received in {elapsed}s", "success")
                self.completed.emit(reply)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            msg = f"HTTP {e.code}: {err_body}"
            self.log_line.emit(f"Electra AI error: {msg}", "error")
            self.failed.emit(msg)
        except Exception as e:
            msg = f"Network failure: {e}"
            self.log_line.emit(f"Electra AI connection error: {msg}", "error")
            self.failed.emit(msg)


# ─────────────────────────────────────────────────────────────────────────────
#  SETTINGS DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """Configuration dialog for API keys, server endpoints, and binary path."""

    def __init__(self, parent=None, settings: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Electra AI & REA Settings")
        self.setMinimumWidth(520)
        self.setStyleSheet(LIGHT_THEME_QSS)

        self.settings = dict(settings or {})
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Application & Provider Settings")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1E293B;")
        layout.addWidget(title)

        desc = QLabel("Configure Electra AI Center connectivity and local reverse engineering engine.")
        desc.setStyleSheet("color: #64748B; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Electra AI Server Group
        grp_ai = QGroupBox("Electra AI Center")
        grp_ai.setStyleSheet("font-weight: 600; color: #1E293B;")
        layout_ai = QVBoxLayout(grp_ai)
        layout_ai.setSpacing(10)

        # Server URL
        layout_ai.addWidget(QLabel("Server Endpoint URL:"))
        self.txt_server = QLineEdit(self.settings.get("server_base", DEFAULT_SERVER_BASE))
        layout_ai.addWidget(self.txt_server)

        # API Key
        layout_ai.addWidget(QLabel("Electra API Key / Token:"))
        key_layout = QHBoxLayout()
        self.txt_key = QLineEdit(self.settings.get("api_key", ""))
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.btn_show_key = QPushButton("Show")
        self.btn_show_key.setFixedWidth(60)
        self.btn_show_key.clicked.connect(self._toggle_show_key)
        key_layout.addWidget(self.txt_key)
        key_layout.addWidget(self.btn_show_key)
        layout_ai.addLayout(key_layout)

        # Test Connection Button
        test_layout = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.clicked.connect(self._test_connection)
        self.lbl_test_result = QLabel("")
        self.lbl_test_result.setStyleSheet("font-size: 11px;")
        test_layout.addWidget(self.btn_test)
        test_layout.addWidget(self.lbl_test_result)
        test_layout.addStretch()
        layout_ai.addLayout(test_layout)

        layout.addWidget(grp_ai)

        # Local Engine Group
        grp_engine = QGroupBox("Local REA Engine")
        grp_engine.setStyleSheet("font-weight: 600; color: #1E293B;")
        layout_engine = QVBoxLayout(grp_engine)
        layout_engine.setSpacing(10)

        layout_engine.addWidget(QLabel("REA Standalone Binary Path:"))
        bin_layout = QHBoxLayout()
        self.txt_bin = QLineEdit(self.settings.get("rea_bin", REA_BIN_PATH))
        btn_browse_bin = QPushButton("Browse...")
        btn_browse_bin.clicked.connect(self._browse_binary)
        bin_layout.addWidget(self.txt_bin)
        bin_layout.addWidget(btn_browse_bin)
        layout_engine.addLayout(bin_layout)

        layout.addWidget(grp_engine)

        # Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("btn_save_settings")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._save_and_close)
        btn_box.addWidget(btn_save)

        layout.addLayout(btn_box)

    def _toggle_show_key(self):
        if self.txt_key.echoMode() == QLineEdit.Password:
            self.txt_key.setEchoMode(QLineEdit.Normal)
            self.btn_show_key.setText("Hide")
        else:
            self.txt_key.setEchoMode(QLineEdit.Password)
            self.btn_show_key.setText("Show")

    def _browse_binary(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select REA Standalone Binary", self.txt_bin.text() or SCRIPT_DIR
        )
        if path:
            self.txt_bin.setText(path)

    def _test_connection(self):
        self.lbl_test_result.setText("Pinging Electra AI...")
        self.lbl_test_result.setStyleSheet("color: #2563EB;")
        QApplication.processEvents()

        server = self.txt_server.text().strip().rstrip("/")
        key = self.txt_key.text().strip()

        def _do_test():
            import urllib.request
            try:
                url = f"{server}/v1/models"
                req = urllib.request.Request(url)
                if key:
                    req.add_header("Authorization", f"Bearer {key}")
                    req.add_header("x-goog-api-key", key)
                with urllib.request.urlopen(req, timeout=5) as r:
                    if r.status in (200, 204):
                        return True, "Connected successfully (HTTP 200)"
                    return False, f"Server responded with status {r.status}"
            except Exception as e:
                return False, f"Failed: {e}"

        ok, msg = _do_test()
        if ok:
            self.lbl_test_result.setText(f"[OK] {msg}")
            self.lbl_test_result.setStyleSheet("color: #10B981; font-weight: 600;")
        else:
            self.lbl_test_result.setText(f"[Failed] {msg}")
            self.lbl_test_result.setStyleSheet("color: #EF4444; font-weight: 500;")

    def _save_and_close(self):
        self.settings["server_base"] = self.txt_server.text().strip()
        self.settings["api_key"] = self.txt_key.text().strip()
        self.settings["rea_bin"] = self.txt_bin.text().strip()
        save_gui_settings(self.settings)
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  ABOUT DIALOG
# ─────────────────────────────────────────────────────────────────────────────

class AboutDialog(QDialog):
    """About dialog highlighting MakuluLinux Rea branding, upstream attribution, and links."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About MakuluLinux Rea")
        self.setFixedWidth(540)
        self.setStyleSheet(LIGHT_THEME_QSS)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header with Logo & Titles
        h_header = QHBoxLayout()
        h_header.setSpacing(14)

        if ICON_PATH and os.path.isfile(ICON_PATH):
            lbl_icon = QLabel()
            pix = QPixmap(ICON_PATH)
            if not pix.isNull():
                lbl_icon.setPixmap(pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                h_header.addWidget(lbl_icon)

        v_titles = QVBoxLayout()
        v_titles.setSpacing(2)

        lbl_app_name = QLabel("MakuluLinux Rea")
        lbl_app_name.setStyleSheet("font-size: 22px; font-weight: 800; color: #1E293B;")
        v_titles.addWidget(lbl_app_name)

        lbl_fork = QLabel("forked from morluto/rea • Engine v6.7.0")
        lbl_fork.setStyleSheet("font-size: 12px; font-style: italic; color: #64748B; font-weight: 500;")
        v_titles.addWidget(lbl_fork)

        h_header.addLayout(v_titles)
        h_header.addStretch()
        layout.addLayout(h_header)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(line)

        # Description
        lbl_desc = QLabel(
            "<b>MakuluLinux Rea (Reverse Engineer Anything)</b> is an intelligent, multi-engine "
            "reverse engineering studio powered by Electra AI Center.<br><br>"
            "Inspect native ELF, PE, Mach-O binaries, Go/Rust runtimes, Unity IL2CPP games, "
            "AI models, GPU code objects, Android APKs, WebAssembly, and bytecode. Disassemble with objdump "
            "and radare2, decompile functions with Ghidra & RetDec, analyze byte entropy, audit security mitigations, "
            "and interact with the real-time Electra AI Copilot."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 13px; color: #334155; line-height: 1.5;")
        layout.addWidget(lbl_desc)

        # Links Card
        grp_links = QFrame()
        grp_links.setProperty("class", "card")
        grp_links.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 14px;"
        )
        v_links = QVBoxLayout(grp_links)
        v_links.setSpacing(10)

        # Website
        lbl_web = QLabel(
            "<b>Website:</b> <a href='https://makululinux.com' style='color: #2563EB; font-weight: 600; text-decoration: none;'>https://makululinux.com</a>"
        )
        lbl_web.setOpenExternalLinks(True)
        lbl_web.setTextInteractionFlags(Qt.TextBrowserInteraction)
        v_links.addWidget(lbl_web)

        # Patreon
        lbl_patreon = QLabel(
            "<b>Patreon:</b> <a href='https://www.patreon.com/makululinux' style='color: #2563EB; font-weight: 600; text-decoration: none;'>https://www.patreon.com/makululinux</a>"
        )
        lbl_patreon.setOpenExternalLinks(True)
        lbl_patreon.setTextInteractionFlags(Qt.TextBrowserInteraction)
        v_links.addWidget(lbl_patreon)

        # Discord
        lbl_discord = QLabel(
            "<b>Discord:</b> <a href='https://discord.gg/UerQvq2hTm' style='color: #2563EB; font-weight: 600; text-decoration: none;'>https://discord.gg/UerQvq2hTm</a>"
        )
        lbl_discord.setOpenExternalLinks(True)
        lbl_discord.setTextInteractionFlags(Qt.TextBrowserInteraction)
        v_links.addWidget(lbl_discord)

        layout.addWidget(grp_links)

        # Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setObjectName("btn_close_about")
        btn_close.setProperty("class", "primary")
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        layout.addLayout(btn_box)


# ─────────────────────────────────────────────────────────────────────────────
#  REA SUBCOMMANDS CATALOG & CUSTOM COMMAND DIALOG
# ─────────────────────────────────────────────────────────────────────────────

REA_ALL_COMMANDS = [
    # Core Binary Analysis & Diagnostics
    ("inspect-with-objdump", "Headers, sections, disassembly, and symbols via GNU objdump"),
    ("analyze-with-radare2", "Functions, basic blocks, control flow graphs, xrefs via Radare2"),
    ("decompile-with-ghidra", "Decompile binary functions into readable C via Ghidra"),
    ("decompile-with-retdec", "Decompile binary functions into high-level C via RetDec"),
    ("decompile-all", "Batch decompile all functions into pseudocode directory"),
    ("inspect-byte-entropy", "Compute Shannon entropy across offsets to find packed/encrypted regions"),
    ("inspect-binary-layout", "Analyze section layout, virtual memory alignment, and address mapping"),
    ("match-native-functions", "Match and compare functions across binaries or signatures"),
    ("instructions", "Read raw machine instructions without decompiling"),
    ("read-bytes", "Read raw memory bytes at an analysis address"),
    ("search-bytes", "Search for masked byte patterns in initialized memory"),
    ("search", "Search all analyzed strings and procedure names"),
    ("xrefs", "List references and cross-references to an address"),

    # Windows PE Analysis
    ("inspect-pe-headers", "Windows PE DOS/NT headers, imports, exports, and sections"),
    ("inspect-pe-resources", "Inspect Windows PE resources (.rsrc, dialogs, icons, manifests)"),
    ("inspect-pe-certificates", "Inspect Authenticode digital signatures and certificate chains"),
    ("inspect-pe-imports", "Inspect PE Import Address Table (IAT) and delay-loaded imports"),
    ("inspect-native-exports", "Inspect exported native functions, names, and ordinals"),

    # Linux & ELF Analysis
    ("inspect-elf-dependencies", "ELF dynamic libraries, DT_NEEDED, and security hardening"),
    ("inspect-elf-notes", "Inspect ELF build notes, build ID, ABI tags, and GNU properties"),

    # Languages, Runtimes & Frameworks
    ("inspect-go-binary", "Inspect Go binaries, gopclntab, functions, types, and goroutines"),
    ("inspect-rust-binary", "Inspect Rust binaries, demangled signatures, and crate metadata"),
    ("inspect-il2cpp-metadata", "Inspect Unity IL2CPP game assemblies and global-metadata.dat"),
    ("inspect-python-pyc", "Inspect Python compiled bytecode (.pyc) structure and instructions"),
    ("inspect-erlang-beam", "Inspect Erlang BEAM bytecode chunks, exports, and atoms"),

    # AI Models & GPU Shaders
    ("inspect-model-artifact", "Inspect AI model architecture, weights, ONNX, GGUF, SafeTensors"),
    ("inspect-gpu-code-objects", "Inspect GPU binaries, SPIR-V, DXBC, Metal, and CUDA cubins"),

    # Android & Mobile
    ("inspect-apk-signature", "Inspect APK v1/v2/v3/v4 signing schemes, fingerprints, certificates"),
    ("decode-android-resources", "Decode APK manifest, resource tables, and strings via apktool"),
    ("search-android-classes", "Search and inventory APK DEX classes and structures"),
    ("project-android-application-graph", "Project APK inventory into Android application graph"),
    ("list-adb-devices", "List connected Android physical devices and emulators"),
    ("list-adb-packages", "List installed packages on connected Android device"),
    ("read-adb-logcat", "Read live logcat stream from connected Android device"),
    ("install-adb-package", "Install local APK onto connected Android device"),
    ("pull-adb-package", "Pull installed APK set from connected Android device"),
    ("start-adb-app", "Start launcher activity of installed Android package"),

    # Apple & macOS / iOS
    ("inspect-macho-headers", "Apple Mach-O headers, load commands, and dylib resolution"),
    ("inspect-apple-ips", "Inspect Apple IPS crash report files, threads, and stacktraces"),
    ("demangle-swift", "Demangle Swift symbols and types"),
    ("observe-native-calls", "Record entries into functions or Obj-C methods under LLDB"),

    # Web, JavaScript & WebAssembly
    ("inspect-wasm-artifact", "Disassemble and inspect WebAssembly artifacts with WABT"),
    ("inspect-web-page", "Inspect active page DOM and listeners through Chrome DevTools Protocol"),
    ("inspect-web-network-capture", "Inspect captured HAR, mitmproxy, or Fiddler network records"),
    ("recover-javascript-sources", "Recover readable JavaScript modules with source provenance"),
    ("list-browser-targets", "List active CDP browser pages and targets"),
    ("list-electron-targets", "List local targets exposed by Electron CDP endpoints"),

    # Dynamic Hooking & Frida
    ("instrument-with-frida", "Run dynamic Frida script against target process"),
    ("list-frida-devices", "List local and remote Frida devices"),
    ("list-frida-processes", "List processes visible through Frida device"),
]


class CustomCommandDialog(QDialog):
    """Dialog allowing users to execute any of the 80+ REA subcommands with custom parameters."""

    def __init__(self, parent=None, target_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Run REA Command")
        self.setMinimumWidth(580)
        self.setStyleSheet(LIGHT_THEME_QSS)
        self.target_path = target_path
        self.selected_command: List[str] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        title = QLabel("Execute Under-The-Hood REA Command")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1E293B;")
        layout.addWidget(title)

        desc = QLabel(
            "REA contains over 80 specialized reverse engineering subcommands for binaries, "
            "Android APKs, Web/CDP runtimes, and dynamic Frida instrumentation. "
            "Select any tool below or customize arguments."
        )
        desc.setStyleSheet("color: #64748B; font-size: 12px; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Command Selector
        layout.addWidget(QLabel("Select Tool / Subcommand:"))
        self.combo_cmd = QComboBox()
        self.combo_cmd.setEditable(True)
        for cmd_name, cmd_desc in REA_ALL_COMMANDS:
            self.combo_cmd.addItem(f"{cmd_name} — {cmd_desc}", cmd_name)
        layout.addWidget(self.combo_cmd)

        # Arguments Input
        layout.addWidget(QLabel("Arguments & Target Options:"))
        self.txt_args = QLineEdit()
        if self.target_path:
            self.txt_args.setText(self.target_path)
        self.txt_args.setPlaceholderText("e.g. /path/to/binary or function_name")
        layout.addWidget(self.txt_args)

        # Format selector
        h_opt = QHBoxLayout()
        h_opt.addWidget(QLabel("Output Format:"))
        self.combo_fmt = QComboBox()
        for fmt in ("(default)", "json", "toon", "yaml", "md", "jsonl"):
            self.combo_fmt.addItem(fmt)
        h_opt.addWidget(self.combo_fmt)

        self.chk_full = QCheckBox("Full envelope (--full-output)")
        h_opt.addWidget(self.chk_full)
        h_opt.addStretch()
        layout.addLayout(h_opt)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_run = QPushButton("Execute Command")
        btn_run.setObjectName("btn_run_cmd")
        btn_run.setProperty("class", "primary")
        btn_run.clicked.connect(self._on_run)
        btn_box.addWidget(btn_run)

        layout.addLayout(btn_box)

    def _on_run(self):
        cmd = self.combo_cmd.currentData()
        if not cmd:
            cmd = self.combo_cmd.currentText().split(" ")[0].strip()

        args_str = self.txt_args.text().strip()
        import shlex
        extra_args = shlex.split(args_str) if args_str else []

        full_args = [cmd] + extra_args

        fmt = self.combo_fmt.currentText()
        if fmt != "(default)":
            full_args.extend(["--format", fmt])

        if self.chk_full.isChecked():
            full_args.append("--full-output")

        self.selected_command = full_args
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class ReaMainWindow(QMainWindow):
    """Primary Window for REA Reverse Engineering GUI."""

    def __init__(self, target_file: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("MakuluLinux Rea — Reverse Engineering Anything (Electra AI)")
        self.resize(1280, 840)
        self.setMinimumSize(960, 640)
        self.setStyleSheet(LIGHT_THEME_QSS)

        if os.path.isfile(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        # State
        self.settings = load_gui_settings()
        self.target_path = target_file or ""
        self.current_worker: Optional[ToolExecutionWorker] = None
        self.ai_worker: Optional[ElectraAiChatWorker] = None
        self.chat_history: List[Dict[str, str]] = []

        self._init_ui()

        # Keyboard Shortcut: Ctrl+O to browse binary
        self.shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_open.activated.connect(self._browse_target_file)

        # If binary supplied on CLI or drag/drop, inspect it immediately
        if self.target_path and os.path.isfile(self.target_path):
            self.set_target_file(self.target_path)
            QTimer.singleShot(400, self.action_inspect_headers)

    # ─────────────────────────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        main_layout.addWidget(self._create_header_bar())

        # 2. Prominent Target Selection Bar (with Browse button & input)
        main_layout.addWidget(self._create_target_bar())

        # 3. Main Splitter (Left: Analysis Tabs + Log Box, Right: Electra AI Copilot)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(4)

        # Left Column: Tabs & Live Log Box in vertical splitter
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 6, 12)
        left_layout.setSpacing(10)

        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setHandleWidth(4)

        # Analysis Tabs Widget
        self.analysis_tabs = self._create_analysis_tabs()
        self.left_splitter.addWidget(self.analysis_tabs)

        # Live Real-time Log Console Widget
        self.log_console = self._create_log_console()
        self.left_splitter.addWidget(self.log_console)

        # Initial vertical split (65% tabs, 35% logs)
        self.left_splitter.setSizes([480, 240])
        left_layout.addWidget(self.left_splitter)

        self.main_splitter.addWidget(left_widget)

        # Right Column: Electra AI Copilot Panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 12, 12, 12)
        right_layout.setSpacing(0)

        self.ai_panel = self._create_ai_panel()
        right_layout.addWidget(self.ai_panel)

        self.main_splitter.addWidget(right_widget)

        # Initial horizontal split (62% analysis & logs, 38% AI copilot)
        self.main_splitter.setSizes([780, 500])
        main_layout.addWidget(self.main_splitter, 1)

        # Enable Drag and Drop
        self.setAcceptDrops(True)

    def _create_header_bar(self) -> QWidget:
        header = QFrame()
        header.setObjectName("HeaderFrame")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        # Logo / Title
        v_title = QVBoxLayout()
        v_title.setSpacing(2)

        h_title = QHBoxLayout()
        h_title.setSpacing(8)
        lbl_title = QLabel("MakuluLinux Rea")
        lbl_title.setObjectName("AppTitle")
        badge = QLabel("ELECTRA AI")
        badge.setObjectName("BadgePill")
        h_title.addWidget(lbl_title)
        h_title.addWidget(badge)
        h_title.addStretch()

        lbl_sub = QLabel("forked from morluto/rea • Reverse Engineering Anything")
        lbl_sub.setObjectName("AppSubtitle")
        lbl_sub.setStyleSheet("font-size: 11px; font-style: italic; color: #64748B; font-weight: 500;")

        v_title.addLayout(h_title)
        v_title.addWidget(lbl_sub)
        layout.addLayout(v_title)

        layout.addStretch()

        # Model Selector Dropdown (Defaults to Electra Nano)
        lbl_model = QLabel("Model:")
        lbl_model.setStyleSheet("font-weight: 600; color: #475569;")
        layout.addWidget(lbl_model)

        self.combo_model = QComboBox()
        self.combo_model.setFixedWidth(270)
        for model_id, model_label in AVAILABLE_MODELS:
            self.combo_model.addItem(model_label, model_id)
        current_model = self.settings.get("model", "electra-nano")
        idx = self.combo_model.findData(current_model)
        if idx >= 0:
            self.combo_model.setCurrentIndex(idx)
        else:
            self.combo_model.setCurrentIndex(0)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)
        layout.addWidget(self.combo_model)

        # Settings Button
        btn_settings = QPushButton("Settings")
        btn_settings.clicked.connect(self._open_settings)
        layout.addWidget(btn_settings)

        # About Button
        btn_about = QPushButton("About")
        btn_about.clicked.connect(self._open_about)
        layout.addWidget(btn_about)

        return header

    def _create_target_bar(self) -> QWidget:
        """Prominent Target Selection Bar with Browse button, path input, clear button, and format pills."""
        container = QFrame()
        container.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0; padding: 6px 16px;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        # Prominent Browse Button
        self.btn_browse = QPushButton("Browse Binary... (Ctrl+O)")
        self.btn_browse.setObjectName("btn_browse")
        self.btn_browse.setProperty("class", "primary")
        self.btn_browse.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_browse.setToolTip("Click to browse and open any binary or executable file on your computer")
        self.btn_browse.clicked.connect(self._browse_target_file)
        layout.addWidget(self.btn_browse)

        # Path display and manual input box
        self.txt_target_path = QLineEdit()
        self.txt_target_path.setPlaceholderText("No binary selected — click Browse Binary... or drag & drop file here")
        self.txt_target_path.setStyleSheet("font-weight: 500; color: #1E293B; padding: 6px 10px;")
        self.txt_target_path.returnPressed.connect(self._on_target_path_entered)
        layout.addWidget(self.txt_target_path, 1)

        # Clear Button
        self.btn_clear_target = QPushButton("Clear")
        self.btn_clear_target.setFixedHeight(30)
        self.btn_clear_target.setToolTip("Unload current binary")
        self.btn_clear_target.clicked.connect(self.clear_target_file)
        layout.addWidget(self.btn_clear_target)

        # Target Format Pill
        self.badge_format = QLabel("FORMAT: NONE")
        self.badge_format.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; font-size: 11px; "
            "font-weight: 600; padding: 3px 8px; border-radius: 4px; border: 1px solid #CBD5E1;"
        )
        layout.addWidget(self.badge_format)

        # Target Size Pill
        self.badge_size = QLabel("SIZE: 0 B")
        self.badge_size.setStyleSheet(
            "background-color: #F1F5F9; color: #475569; font-size: 11px; "
            "font-weight: 600; padding: 3px 8px; border-radius: 4px; border: 1px solid #CBD5E1;"
        )
        layout.addWidget(self.badge_size)

        return container

    def _create_analysis_tabs(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # Action Buttons Toolbar above tabs
        actions_bar = QWidget()
        actions_bar.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E2E8F0; padding: 6px 10px;")
        actions_layout = QHBoxLayout(actions_bar)
        actions_layout.setContentsMargins(8, 4, 8, 4)
        actions_layout.setSpacing(6)

        btn_inspect = QPushButton("Inspect Headers")
        btn_inspect.setProperty("class", "action")
        btn_inspect.clicked.connect(self.action_inspect_headers)
        actions_layout.addWidget(btn_inspect)

        btn_disasm = QPushButton("Disassemble")
        btn_disasm.setProperty("class", "action")
        btn_disasm.clicked.connect(self.action_disassemble)
        actions_layout.addWidget(btn_disasm)

        btn_decompile = QPushButton("Decompile (Ghidra)")
        btn_decompile.setProperty("class", "action")
        btn_decompile.clicked.connect(self.action_decompile)
        actions_layout.addWidget(btn_decompile)

        btn_strings = QPushButton("Extract Strings")
        btn_strings.setProperty("class", "action")
        btn_strings.clicked.connect(self.action_strings)
        actions_layout.addWidget(btn_strings)

        btn_audit = QPushButton("Security Audit")
        btn_audit.setProperty("class", "action")
        btn_audit.clicked.connect(self.action_security_audit)
        actions_layout.addWidget(btn_audit)

        # More Tools Dropdown Menu (Direct categorized access to all specialized REA subcommands)
        btn_more = QPushButton("More Tools ▾")
        btn_more.setProperty("class", "action")
        menu_more = QMenu(self)

        # 1. Windows PE Submenu
        menu_pe = menu_more.addMenu("Windows PE Tools")
        menu_pe.addAction("Inspect PE Headers", lambda: self._run_extended_tool("inspect-pe-headers"))
        menu_pe.addAction("Inspect PE Resources & Manifests", lambda: self._run_extended_tool("inspect-pe-resources"))
        menu_pe.addAction("Inspect PE Digital Certificates", lambda: self._run_extended_tool("inspect-pe-certificates"))
        menu_pe.addAction("Inspect PE Import Address Table (IAT)", lambda: self._run_extended_tool("inspect-pe-imports"))
        menu_pe.addAction("Inspect Native Exported Symbols", lambda: self._run_extended_tool("inspect-native-exports"))

        # 2. Linux ELF Submenu
        menu_elf = menu_more.addMenu("Linux ELF Tools")
        menu_elf.addAction("Inspect Dynamic Libraries (DT_NEEDED)", lambda: self._run_extended_tool("inspect-elf-dependencies"))
        menu_elf.addAction("Inspect ELF Notes & ABI Tags", lambda: self._run_extended_tool("inspect-elf-notes"))

        # 3. Languages & Frameworks Submenu
        menu_lang = menu_more.addMenu("Languages & Frameworks")
        menu_lang.addAction("Inspect Go Binary (pclntab & functions)", lambda: self._run_extended_tool("inspect-go-binary"))
        menu_lang.addAction("Inspect Rust Binary (demangle & crates)", lambda: self._run_extended_tool("inspect-rust-binary"))
        menu_lang.addAction("Inspect Unity IL2CPP Metadata", lambda: self._run_extended_tool("inspect-il2cpp-metadata"))
        menu_lang.addAction("Inspect Python Bytecode (.pyc)", lambda: self._run_extended_tool("inspect-python-pyc"))
        menu_lang.addAction("Inspect Erlang BEAM Bytecode", lambda: self._run_extended_tool("inspect-erlang-beam"))

        # 4. Security & Entropy Diagnostics Submenu
        menu_diag = menu_more.addMenu("Security & Entropy Diagnostics")
        menu_diag.addAction("Analyze Byte Entropy (Packing/Encryption)", lambda: self._run_extended_tool("inspect-byte-entropy"))
        menu_diag.addAction("Analyze Binary Layout & Alignment", lambda: self._run_extended_tool("inspect-binary-layout"))
        menu_diag.addAction("Match Native Functions & Signatures", lambda: self._run_extended_tool("match-native-functions"))

        # 5. Decompilation Engines Submenu
        menu_decomp = menu_more.addMenu("Decompilation Engines")
        menu_decomp.addAction("Batch Decompile All Functions", lambda: self._run_extended_tool("decompile-all"))
        menu_decomp.addAction("Decompile with RetDec", lambda: self._run_extended_tool("decompile-with-retdec"))
        menu_decomp.addAction("Analyze with Radare2", lambda: self._run_extended_tool("analyze-with-radare2"))
        menu_decomp.addAction("GNU objdump Disassembly", lambda: self._run_extended_tool("inspect-with-objdump", ["disassemble"]))

        # 6. AI Models & GPU Shaders Submenu
        menu_ai_gpu = menu_more.addMenu("AI Models & GPU Shaders")
        menu_ai_gpu.addAction("Inspect AI Model (ONNX / GGUF / SafeTensors)", lambda: self._run_extended_tool("inspect-model-artifact"))
        menu_ai_gpu.addAction("Inspect GPU Code Objects / Shaders", lambda: self._run_extended_tool("inspect-gpu-code-objects"))

        # 7. Android & Mobile Submenu
        menu_android = menu_more.addMenu("Android & Mobile")
        menu_android.addAction("Inspect APK Signature Schemes (v1/v2/v3)", lambda: self._run_extended_tool("inspect-apk-signature"))
        menu_android.addAction("Decode Android Resources (apktool)", lambda: self._run_extended_tool("decode-android-resources"))
        menu_android.addAction("Search Android Classes (DEX)", lambda: self._run_extended_tool("search-android-classes"))
        menu_android.addAction("Project Android Application Graph", lambda: self._run_extended_tool("project-android-application-graph"))
        menu_android.addAction("List Connected ADB Devices", lambda: self._run_global_tool("list-adb-devices"))

        # 8. Apple & Mach-O Submenu
        menu_apple = menu_more.addMenu("Apple & Mach-O")
        menu_apple.addAction("Inspect Mach-O Headers", lambda: self._run_extended_tool("inspect-macho-headers"))
        menu_apple.addAction("Inspect Apple IPS Crash Report", lambda: self._run_extended_tool("inspect-apple-ips"))
        menu_apple.addAction("Demangle Swift Symbols", lambda: self._run_extended_tool("demangle-swift"))

        # 9. Web & Dynamic Hooking Submenu
        menu_web = menu_more.addMenu("Web & Dynamic Hooking")
        menu_web.addAction("Inspect WebAssembly Artifact (WABT)", lambda: self._run_extended_tool("inspect-wasm-artifact"))
        menu_web.addAction("Recover JavaScript Sources (CDP)", lambda: self._run_extended_tool("recover-javascript-sources"))
        menu_web.addAction("List Frida Devices", lambda: self._run_global_tool("list-frida-devices"))

        menu_more.addSeparator()
        act_custom = menu_more.addAction("Run Custom REA Command...")
        act_custom.triggered.connect(self._open_custom_command_dialog)

        btn_more.setMenu(menu_more)
        actions_layout.addWidget(btn_more)

        actions_layout.addStretch()

        btn_auto_ai = QPushButton("Auto-Analyze with Electra")
        btn_auto_ai.setObjectName("btn_auto_ai")
        btn_auto_ai.setProperty("class", "primary")
        btn_auto_ai.clicked.connect(self.action_auto_analyze)
        actions_layout.addWidget(btn_auto_ai)

        layout.addWidget(actions_bar)

        # Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Overview (Stacked Widget: Page 0 = Welcome / Browse Dropzone, Page 1 = Full Overview)
        self.stack_overview = QStackedWidget()

        # Page 0: Welcome / Browse Hero Card
        page_welcome = QWidget()
        v_welcome = QVBoxLayout(page_welcome)
        v_welcome.setAlignment(Qt.AlignCenter)
        v_welcome.setSpacing(14)
        v_welcome.setContentsMargins(40, 40, 40, 40)

        lbl_hero_badge = QLabel("REA")
        lbl_hero_badge.setStyleSheet(
            "font-size: 28px; font-weight: 900; color: #2563EB; "
            "background-color: #EFF6FF; border: 2px solid #BFDBFE; "
            "border-radius: 12px; padding: 6px 22px;"
        )
        lbl_hero_badge.setAlignment(Qt.AlignCenter)
        v_welcome.addWidget(lbl_hero_badge, 0, Qt.AlignCenter)

        lbl_hero_title = QLabel("Select a Binary to Begin Reverse Engineering")
        lbl_hero_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1E293B;")
        lbl_hero_title.setAlignment(Qt.AlignCenter)
        v_welcome.addWidget(lbl_hero_title)

        lbl_hero_sub = QLabel(
            "Browse your system for any executable, shared library, or binary file (ELF, PE, Mach-O, APK, WASM),\n"
            "or simply drag and drop the file directly onto this window."
        )
        lbl_hero_sub.setStyleSheet("font-size: 13px; color: #64748B; line-height: 1.5;")
        lbl_hero_sub.setAlignment(Qt.AlignCenter)
        v_welcome.addWidget(lbl_hero_sub)

        # Big, Center Browse Button
        btn_hero_browse = QPushButton("Browse & Select Binary File... (Ctrl+O)")
        btn_hero_browse.setObjectName("btn_hero_browse")
        btn_hero_browse.setProperty("class", "primary")
        btn_hero_browse.setCursor(QCursor(Qt.PointingHandCursor))
        btn_hero_browse.setFixedHeight(44)
        btn_hero_browse.setFixedWidth(320)
        btn_hero_browse.setStyleSheet("font-size: 14px; font-weight: 700;")
        btn_hero_browse.clicked.connect(self._browse_target_file)
        v_welcome.addWidget(btn_hero_browse, 0, Qt.AlignCenter)

        # Sample Quick Test Button
        h_samples = QHBoxLayout()
        h_samples.setSpacing(10)
        lbl_try = QLabel("Quick Test:")
        lbl_try.setStyleSheet("color: #94A3B8; font-size: 12px;")
        h_samples.addWidget(lbl_try)

        btn_sample_ls = QPushButton("Load /bin/ls")
        btn_sample_ls.setProperty("class", "chip")
        btn_sample_ls.clicked.connect(lambda: self.set_target_file("/bin/ls") or self.action_inspect_headers())
        h_samples.addWidget(btn_sample_ls)

        btn_sample_bash = QPushButton("Load /bin/bash")
        btn_sample_bash.setProperty("class", "chip")
        btn_sample_bash.clicked.connect(lambda: self.set_target_file("/bin/bash") or self.action_inspect_headers())
        h_samples.addWidget(btn_sample_bash)

        v_welcome.addLayout(h_samples)
        self.stack_overview.addWidget(page_welcome)

        # Page 1: Loaded Overview Viewer
        self.tab_overview = QTextEdit()
        self.tab_overview.setReadOnly(True)
        self.tab_overview.setProperty("class", "code-view")
        self.tab_overview.setPlaceholderText("Binary overview, sections, and hashes will appear here...")
        self.stack_overview.addWidget(self.tab_overview)

        self.tabs.addTab(self.stack_overview, "Overview")

        # Tab 2: Disassembly
        self.tab_disasm = QPlainTextEdit()
        self.tab_disasm.setReadOnly(True)
        self.tab_disasm.setProperty("class", "code-view")
        self.tab_disasm.setPlaceholderText("Disassembly listing (ASM) will appear here...")
        self.tabs.addTab(self.tab_disasm, "Disassembly")

        # Tab 3: Decompiled C
        self.tab_decomp = QPlainTextEdit()
        self.tab_decomp.setReadOnly(True)
        self.tab_decomp.setProperty("class", "code-view")
        self.tab_decomp.setPlaceholderText("Decompiled C pseudocode will appear here...")
        self.tabs.addTab(self.tab_decomp, "Decompiled C")

        # Tab 4: Strings & Symbols
        self.tab_strings = QTextEdit()
        self.tab_strings.setReadOnly(True)
        self.tab_strings.setProperty("class", "code-view")
        self.tab_strings.setPlaceholderText("Extracted strings, URLs, and symbols will appear here...")
        self.tabs.addTab(self.tab_strings, "Strings & Symbols")

        # Tab 5: Hex View
        self.tab_hex = QPlainTextEdit()
        self.tab_hex.setReadOnly(True)
        self.tab_hex.setProperty("class", "code-view")
        self.tab_hex.setPlaceholderText("Hexadecimal byte dump will appear here...")
        self.tabs.addTab(self.tab_hex, "Hex View")

        # Tab 6: Tool Output
        self.tab_raw = QPlainTextEdit()
        self.tab_raw.setReadOnly(True)
        self.tab_raw.setProperty("class", "code-view")
        self.tab_raw.setPlaceholderText("Output from extended tools and custom commands will appear here...")
        self.tabs.addTab(self.tab_raw, "Tool Output")

        layout.addWidget(self.tabs)
        return card

    def _create_log_console(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        # Console Header
        console_bar = QWidget()
        console_bar.setStyleSheet("background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0; padding: 4px 10px;")
        bar_layout = QHBoxLayout(console_bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.setSpacing(8)

        lbl_log = QLabel("Real-Time Execution Log")
        lbl_log.setStyleSheet("font-weight: 700; color: #475569; font-size: 12px;")
        bar_layout.addWidget(lbl_log)

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("font-size: 11px; color: #64748B;")
        bar_layout.addWidget(self.chk_autoscroll)

        bar_layout.addStretch()

        btn_copy = QPushButton("Copy")
        btn_copy.setFixedHeight(24)
        btn_copy.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_copy.clicked.connect(self._copy_log)
        bar_layout.addWidget(btn_copy)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(24)
        btn_clear.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_clear.clicked.connect(self._clear_log)
        bar_layout.addWidget(btn_clear)

        layout.addWidget(console_bar)

        # Log Text Box
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setProperty("class", "code-view")
        self.txt_log.setStyleSheet(
            "background-color: #FFFFFF; color: #1E293B; font-family: 'DejaVu Sans Mono', monospace; font-size: 11px;"
        )
        layout.addWidget(self.txt_log)

        return card

    def _create_ai_panel(self) -> QWidget:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Copilot Header
        h_copilot = QHBoxLayout()
        h_copilot.setSpacing(6)
        lbl_ai = QLabel("Electra AI Copilot")
        lbl_ai.setStyleSheet("font-size: 14px; font-weight: 700; color: #1E293B;")
        h_copilot.addWidget(lbl_ai)

        self.lbl_ai_status = QLabel("Ready")
        self.lbl_ai_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        h_copilot.addWidget(self.lbl_ai_status)
        h_copilot.addStretch()

        btn_clear_chat = QPushButton("Clear Chat")
        btn_clear_chat.setFixedHeight(24)
        btn_clear_chat.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        btn_clear_chat.clicked.connect(self._clear_chat)
        h_copilot.addWidget(btn_clear_chat)

        layout.addLayout(h_copilot)

        # Quick Prompt Chips
        chip_layout = QHBoxLayout()
        chip_layout.setSpacing(6)

        chips = [
            ("Explain Binary", "Analyze the target binary and explain its primary purpose and functionality."),
            ("Entropy & Packing", "Analyze whether this binary is packed, compressed, or obfuscated based on byte entropy and anomalous section headers."),
            ("Vulnerability Scan", "Scan the binary's functions and imports for potential security vulnerabilities, unsafe buffer operations, or format string bugs."),
            ("Explain Disasm", "Review the current disassembly and explain the control flow and critical logic."),
            ("Extract Secrets", "Look through extracted strings and symbols for hardcoded secrets, keys, IP addresses, or endpoints.")
        ]

        for label, prompt_text in chips:
            btn_chip = QPushButton(label)
            btn_chip.setProperty("class", "chip")
            btn_chip.clicked.connect(lambda checked, p=prompt_text: self._send_ai_prompt(p))
            chip_layout.addWidget(btn_chip)

        layout.addLayout(chip_layout)

        # Chat History Viewer
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px;"
        )
        self.chat_view.setPlaceholderText(
            "Electra AI Copilot conversation will appear here.\n"
            "Ask questions about the binary, request decompilations, or click a quick action above."
        )
        layout.addWidget(self.chat_view, 1)

        # User Prompt Box & Send Button
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setFixedHeight(56)
        self.txt_prompt.setPlaceholderText("Ask Electra AI about this binary... (Shift+Enter for newline, Enter to send)")
        self.txt_prompt.installEventFilter(self)
        input_layout.addWidget(self.txt_prompt, 1)

        v_btns = QVBoxLayout()
        v_btns.setSpacing(4)
        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.setProperty("class", "primary")
        self.btn_send.setFixedHeight(28)
        self.btn_send.clicked.connect(self._on_send_clicked)
        v_btns.addWidget(self.btn_send)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setFixedHeight(24)
        self.btn_stop.setStyleSheet("font-size: 11px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        v_btns.addWidget(self.btn_stop)

        input_layout.addLayout(v_btns)
        layout.addWidget(input_container)

        return card

    # ─────────────────────────────────────────────────────────────────────────
    #  FILE HANDLING & DRAG-AND-DROP
    # ─────────────────────────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isfile(path):
                self.set_target_file(path)
                self.action_inspect_headers()

    def _browse_target_file(self):
        start_dir = os.path.dirname(self.target_path) if self.target_path else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Binary or Executable to Reverse Engineer",
            start_dir,
            "Executable / Binary Files (*);;All Files (*)"
        )
        if path and os.path.isfile(path):
            self.set_target_file(path)
            self.action_inspect_headers()

    def _on_target_path_entered(self):
        path = self.txt_target_path.text().strip()
        if path and os.path.isfile(path):
            self.set_target_file(path)
            self.action_inspect_headers()
        elif path:
            QMessageBox.warning(self, "Invalid File", f"File does not exist:\n{path}")

    def clear_target_file(self):
        self.target_path = ""
        self.txt_target_path.clear()
        self.badge_format.setText("FORMAT: NONE")
        self.badge_size.setText("SIZE: 0 B")
        self.tab_overview.clear()
        self.tab_disasm.clear()
        self.tab_decomp.clear()
        self.tab_strings.clear()
        self.tab_hex.clear()
        self.stack_overview.setCurrentIndex(0)
        self.append_log("Target cleared.", "info")

    def set_target_file(self, path: str):
        self.target_path = os.path.abspath(path)
        self.txt_target_path.setText(self.target_path)

        # Switch Overview stack to Page 1 (Loaded View)
        self.stack_overview.setCurrentIndex(1)

        # Update file size
        try:
            sz = os.path.getsize(self.target_path)
            if sz < 1024:
                size_str = f"{sz} B"
            elif sz < 1024 * 1024:
                size_str = f"{sz / 1024:.1f} KB"
            else:
                size_str = f"{sz / (1024 * 1024):.1f} MB"
            self.badge_size.setText(f"SIZE: {size_str}")
        except Exception:
            self.badge_size.setText("SIZE: N/A")

        # Detect Format & Architecture
        fmt = self._detect_file_format(self.target_path)
        self.badge_format.setText(f"FORMAT: {fmt}")
        self.append_log(f"Loaded target binary: {self.target_path} ({fmt})", "info")

        # Populate Hex View preview
        self._populate_hex_preview(self.target_path)

    def _detect_file_format(self, path: str) -> str:
        try:
            basename = os.path.basename(path).lower()
            if basename == "global-metadata.dat":
                return "Unity IL2CPP Metadata"
            if basename.endswith(".ips"):
                return "Apple IPS Crash Report"
            if basename.endswith(".pyc"):
                return "Python Bytecode (.pyc)"
            if basename.endswith((".onnx", ".gguf", ".safetensors")):
                return "AI Model Artifact"

            with open(path, "rb") as f:
                magic = f.read(16)
                if magic.startswith(b"\x7fELF"):
                    # Check 32 vs 64 bit
                    is_64 = magic[4] == 2
                    return f"ELF {'64-bit' if is_64 else '32-bit'}"
                elif magic.startswith(b"MZ"):
                    return "PE Windows Executable"
                elif magic.startswith((b"\xca\xfe\xba\xbe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")):
                    return "Mach-O Apple Binary"
                elif magic.startswith(b"PK\x03\x04"):
                    if path.endswith(".apk"):
                        return "Android APK"
                    return "ZIP / Archive"
                elif magic.startswith(b"\x00asm"):
                    return "WebAssembly (WASM)"
                elif magic.startswith(b"dex\n"):
                    return "Dalvik Executable (DEX)"
                elif magic.startswith(b"FOR1") and path.endswith(".beam"):
                    return "Erlang BEAM Bytecode"
                elif magic.startswith(b"GGUF"):
                    return "GGUF AI Model"
        except Exception:
            pass
        return "Raw Binary"

    def _populate_hex_preview(self, path: str, max_bytes: int = 4096):
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
                lines = []
                for i in range(0, len(data), 16):
                    chunk = data[i:i+16]
                    hex_part = " ".join(f"{b:02x}" for b in chunk)
                    ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                    lines.append(f"{i:08x}  {hex_part:<48}  |{ascii_part}|")
                if len(data) == max_bytes:
                    lines.append(f"... (preview limited to first {max_bytes} bytes) ...")
                self.tab_hex.setPlainText("\n".join(lines))
        except Exception as e:
            self.tab_hex.setPlainText(f"Error loading hex preview: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    #  LOG & CHAT OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────

    def append_log(self, text: str, level: str = "info"):
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
            "info": "#2563EB",     # Blue
            "run": "#7C3AED",      # Purple
            "success": "#10B981",  # Green
            "error": "#EF4444",    # Red
            "warn": "#F59E0B",     # Amber
            "ai": "#0D9488"        # Teal
        }
        tag_color = color_map.get(level, "#475569")
        tag_label = level.upper()

        html_line = (
            f"<span style='color: #94A3B8;'>[{timestamp}]</span> "
            f"<span style='color: {tag_color}; font-weight: bold;'>[{tag_label}]</span> "
            f"<span style='color: #1E293B;'>{text}</span><br>"
        )

        cursor = self.txt_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html_line)

        if self.chk_autoscroll.isChecked():
            self.txt_log.ensureCursorVisible()

    def _clear_log(self):
        self.txt_log.clear()

    def _copy_log(self):
        QApplication.clipboard().setText(self.txt_log.toPlainText())
        self.append_log("Log copied to clipboard.", "info")

    def _clear_chat(self):
        self.chat_history.clear()
        self.chat_view.clear()
        self.append_log("Chat history cleared.", "info")

    def append_chat_message(self, role: str, content: str):
        self.chat_history.append({"role": role, "content": content})

        if role == "user":
            bg_color = "#EFF6FF"
            border_color = "#BFDBFE"
            sender_name = "You"
            sender_color = "#1D4ED8"
        else:
            bg_color = "#F8FAFC"
            border_color = "#E2E8F0"
            sender_name = "Electra AI"
            sender_color = "#0D9488"

        escaped = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        formatted_content = escaped.replace("\n", "<br>")

        # Check for code blocks
        if "```" in content:
            parts = content.split("```")
            out = []
            for i, p in enumerate(parts):
                if i % 2 == 1:
                    code_esc = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    out.append(
                        f"<pre style='background-color: #F1F5F9; border: 1px solid #CBD5E1; padding: 8px; "
                        f"border-radius: 4px; font-family: monospace;'>{code_esc}</pre>"
                    )
                else:
                    out.append(p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>"))
            formatted_content = "".join(out)

        html = f"""
        <div style='margin-bottom: 12px; background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 10px;'>
            <div style='font-weight: 700; color: {sender_color}; font-size: 11px; margin-bottom: 4px;'>{sender_name}</div>
            <div style='color: #0F172A; font-size: 12px;'>{formatted_content}</div>
        </div>
        """

        cursor = self.chat_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        self.chat_view.ensureCursorVisible()

    # ─────────────────────────────────────────────────────────────────────────
    #  REVERSE ENGINEERING QUICK ACTIONS
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_target(self) -> bool:
        if not self.target_path or not os.path.isfile(self.target_path):
            QMessageBox.warning(self, "No Target Loaded", "Please browse and select a binary file first.")
            self._browse_target_file()
            return bool(self.target_path and os.path.isfile(self.target_path))
        return True

    def _run_tool_command(self, command_id: str, args: List[str]):
        if self.current_worker and self.current_worker.isRunning():
            self.append_log("Another analysis task is currently running. Please wait...", "warn")
            return

        rea_bin = self.settings.get("rea_bin", REA_BIN_PATH)
        full_args = [rea_bin] + args

        self.current_worker = ToolExecutionWorker(command_id, full_args)
        self.current_worker.log_line.connect(self.append_log)
        self.current_worker.completed.connect(self._on_tool_completed)
        self.current_worker.failed.connect(self._on_tool_failed)
        self.current_worker.start()

    def _on_tool_completed(self, command_id: str, output: str):
        if command_id == "inspect_headers":
            self.stack_overview.setCurrentIndex(1)
            self.tab_overview.setText(output)
            self.tabs.setCurrentIndex(0)
        elif command_id == "disassemble":
            self.tab_disasm.setPlainText(output)
            self.tabs.setCurrentIndex(1)
        elif command_id == "decompile":
            self.tab_decomp.setPlainText(output)
            self.tabs.setCurrentIndex(2)
        elif command_id == "strings":
            self.tab_strings.setText(output)
            self.tabs.setCurrentIndex(3)
        elif command_id == "security_audit":
            self.stack_overview.setCurrentIndex(1)
            self.tab_overview.append("\n\n" + "="*50 + "\nSECURITY AUDIT RESULTS:\n" + "="*50 + "\n" + output)
            self.tabs.setCurrentIndex(0)
        elif command_id == "custom_tool":
            self.tab_raw.setPlainText(output)
            self.tabs.setCurrentWidget(self.tab_raw)
        elif command_id == "auto_analyze":
            self.stack_overview.setCurrentIndex(1)
            self.tab_overview.setText(output)
            self.tabs.setCurrentIndex(0)
            # Feed result to Electra AI
            prompt = (
                f"I have inspected the binary '{os.path.basename(self.target_path)}'.\n"
                f"Here are the header and architecture details:\n\n{output[:3000]}\n\n"
                f"Please provide an executive technical overview of what this binary is, its architecture, "
                f"its likely purpose, and key security implications."
            )
            self._send_ai_prompt(prompt)

    def _on_tool_failed(self, command_id: str, err: str):
        self.append_log(f"Task '{command_id}' failed: {err}", "error")

    def action_inspect_headers(self):
        if not self._ensure_target():
            return
        self.append_log(f"Inspecting file headers and sections for: {self.target_path}", "run")
        self._run_tool_command("inspect_headers", ["inspect-with-objdump", self.target_path, "file_headers"])

    def action_disassemble(self):
        if not self._ensure_target():
            return
        self.append_log(f"Disassembling {self.target_path}...", "run")
        self._run_tool_command("disassemble", ["inspect-with-objdump", self.target_path, "disassemble"])

    def action_decompile(self):
        if not self._ensure_target():
            return
        self.append_log(f"Decompiling {self.target_path} with Ghidra/RetDec...", "run")
        self._run_tool_command("decompile", ["decompile-with-ghidra", self.target_path])

    def action_strings(self):
        if not self._ensure_target():
            return
        self.append_log(f"Extracting strings from {self.target_path}...", "run")
        self._run_tool_command("strings", ["inspect-with-objdump", self.target_path, "all_headers"])

    def action_security_audit(self):
        if not self._ensure_target():
            return
        self.append_log(f"Running security mitigation audit on {self.target_path}...", "run")
        self._run_tool_command("security_audit", ["inspect-elf-dependencies", self.target_path])

    def action_auto_analyze(self):
        if not self._ensure_target():
            return
        self.append_log(f"Initiating automated multi-step analysis for {self.target_path}...", "run")
        self._run_tool_command("auto_analyze", ["inspect-with-objdump", self.target_path, "file_headers"])

    def _run_extended_tool(self, cmd_name: str, extra_flags: Optional[List[str]] = None):
        if not self._ensure_target():
            return
        flags = [cmd_name, self.target_path]
        if extra_flags:
            flags.extend(extra_flags)
        self.append_log(f"Running {cmd_name} on {self.target_path}...", "run")
        self._run_tool_command("custom_tool", flags)

    def _run_global_tool(self, cmd_name: str):
        self.append_log(f"Executing REA command: {cmd_name}...", "run")
        self._run_tool_command("custom_tool", [cmd_name])

    def _open_custom_command_dialog(self):
        dlg = CustomCommandDialog(self, target_path=self.target_path)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_command:
            cmd_line = " ".join(dlg.selected_command)
            self.append_log(f"Executing custom REA command: {cmd_line}", "run")
            self._run_tool_command("custom_tool", dlg.selected_command)

    # ─────────────────────────────────────────────────────────────────────────
    #  ELECTRA AI INTERACTION
    # ─────────────────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj == self.txt_prompt and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self._on_send_clicked()
                    return True
        return super().eventFilter(obj, event)

    def _on_model_changed(self):
        selected_model = self.combo_model.currentData()
        self.settings["model"] = selected_model
        save_gui_settings(self.settings)
        self.append_log(f"Selected model: {selected_model}", "info")

    def _on_send_clicked(self):
        prompt = self.txt_prompt.toPlainText().strip()
        if not prompt:
            return
        self.txt_prompt.clear()
        self._send_ai_prompt(prompt)

    def _send_ai_prompt(self, user_prompt: str):
        if self.ai_worker and self.ai_worker.isRunning():
            self.append_log("An Electra AI query is already in progress.", "warn")
            return

        self.append_chat_message("user", user_prompt)
        self.lbl_ai_status.setText("Thinking...")
        self.lbl_ai_status.setStyleSheet("color: #2563EB; font-size: 11px; font-weight: 600;")
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)

        server_base = self.settings.get("server_base", DEFAULT_SERVER_BASE)
        api_key = self.settings.get("api_key") or discover_electra_api_key()
        model = self.settings.get("model", "electra-nano")

        # Build context from current binary and active tab
        active_tab_idx = self.tabs.currentIndex()
        context_snippets = []
        if self.target_path:
            context_snippets.append(f"Target Binary: {self.target_path}")

        if active_tab_idx == 0 and self.tab_overview.toPlainText():
            context_snippets.append(f"--- Binary Overview / Headers ---\n{self.tab_overview.toPlainText()[:2000]}")
        elif active_tab_idx == 1 and self.tab_disasm.toPlainText():
            context_snippets.append(f"--- Active Disassembly Snippet ---\n{self.tab_disasm.toPlainText()[:2500]}")
        elif active_tab_idx == 2 and self.tab_decomp.toPlainText():
            context_snippets.append(f"--- Decompiled C Code ---\n{self.tab_decomp.toPlainText()[:2500]}")

        system_prompt = (
            "You are the Electra AI Reverse Engineering Assistant, deeply integrated into REA "
            "(Reverse Engineering Anything). You provide precise, insightful explanations of machine code, "
            "decompilations, assembly instructions, binary security mitigations, and potential vulnerabilities. "
            "Respond in clean, clear markdown format."
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Inject context snippet if available
        if context_snippets:
            context_text = "\n\n".join(context_snippets)
            messages.append({
                "role": "system",
                "content": f"Current Binary Context from REA Analysis Studio:\n{context_text}"
            })

        # Inject conversation history
        for msg in self.chat_history:
            messages.append(msg)

        self.ai_worker = ElectraAiChatWorker(server_base, api_key, model, messages)
        self.ai_worker.log_line.connect(self.append_log)
        self.ai_worker.completed.connect(self._on_ai_completed)
        self.ai_worker.failed.connect(self._on_ai_failed)
        self.ai_worker.start()

    def _on_ai_completed(self, reply: str):
        self.append_chat_message("assistant", reply)
        self.lbl_ai_status.setText("Ready")
        self.lbl_ai_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_ai_failed(self, error_msg: str):
        self.append_chat_message("assistant", f"**Electra AI Error:** {error_msg}")
        self.lbl_ai_status.setText("Error")
        self.lbl_ai_status.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_stop_clicked(self):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.cancel()
            self.append_log("Electra AI request cancelled by user.", "warn")
            self.lbl_ai_status.setText("Stopped")
            self.lbl_ai_status.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 600;")
            self.btn_send.setEnabled(True)
            self.btn_stop.setEnabled(False)

    def _open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec_() == QDialog.Accepted:
            self.settings = load_gui_settings()
            self.append_log("Settings updated successfully.", "info")

    def _open_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    target_arg = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        target_arg = sys.argv[1]

    app = QApplication(sys.argv)
    app.setApplicationName("REA")
    app.setOrganizationName("MakuluLinux")

    window = ReaMainWindow(target_file=target_arg)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
