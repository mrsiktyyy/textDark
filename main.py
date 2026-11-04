import os, sys, json, base64, secrets, traceback, re, hashlib, html as html_lib
from pathlib import Path
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from PySide6.QtCore import (
    Qt, QRect, QRectF, QPointF, QPoint, QSize, QTimer, QSettings, QObject, QEvent, QUrl,
    QByteArray, QBuffer, QIODevice,
    QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QVariantAnimation, Signal
)
from PySide6.QtGui import (
    QAction, QColor, QFont, QPainter, QPainterPath, QPen, QPalette, QTextFormat,
    QSyntaxHighlighter, QTextCharFormat, QKeySequence, QTextCursor, QImage, QPixmap,
    QDesktopServices, QIcon, QTextImageFormat, QTextTableFormat, QTextTableCellFormat,
    QTextLength, QTextBlockFormat, QTextListFormat, QTextDocument
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPlainTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QTabBar, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStatusBar, QToolBar, QToolButton, QAbstractButton, QFontComboBox, QSpinBox,
    QSplitter, QInputDialog, QFontDialog, QDialog, QDialogButtonBox, QLineEdit,
    QMenu, QGridLayout, QSlider, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect,
    QTextEdit, QComboBox, QTabWidget as QSettingsTabs, QCheckBox, QScrollArea, QFormLayout,
    QKeySequenceEdit, QSystemTrayIcon, QSplashScreen, QFrame
)

APP_NAME = "textDark"
APP_VERSION = "3.2"
# !!! ЗАМЕНИТЕ на ссылку на вашу страницу релизов на GitHub !!!
GITHUB_URL = "https://github.com/mrsiktyyy/textDark/releases"
MAGIC = b"TEXTDARK\x02"
RICH_DOC_PREFIX = "TEXTDARK_RICH_HTML_V1\n"
STYLE_PROGRAMMING = "programming"
STYLE_NOTEBOOK = "notebook"
# Convenience encryption for a closed, non-public app distribution.
# Anyone who can reverse-engineer this application can potentially recover this key.
APP_KEY = bytes.fromhex(
    "8f2c7a4d1b9e6035a6d0c4f8721e9b3a"
    "5c8d2f701a4e96b3d7c0f5829a1e6d4b"
)

TEXT_EXTENSIONS = {
    ".txt", ".txtd", ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".jsx",
    ".tsx", ".html", ".htm", ".css", ".scss", ".sass", ".less", ".json",
    ".xml", ".yaml", ".yml", ".md", ".markdown", ".c", ".h", ".cpp",
    ".hpp", ".cc", ".cs", ".java", ".php", ".sql", ".sh", ".bash",
    ".bat", ".cmd", ".ps1", ".ini", ".cfg", ".conf", ".log", ".toml",
    ".rs", ".go", ".rb", ".swift", ".kt", ".lua", ".r", ".m", ".properties"
}

# Расширения, для которых textDark регистрируется как «Открыть с помощью» / замена Блокнота.
DEFAULT_APP_EXTENSIONS = [".txt", ".log", ".md", ".ini", ".cfg", ".conf", ".json", ".xml",
                          ".yaml", ".yml", ".toml", ".csv", ".txtd"]
PROG_ID = "textDark.File"

# ───────────────────────── Дизайн-токены ─────────────────────────
BG = "#0e0e0f"             # рамка окна, меню, строка состояния
EDITOR_BG = "#131314"      # поверхность редактора
SURFACE = "#1d1d20"        # кнопки, чипы вкладок, меню
SURFACE_HOVER = "#2a2a2e"  # наведение
BORDER = "#2a2a2d"         # тонкие границы
TEXT = "#ececee"           # основной текст
MUTED = "#8f8f96"          # второстепенный текст
ACCENT = "#ff5a1f"         # акцент
GUTTER_TEXT = "#5c5c63"    # номера строк

# Длительности анимаций (мс): короткие, чтобы интерфейс не ощущался медленным.
ANIM_FADE = 170
ANIM_SLIDE = 220


def app_data_dir():
    base = os.getenv("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

def resource_path(name):
    """Ищет ресурс (например logo.png) и рядом с main.py, и внутри собранного EXE."""
    bases = []
    if hasattr(sys, "_MEIPASS"):
        bases.append(Path(sys._MEIPASS))
    bases.append(Path(__file__).resolve().parent)
    for base in bases:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None

def default_editor_font():
    font = QFont()
    font.setFamilies(["Cascadia Code", "Cascadia Mono", "Consolas", "Courier New"])
    font.setStyleHint(QFont.Monospace)
    font.setPointSize(11)
    return font

def default_notebook_font():
    font = QFont("Segoe UI", 12)
    font.setStyleHint(QFont.SansSerif)
    return font

def mix_color(c1, c2, t):
    a, b = QColor(c1), QColor(c2)
    return QColor(int(a.red() + (b.red() - a.red()) * t),
                  int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t))

def encrypt_text(text: str) -> bytes:
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(APP_KEY).encrypt(nonce, text.encode("utf-8"), MAGIC)
    return MAGIC + nonce + encrypted

def decrypt_text(data: bytes) -> str:
    if not data.startswith(MAGIC):
        raise ValueError("Это не файл textDark или формат файла не поддерживается.")
    nonce = data[len(MAGIC):len(MAGIC)+12]
    payload = data[len(MAGIC)+12:]
    if len(nonce) != 12 or len(payload) < 16:
        raise ValueError("Файл повреждён или имеет неверный формат.")
    try:
        return AESGCM(APP_KEY).decrypt(nonce, payload, MAGIC).decode("utf-8")
    except Exception as exc:
        raise ValueError("Не удалось расшифровать файл: файл повреждён или создан несовместимой версией textDark.") from exc

def current_editor_style():
    value = str(QSettings("textDark", "textDark").value("editor_style", STYLE_PROGRAMMING))
    return value if value in (STYLE_PROGRAMMING, STYLE_NOTEBOOK) else STYLE_PROGRAMMING

def editor_block_count(editor):
    return editor.blockCount() if hasattr(editor, "blockCount") else editor.document().blockCount()

def _image_to_png_data(image):
    if isinstance(image, QPixmap):
        image = image.toImage()
    if not isinstance(image, QImage) or image.isNull():
        return None
    data = QByteArray()
    buffer = QBuffer(data)
    if not buffer.open(QIODevice.WriteOnly):
        return None
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data.toBase64()).decode("ascii")

def serialize_rich_html(editor):
    """Сохраняет ресурсы вставленных изображений прямо внутри HTML-документа."""
    result = editor.document().toHtml()
    pattern = re.compile("src=([\"'])(.*?)\\1", re.IGNORECASE)
    def replace_image(match):
        src = html_lib.unescape(match.group(2))
        if not src.startswith("textdark://image/"):
            return match.group(0)
        resource = editor.document().resource(QTextDocument.ImageResource, QUrl(src))
        encoded = _image_to_png_data(resource)
        if not encoded:
            return match.group(0)
        return f'{match.group(0)[:5]}data:image/png;base64,{encoded}{match.group(1)}'
    return pattern.sub(replace_image, result)

def load_rich_html(editor, source):
    """Поднимает встроенные PNG-ресурсы обратно в QTextDocument."""
    images = []
    pattern = re.compile("src=([\"])data:image/[^;]+;base64,([^'\"]+)\\1", re.IGNORECASE)
    def replace_image(match):
        try:
            image = QImage.fromData(base64.b64decode(match.group(2), validate=True))
            if image.isNull():
                return match.group(0)
            url = f"textdark://image/restored-{len(images)}.png"
            images.append((url, image))
            return f'src="{url}"'
        except Exception:
            return match.group(0)
    html_text = pattern.sub(replace_image, source)
    editor.setHtml(html_text)
    for url, image in images:
        editor.document().addResource(QTextDocument.ImageResource, QUrl(url), image)
    editor.document().markContentsDirty(0, max(1, editor.document().characterCount()))
    editor.document().adjustSize()
    editor.viewport().update()

def rich_html_to_plain_text(source):
    document = QTextDocument()
    document.setHtml(source)
    return document.toPlainText()

def serialize_tab(tab):
    if getattr(tab, "style", STYLE_PROGRAMMING) == STYLE_NOTEBOOK:
        return RICH_DOC_PREFIX + serialize_rich_html(tab.editor)
    return tab.editor.toPlainText()

def apply_theme(app):
    """Fusion + тёмная палитра: диалоги, списки и поля ввода автоматически становятся тёмными."""
    app.setStyle("Fusion")
    R = QPalette.ColorRole
    G = QPalette.ColorGroup
    pal = QPalette()
    pal.setColor(R.Window, QColor(BG))
    pal.setColor(R.WindowText, QColor(TEXT))
    pal.setColor(R.Base, QColor(EDITOR_BG))
    pal.setColor(R.AlternateBase, QColor(SURFACE))
    pal.setColor(R.ToolTipBase, QColor(SURFACE_HOVER))
    pal.setColor(R.ToolTipText, QColor(TEXT))
    pal.setColor(R.Text, QColor(TEXT))
    pal.setColor(R.Button, QColor(SURFACE))
    pal.setColor(R.ButtonText, QColor(TEXT))
    pal.setColor(R.BrightText, QColor("#ffffff"))
    pal.setColor(R.Link, QColor(ACCENT))
    pal.setColor(R.Highlight, QColor(ACCENT))
    pal.setColor(R.HighlightedText, QColor("#ffffff"))
    pal.setColor(R.PlaceholderText, QColor(MUTED))
    for role in (R.Text, R.ButtonText, R.WindowText):
        pal.setColor(G.Disabled, role, QColor("#5d5d63"))
    app.setPalette(pal)
    font = QFont()
    font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Helvetica Neue", "Arial"])
    font.setPointSize(10)
    app.setFont(font)

# ───────────────────────── Windows: замена Блокнота ─────────────────────────
def _launch_command():
    """Команда запуска и путь значка: для собранного EXE и для запуска из исходников."""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        return f'"{exe}" "%1"', exe
    py = Path(sys.executable)
    pythonw = py.with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else py
    script = Path(__file__).resolve()
    return f'"{runner}" "{script}" "%1"', str(runner)

def is_default_app_registered():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except OSError:
        return False

def txt_user_choice_is_textdark():
    """True, если Windows уже выбрала textDark для .txt (запись UserChoice)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.txt\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            return winreg.QueryValueEx(key, "ProgId")[0] == PROG_ID
    except OSError:
        return False

def _notify_shell():
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:
        pass

def register_default_app():
    import winreg
    command, icon = _launch_command()
    hive = winreg.HKEY_CURRENT_USER

    def set_value(path, name, value, kind=winreg.REG_SZ):
        with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, name, 0, kind, value)

    base = r"Software\Classes\textDark.File"
    set_value(base, "", "Текстовый документ (textDark)")
    set_value(base + r"\DefaultIcon", "", f"{icon},0")
    set_value(base + r"\shell\open\command", "", command)
    caps = r"Software\textDark\Capabilities"
    set_value(caps, "ApplicationName", "textDark")
    set_value(caps, "ApplicationDescription", "Тёмный текстовый редактор")
    for ext in DEFAULT_APP_EXTENSIONS:
        set_value(caps + r"\FileAssociations", ext, PROG_ID)
        set_value(rf"Software\Classes\{ext}\OpenWithProgids", PROG_ID, b"", winreg.REG_NONE)
    set_value(r"Software\Classes\.txtd", "", PROG_ID)  # собственный формат — привязываем полностью
    set_value(r"Software\RegisteredApplications", APP_NAME, caps)
    _notify_shell()

def _delete_tree(path):
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
    except OSError:
        return
    with key:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(path + "\\" + sub)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        pass

def unregister_default_app():
    import winreg
    for ext in DEFAULT_APP_EXTENSIONS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, PROG_ID)
        except OSError:
            pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.txtd", 0, winreg.KEY_ALL_ACCESS) as key:
            if winreg.QueryValueEx(key, "")[0] == PROG_ID:
                winreg.DeleteValue(key, "")
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except OSError:
        pass
    _delete_tree(r"Software\Classes\textDark.File")
    # Не удаляем Software\textDark целиком: там же хранятся пользовательские
    # параметры QSettings (масштаб, шрифт, фон и выбранный режим редактора).
    _delete_tree(r"Software\textDark\Capabilities")
    _notify_shell()

def open_default_apps_settings():
    for uri in (f"ms-settings:defaultapps?registeredAppUser={APP_NAME}", "ms-settings:defaultapps"):
        try:
            os.startfile(uri)
            return
        except Exception:
            continue

# ───────────────────────── Фон приложения ─────────────────────────
class BackgroundManager(QObject):
    """Хранит фоновое изображение и его настройки; тяжёлые операции (размытие, масштаб) кэшируются."""
    changed = Signal()
    MAX_SIDE = 1600
    BLUR_SIDE = 960

    def __init__(self):
        super().__init__()
        self.settings = QSettings("textDark", "textDark")
        self.path = str(self.settings.value("bg_path", "") or "")
        self.transparency = self._read_int("bg_transparency", 15)
        self.dim = self._read_int("bg_dim", 45)
        self.blur = self._read_int("bg_blur", 0)
        self._source = None
        self._blurred = None
        self._blurred_key = None
        self._margin = 0
        self._covers = {}
        self._load_source()

    def _read_int(self, key, default):
        try:
            return int(self.settings.value(key, default))
        except (TypeError, ValueError):
            return default

    @property
    def active(self):
        return self._source is not None

    def _reset_caches(self):
        self._blurred = None
        self._blurred_key = None
        self._margin = 0
        self._covers.clear()

    def _load_source(self):
        self._source = None
        self._reset_caches()
        if not self.path or not Path(self.path).is_file():
            return False
        image = QImage(self.path)
        if image.isNull():
            return False
        if max(image.width(), image.height()) > self.MAX_SIDE:
            image = image.scaled(self.MAX_SIDE, self.MAX_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._source = image
        return True

    def set_image(self, path):
        old = self.path
        self.path = path or ""
        if self.path and not self._load_source():
            self.path = old
            self._load_source()
            return False
        if not self.path:
            self._source = None
            self._reset_caches()
        self.settings.setValue("bg_path", self.path)
        self.changed.emit()
        return True

    def set_transparency(self, value):
        self.transparency = int(value)
        self.settings.setValue("bg_transparency", self.transparency)
        self.changed.emit()

    def set_dim(self, value):
        self.dim = int(value)
        self.settings.setValue("bg_dim", self.dim)
        self.changed.emit()

    def set_blur(self, value):
        self.blur = int(value)
        self.settings.setValue("bg_blur", self.blur)
        self.changed.emit()

    @staticmethod
    def _gaussian(image, radius):
        try:
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem(QPixmap.fromImage(image))
            effect = QGraphicsBlurEffect()
            effect.setBlurRadius(radius)
            effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
            item.setGraphicsEffect(effect)
            scene.addItem(item)
            out = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
            out.fill(Qt.transparent)
            painter = QPainter(out)
            scene.render(painter, QRectF(out.rect()), QRectF(0, 0, image.width(), image.height()))
            painter.end()
            return QPixmap.fromImage(out)
        except Exception:
            return QPixmap.fromImage(image)

    def _blurred_pixmap(self):
        if self._source is None:
            return None
        if self._blurred is not None and self._blurred_key == self.blur:
            return self._blurred
        source = self._source
        if self.blur <= 0:
            pixmap = QPixmap.fromImage(source)
            self._margin = 0
        else:
            work = source
            if max(work.width(), work.height()) > self.BLUR_SIDE:
                work = work.scaled(self.BLUR_SIDE, self.BLUR_SIDE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap = self._gaussian(work, self.blur)
            # Края после размытия полупрозрачные — обрезаем их при отрисовке.
            self._margin = min(int(self.blur * 1.6), min(pixmap.width(), pixmap.height()) // 4)
        self._blurred = pixmap
        self._blurred_key = self.blur
        self._covers.clear()
        return pixmap

    def cover(self, size):
        """Изображение, заполняющее size (режим cover), с кэшем по размеру."""
        if size.isEmpty():
            return None
        pixmap = self._blurred_pixmap()
        if pixmap is None:
            return None
        key = (size.width(), size.height())
        hit = self._covers.get(key)
        if hit is not None:
            return hit
        m = self._margin
        src = pixmap.copy(m, m, pixmap.width() - 2 * m, pixmap.height() - 2 * m) if m > 0 else pixmap
        scaled = src.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = (scaled.width() - size.width()) // 2
        y = (scaled.height() - size.height()) // 2
        result = scaled.copy(x, y, size.width(), size.height())
        if len(self._covers) > 6:
            self._covers.clear()
        self._covers[key] = result
        return result

    def paint_into(self, painter, rect_size):
        """Рисует фон (изображение + затемнение) в левом верхнем углу размера rect_size."""
        cover = self.cover(rect_size)
        if cover is None:
            return False
        painter.setOpacity(max(0.0, 1.0 - self.transparency / 100.0))
        painter.drawPixmap(0, 0, cover)
        painter.setOpacity(1.0)
        if self.dim > 0:
            painter.fillRect(QRect(0, 0, rect_size.width(), rect_size.height()), QColor(0, 0, 0, int(self.dim * 2.55)))
        return True

_BACKGROUND = None
def get_background():
    global _BACKGROUND
    if _BACKGROUND is None:
        _BACKGROUND = BackgroundManager()
    return _BACKGROUND

# ───────────────────────── Анимации и диалоги ─────────────────────────
class AnimatedMenu(QMenu):
    """Меню с плавным появлением: прозрачность 160 мс + сдвиг сверху вниз 200 мс."""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        # Прозрачный фон без системной тени, чтобы работали скруглённые углы меню.
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._group = None

    def setVisible(self, visible):
        if visible and not self.isVisible():
            self.setWindowOpacity(0.0)   # чтобы не было мигания до старта анимации
        super().setVisible(visible)

    def showEvent(self, event):
        super().showEvent(event)
        if self._group is not None:
            self._group.stop()
        end = self.pos()
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(160)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)
        slide = QPropertyAnimation(self, b"pos", self)
        slide.setDuration(200)
        slide.setStartValue(end - QPoint(0, 10))
        slide.setEndValue(end)
        slide.setEasingCurve(QEasingCurve.OutCubic)
        self._group = QParallelAnimationGroup(self)
        self._group.addAnimation(fade)
        self._group.addAnimation(slide)
        self.move(end - QPoint(0, 10))
        self._group.start()

    def hideEvent(self, event):
        if self._group is not None:
            self._group.stop()
        super().hideEvent(event)

class _DialogShowAnimator(QObject):
    """Фильтр событий одного диалога: плавное появление (170 мс) и сдвиг сверху (220 мс)."""
    def __init__(self, dialog):
        super().__init__(dialog)
        self._dialog = dialog
        self._done = False
        self._anims = []

    def eventFilter(self, obj, event):
        if obj is self._dialog and not self._done and event.type() == QEvent.Show:
            self._done = True
            end = obj.pos()
            fade = QPropertyAnimation(obj, b"windowOpacity", obj)
            fade.setDuration(ANIM_FADE)
            fade.setStartValue(0.0)
            fade.setEndValue(1.0)
            fade.setEasingCurve(QEasingCurve.OutCubic)
            slide = QPropertyAnimation(obj, b"pos", obj)
            slide.setDuration(ANIM_SLIDE)
            slide.setStartValue(end - QPoint(0, 14))
            slide.setEndValue(end)
            slide.setEasingCurve(QEasingCurve.OutCubic)
            self._anims = [fade, slide]
            obj.move(end - QPoint(0, 14))
            fade.start()
            slide.start()
        return False

def enable_dialog_animation(dialog):
    dialog.setWindowOpacity(0.0)
    dialog.installEventFilter(_DialogShowAnimator(dialog))

def _message_box(parent, icon, title, text, buttons):
    box = QMessageBox(icon, title, text, buttons, parent)
    for candidate in (QMessageBox.Save, QMessageBox.Yes, QMessageBox.Ok):
        if buttons & candidate:
            box.setDefaultButton(candidate)
            break
    enable_dialog_animation(box)
    return box

def msg_info(parent, title, text):
    _message_box(parent, QMessageBox.Information, title, text, QMessageBox.Ok).exec()

def msg_warn(parent, title, text):
    _message_box(parent, QMessageBox.Warning, title, text, QMessageBox.Ok).exec()

def msg_crit(parent, title, text):
    _message_box(parent, QMessageBox.Critical, title, text, QMessageBox.Ok).exec()

def msg_question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No):
    box = _message_box(parent, QMessageBox.Question, title, text, buttons)
    box.exec()
    clicked = box.clickedButton()
    if clicked is None:
        return QMessageBox.Cancel if (buttons & QMessageBox.Cancel) else QMessageBox.No
    return box.standardButton(clicked)

def ask_text(parent, title, label, text=""):
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.TextInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(text)
    enable_dialog_animation(dialog)
    ok = bool(dialog.exec())
    return dialog.textValue(), ok

def ask_int(parent, title, label, value, minimum, maximum):
    dialog = QInputDialog(parent)
    dialog.setInputMode(QInputDialog.IntInput)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setIntRange(minimum, maximum)
    dialog.setIntValue(value)
    enable_dialog_animation(dialog)
    ok = bool(dialog.exec())
    return dialog.intValue(), ok

class FadeVeil(QWidget):
    """Тонкая «вуаль» поверх страницы: плавно исчезает за 180 мс при переключении вкладок."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._alpha = 0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setStartValue(215)
        self._anim.setEndValue(0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_value)
        self._anim.finished.connect(self.hide)
        self.hide()

    def _on_value(self, value):
        self._alpha = int(value)
        self.update()

    def play(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self._anim.stop()
        self.setGeometry(parent.rect())
        self._alpha = 215
        self.raise_()
        self.show()
        self._anim.start()

    def paintEvent(self, event):
        if self._alpha <= 0:
            return
        color = QColor(EDITOR_BG)
        color.setAlpha(self._alpha)
        painter = QPainter(self)
        painter.fillRect(self.rect(), color)

class ToggleSwitch(QAbstractButton):
    """Переключатель с плавной анимацией ползунка (160 мс)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_value)
        self.toggled.connect(self._animate)

    def _on_value(self, value):
        self._pos = float(value)
        self.update()

    def _animate(self, checked):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def set_checked_silent(self, value):
        self.blockSignals(True)
        self.setChecked(value)
        self.blockSignals(False)
        self._pos = 1.0 if value else 0.0
        self.update()

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = mix_color("#3a3a3f", ACCENT, self._pos)
        if not self.isEnabled():
            track = QColor("#2a2a2d")
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(self.rect()), 13, 13)
        knob = 20
        x = 3 + self._pos * (self.width() - knob - 6)
        painter.setBrush(QColor("#ffffff") if self.isEnabled() else QColor("#6a6a70"))
        painter.drawEllipse(QRectF(x, 3, knob, knob))

class TabCloseButton(QAbstractButton):
    """Кнопка закрытия вкладки. Рисуется вручную; для несохранённого файла показывает точку,
    которая при наведении плавно превращается в крестик."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TabCloseButton")
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip("Закрыть вкладку")
        self._hover = 0.0
        self._modified = False
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_value)

    def sizeHint(self):
        return QSize(20, 20)

    def set_modified(self, value):
        value = bool(value)
        if value != self._modified:
            self._modified = value
            self.update()

    def _on_value(self, value):
        self._hover = float(value)
        self.update()

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_selected_tab(self):
        bar = self.parentWidget()
        if isinstance(bar, QTabBar):
            index = bar.currentIndex()
            if index >= 0:
                return bar.tabButton(index, QTabBar.RightSide) is self
        return False

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        h = self._hover
        selected = self._on_selected_tab()
        cx, cy = self.width() / 2, self.height() / 2

        if h > 0.01 or self.isDown():
            if selected:
                alpha = 70 if self.isDown() else 40
                bg = QColor(0, 0, 0, int(alpha * max(h, 0.6 if self.isDown() else 0)))
            else:
                alpha = 56 if self.isDown() else 34
                bg = QColor(255, 255, 255, int(alpha * max(h, 0.6 if self.isDown() else 0)))
            painter.setPen(Qt.NoPen)
            painter.setBrush(bg)
            painter.drawEllipse(QRectF(self.rect()).adjusted(1, 1, -1, -1))

        x_alpha = h if self._modified else 1.0
        dot_alpha = (1.0 - h) if self._modified else 0.0

        if x_alpha > 0.01:
            idle, active = (QColor("#4a4a50"), QColor(BG)) if selected else (QColor("#9a9aa2"), QColor("#ffffff"))
            color = mix_color(idle, active, h)
            color.setAlphaF(x_alpha)
            pen = QPen(color, 1.6)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            d = 3.6
            painter.drawLine(QPointF(cx - d, cy - d), QPointF(cx + d, cy + d))
            painter.drawLine(QPointF(cx - d, cy + d), QPointF(cx + d, cy - d))
        if dot_alpha > 0.01:
            color = QColor(ACCENT)
            color.setAlphaF(dot_alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(cx, cy), 4.0, 4.0)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_line_numbers(event)

class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, document, extension):
        super().__init__(document)
        self.extension = extension.lower()
        self.rules = []
        self._add(r"\b(class|def|return|if|elif|else|for|while|in|is|not|and|or|try|except|finally|with|as|import|from|pass|break|continue|lambda|yield|async|await|function|const|let|var|new|this|public|private|static|void|int|string|bool|true|false|null|None|True|False)\b", "#c792ea", True)
        self._add(r"\b\d+(?:\.\d+)?\b", "#f78c6c")
        self._add(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', "#c3e88d")
        self._add(r"#[^\n]*", "#697386")
        self._add(r"//[^\n]*", "#697386")
        self._add(r"\b[A-Z_]{3,}\b", "#ffcb6b", True)
        self._add(r"\b[A-Za-z_]\w*(?=\s*\()", "#82aaff")
        self.comment_start = "/*"
        self.comment_end = "*/"

    def _add(self, pattern, color, bold=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        self.rules.append((pattern, fmt))

    def highlightBlock(self, text):
        import re
        for pattern, fmt in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end()-match.start(), fmt)
        if self.extension in {".js", ".ts", ".jsx", ".tsx", ".css", ".scss", ".java", ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".go", ".rs"}:
            start = text.find(self.comment_start)
            if start >= 0:
                end = text.find(self.comment_end, start + 2)
                if end < 0:
                    self.setFormat(start, len(text)-start, QColor("#697386"))
                    self.setCurrentBlockState(1)
                else:
                    self.setFormat(start, end+2-start, QColor("#697386"))
        if self.previousBlockState() == 1:
            end = text.find(self.comment_end)
            if end < 0:
                self.setFormat(0, len(text), QColor("#697386"))
                self.setCurrentBlockState(1)
            else:
                self.setFormat(0, end+2, QColor("#697386"))
                self.setCurrentBlockState(0)

class Editor(QPlainTextEdit):
    zoomRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.gutter = LineNumberArea(self)
        # Фон редактора прозрачный: его рисует DocumentTab (цвет или изображение из настроек).
        self.viewport().setAutoFillBackground(False)
        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(lambda: self.gutter.update())
        self.update_gutter_width(0)
        self.highlight_current_line()
        self.setCursorWidth(2)
        self.setFont(default_editor_font())   # setFont также пересчитывает табуляцию и ширину нумерации
        self.highlighter = None

    # Qt не вызывает виртуальный setFont, поэтому пересчёт метрик делаем сами.
    def setFont(self, font):
        super().setFont(font)
        self.refresh_metrics()

    def refresh_metrics(self):
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.update_gutter_width(0)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))
        self.gutter.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoomRequested.emit(1 if delta > 0 else -1)
                event.accept()
                return
        super().wheelEvent(event)

    def line_number_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 30 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_gutter_width(self, _):
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_gutter_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.line_number_width(), cr.height()))

    def paint_line_numbers(self, event):
        painter = QPainter(self.gutter)   # фон не заливаем: за ним рисуется фон вкладки
        painter.setFont(self.font())
        current = self.textCursor().blockNumber()
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(ACCENT) if number == current else QColor(GUTTER_TEXT))
                painter.drawText(0, top, self.gutter.width()-14, self.fontMetrics().height(),
                                 Qt.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

    def highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            sel = QTextEditExtraSelection()
            sel.format.setBackground(QColor(255, 255, 255, 9))   # полупрозрачная: видно и на фоне-картинке
            sel.format.setProperty(QTextFormat.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)

    def keyPressEvent(self, event):
        pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        closing = set(pairs.values())
        cursor = self.textCursor()
        key = event.text()
        # Если следующий символ уже совпадает с вводимой закрывающей скобкой/кавычкой — просто перешагиваем её.
        if key and key in closing and not cursor.hasSelection():
            if self.document().characterAt(cursor.position()) == key:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return
        if key and key in pairs and not cursor.hasSelection():
            # В середине слова (don't, it's) кавычки не дублируем.
            prev = self.document().characterAt(cursor.position() - 1) if cursor.position() > 0 else ""
            if not (key in ('"', "'") and prev.isalnum()):
                cursor.insertText(key + pairs[key])
                cursor.movePosition(QTextCursor.Left)
                self.setTextCursor(cursor)
                return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            line = cursor.block().text()
            indent = len(line) - len(line.lstrip(" \t"))
            trimmed = line.rstrip()
            extra = 1 if trimmed.endswith(("{", "[", "(")) else 0
            super().keyPressEvent(event)
            self.insertPlainText(" " * (indent + extra * 4))
            return
        if event.key() == Qt.Key_Tab:
            if cursor.hasSelection():
                cursor.beginEditBlock()
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                cursor.setPosition(start)
                cursor.movePosition(QTextCursor.StartOfLine)
                while cursor.position() <= end:
                    cursor.insertText("    ")
                    if not cursor.movePosition(QTextCursor.Down):
                        break
                cursor.endEditBlock()
            else:
                self.insertPlainText("    ")
            return
        super().keyPressEvent(event)

# Qt's extra-selection class is exported from QTextEdit.
QTextEditExtraSelection = QTextEdit.ExtraSelection

class NotebookEditor(QTextEdit):
    """Редактор обычных документов: форматирование, изображения, таблицы и списки."""
    zoomRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.viewport().setAutoFillBackground(False)
        self.setFont(default_notebook_font())
        self._zoom_level_applied = 0

    def refresh_metrics(self):
        # Общий интерфейс с программным редактором; отдельный gutter здесь не нужен.
        return

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoomRequested.emit(1 if delta > 0 else -1)
                event.accept()
                return
        super().wheelEvent(event)

class DocumentTab(QWidget):
    def __init__(self, path=None, text="", rich_html=None, style=None):
        super().__init__()
        self.path = Path(path) if path else None
        self.modified = False
        self.style = style or current_editor_style()
        self.editor = self._create_editor(self.style)
        if rich_html is not None and self.style == STYLE_NOTEBOOK:
            load_rich_html(self.editor, rich_html)
        else:
            self.editor.setPlainText(text)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.editor.document().modificationChanged.connect(self._modified)
        self.set_highlighter()
        self.veil = FadeVeil(self)
        get_background().changed.connect(self._bg_changed)

    def _create_editor(self, style):
        return Editor() if style == STYLE_PROGRAMMING else NotebookEditor()

    def _bg_changed(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(EDITOR_BG))
        bg = get_background()
        if bg.active:
            bg.paint_into(painter, self.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.veil.setGeometry(self.rect())

    def play_fade(self):
        self.veil.play()

    def _modified(self, value):
        self.modified = value

    def set_highlighter(self):
        if isinstance(self.editor, Editor):
            ext = self.path.suffix if self.path else ""
            self.editor.highlighter = CodeHighlighter(self.editor.document(), ext)
        else:
            self.editor.highlighter = None

    def switch_style(self, style):
        if style == self.style:
            return
        old = self.editor
        old_text = old.toPlainText()
        old_font = old.font()
        old_cursor = old.textCursor()
        old_position = old_cursor.position()
        new = self._create_editor(style)
        new.setPlainText(old_text)
        new.setFont(old_font)
        cursor = new.textCursor()
        cursor.setPosition(min(old_position, max(0, new.document().characterCount() - 1)))
        new.setTextCursor(cursor)
        new.document().modificationChanged.connect(self._modified)
        self.layout().replaceWidget(old, new)
        old.setParent(None)
        old.deleteLater()
        self.editor = new
        self.style = style
        self.set_highlighter()
        # Режим меняет тип документа; просим сохранить преобразованный вариант.
        self.editor.document().setModified(True)

    @property
    def title(self):
        return self.path.name if self.path else "Безымянный"


class BgPreview(QWidget):
    """Живой предпросмотр фона вместе с примером текста."""
    def __init__(self, bg, parent=None):
        super().__init__(parent)
        self.bg = bg
        self.setFixedHeight(150)
        self.setMinimumWidth(300)
        self.bg.changed.connect(self._refresh)

    def _refresh(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor(EDITOR_BG))
        has_image = self.bg.active and self.bg.paint_into(painter, self.size())
        font = default_editor_font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor("#c792ea"))
        painter.drawText(18, 40, "def")
        painter.setPen(QColor("#82aaff"))
        painter.drawText(50, 40, "hello():")
        painter.setPen(QColor("#c3e88d"))
        painter.drawText(34, 64, '"Пример текста textDark"')
        painter.setPen(QColor(TEXT))
        painter.drawText(34, 88, "Читаемость на выбранном фоне")
        if not has_image:
            painter.setPen(QColor(MUTED))
            painter.drawText(18, 130, "Фон не выбран")
        painter.setClipping(False)
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.bg = get_background()
        self.setWindowTitle("Настройки textDark")
        self.setMinimumSize(680, 570)
        enable_dialog_animation(self)
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(12)
        title = QLabel("Настройки")
        title.setObjectName("DlgTitle")
        root.addWidget(title)

        self.pages = QSettingsTabs()
        root.addWidget(self.pages, 1)
        self._build_general_page()
        self._build_advanced_page()

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        done = QPushButton("Готово")
        done.setDefault(True)
        done.clicked.connect(self.apply_and_close)
        buttons.addWidget(done)
        root.addLayout(buttons)

        self._blur_timer = QTimer(self)
        self._blur_timer.setSingleShot(True)
        self._blur_timer.setInterval(140)
        self._blur_timer.timeout.connect(lambda: self.bg.set_blur(self.s_blur.value()))
        self.choose_btn.clicked.connect(self.choose_image)
        self.clear_btn.clicked.connect(self.clear_image)
        self.s_transp.valueChanged.connect(self.bg.set_transparency)
        self.s_dim.valueChanged.connect(self.bg.set_dim)
        self.s_blur.valueChanged.connect(lambda _v: self._blur_timer.start())
        if sys.platform == "win32":
            self.switch.set_checked_silent(is_default_app_registered())
            self.switch.toggled.connect(self._toggle_default)
        else:
            self.switch.setEnabled(False)
        self._refresh_system_hint()
        self._refresh_enabled()

    def _build_general_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)
        root.addWidget(self._section("Стиль редактора"))
        self.style_combo = QComboBox()
        self.style_combo.addItem("Программирование — номера строк и подсветка кода", STYLE_PROGRAMMING)
        self.style_combo.addItem("Блокнот — форматированный текст, картинки и таблицы", STYLE_NOTEBOOK)
        current = current_editor_style()
        self.style_combo.setCurrentIndex(max(0, self.style_combo.findData(current)))
        root.addWidget(self.style_combo)
        style_hint = QLabel("Режим «Программирование» сохраняет привычный редактор кода. Режим «Блокнот» поддерживает форматирование, изображения и таблицы.")
        style_hint.setObjectName("Hint")
        style_hint.setWordWrap(True)
        root.addWidget(style_hint)
        root.addSpacing(4)
        root.addWidget(self._section("Фон приложения"))
        hint = QLabel("Изображение отображается позади текста в окне редактора.")
        hint.setObjectName("Hint")
        root.addWidget(hint)
        self.preview = BgPreview(self.bg)
        root.addWidget(self.preview)
        buttons = QHBoxLayout()
        self.choose_btn = QPushButton("Выбрать изображение...")
        self.clear_btn = QPushButton("Убрать фон")
        buttons.addWidget(self.choose_btn)
        buttons.addWidget(self.clear_btn)
        buttons.addStretch(1)
        root.addLayout(buttons)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)
        self.s_transp, self.l_transp = self._slider(grid, 0, "Прозрачность", 0, 100, self.bg.transparency, "%")
        self.s_dim, self.l_dim = self._slider(grid, 1, "Затемнение", 0, 95, self.bg.dim, "%")
        self.s_blur, self.l_blur = self._slider(grid, 2, "Размытие (блюр)", 0, 40, self.bg.blur, " px")
        root.addLayout(grid)
        root.addStretch(1)
        self.pages.addTab(page, "Общие")

    def _build_advanced_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)
        root.addWidget(self._section("Системные настройки"))
        row = QHBoxLayout()
        column = QVBoxLayout()
        column.setSpacing(2)
        row_title = QLabel("Использовать textDark для текстовых файлов")
        row_title.setObjectName("RowTitle")
        self.sys_hint = QLabel("")
        self.sys_hint.setObjectName("Hint")
        self.sys_hint.setWordWrap(True)
        column.addWidget(row_title)
        column.addWidget(self.sys_hint)
        row.addLayout(column, 1)
        self.switch = ToggleSwitch()
        row.addWidget(self.switch, 0, Qt.AlignVCenter)
        root.addLayout(row)
        root.addWidget(self._section("Сворачивание в трей"))
        self.tray_check = QCheckBox("При нажатии на крестик сворачивать textDark в системный трей")
        self.tray_check.setChecked(bool(self.parent_window.settings.value("minimize_to_tray", False, type=bool)))
        if sys.platform != "win32" or not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_check.setEnabled(False)
            self.tray_check.setToolTip("Системный трей недоступен в этой среде Windows.")
        root.addWidget(self.tray_check)
        tray_hint = QLabel("Приложение продолжит работать в фоне. Полностью закрыть его можно через значок textDark в трее.")
        tray_hint.setObjectName("Hint")
        tray_hint.setWordWrap(True)
        root.addWidget(tray_hint)
        root.addWidget(self._section("Свои сочетания клавиш"))
        shortcut_hint = QLabel("Нажми на поле и задай новое сочетание. Пустое поле отключает комбинацию. Изменения применятся после нажатия «Готово».")
        shortcut_hint.setObjectName("Hint")
        shortcut_hint.setWordWrap(True)
        root.addWidget(shortcut_hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        shortcut_widget = QWidget()
        form = QFormLayout(shortcut_widget)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.shortcut_edits = []
        for label, action in self.parent_window.shortcut_actions:
            edit = QKeySequenceEdit(action.shortcut())
            edit.setMaximumSequenceLength(2)
            form.addRow(label, edit)
            self.shortcut_edits.append((action, edit))
        scroll.setWidget(shortcut_widget)
        root.addWidget(scroll, 1)
        reset = QPushButton("Сбросить сочетания по умолчанию")
        reset.clicked.connect(self.reset_shortcuts)
        root.addWidget(reset, 0, Qt.AlignRight)
        self.pages.addTab(page, "Расширенные")

    def _section(self, text):
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _slider(self, grid, row, title, minimum, maximum, value, unit):
        name = QLabel(title)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        value_label = QLabel(f"{value}{unit}")
        value_label.setObjectName("Hint")
        value_label.setMinimumWidth(48)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider.valueChanged.connect(lambda v, l=value_label, u=unit: l.setText(f"{v}{u}"))
        grid.addWidget(name, row, 0)
        grid.addWidget(slider, row, 1)
        grid.addWidget(value_label, row, 2)
        return slider, value_label

    def _refresh_enabled(self):
        enabled = self.bg.active
        for widget in (self.s_transp, self.s_dim, self.s_blur, self.clear_btn):
            widget.setEnabled(enabled)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбор фона", "", "Изображения (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;Все файлы (*.*)")
        if not path:
            return
        if not self.bg.set_image(path):
            msg_warn(self, "Не удалось загрузить фон", "Не получилось открыть это изображение. Выберите другой файл.")
        self._refresh_enabled()

    def clear_image(self):
        self.bg.set_image("")
        self._refresh_enabled()

    def _refresh_system_hint(self):
        if sys.platform != "win32":
            self.sys_hint.setText("Доступно только в Windows.")
        elif txt_user_choice_is_textdark():
            self.sys_hint.setText("textDark назначен программой по умолчанию для .txt.")
        elif is_default_app_registered():
            self.sys_hint.setText("textDark зарегистрирован. Осталось выбрать его в окне Windows «Приложения по умолчанию».")
        else:
            self.sys_hint.setText("Регистрирует textDark для открытия .txt, .log, .md, .json и других текстовых файлов, а также .txtd.")

    def _toggle_default(self, checked):
        try:
            if checked:
                register_default_app()
                self._refresh_system_hint()
                msg_info(self, "Приложение по умолчанию",
                         "textDark зарегистрирован в системе, файлы .txtd уже привязаны.\n\n"
                         "Windows не позволяет программам самостоятельно менять приложение по умолчанию для .txt, "
                         "поэтому сейчас откроется окно «Приложения по умолчанию». Выберите там textDark.")
                open_default_apps_settings()
            else:
                unregister_default_app()
                self._refresh_system_hint()
        except Exception as exc:
            msg_crit(self, "Ошибка", f"Не удалось изменить настройки системы:\n{exc}")
            self.switch.set_checked_silent(is_default_app_registered())
            self._refresh_system_hint()

    def reset_shortcuts(self):
        for action, edit in self.shortcut_edits:
            default = self.parent_window.shortcut_defaults.get(action.objectName(), "")
            edit.setKeySequence(QKeySequence(default))

    def apply_and_close(self):
        # Не допускаем случайного назначения одного сочетания нескольким командам.
        assignments = {}
        conflicts = []
        for action, edit in self.shortcut_edits:
            sequence = edit.keySequence()
            value = sequence.toString(QKeySequence.PortableText)
            if not value:
                continue
            if value in assignments:
                conflicts.append(f"{value}: {assignments[value]} и {action.text()}")
            else:
                assignments[value] = action.text()
        if conflicts:
            msg_warn(self, "Повторяющиеся сочетания клавиш",
                     "Одно сочетание назначено нескольким действиям. Измени повторы:\n\n" + "\n".join(conflicts))
            return

        new_style = self.style_combo.currentData()
        if not self.parent_window.set_editor_style(new_style):
            self.style_combo.setCurrentIndex(max(0, self.style_combo.findData(current_editor_style())))
        self.parent_window.settings.setValue("minimize_to_tray", self.tray_check.isChecked())
        self.parent_window.configure_tray(self.tray_check.isChecked())
        for action, edit in self.shortcut_edits:
            self.parent_window.update_shortcut(action, edit.keySequence())
        self.accept()


class TextDark(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.settings = QSettings("textDark", "textDark")
        self._saved_font = self._load_saved_font()
        self._titlebar_done = False
        self._fade_anim = None
        self._really_quit = False
        self.tray_icon = None
        self.zoom_level = self._read_zoom_level()
        self.action_map = {}
        self.shortcut_actions = []
        self.shortcut_defaults = {}
        self.setWindowTitle("textDark - Текстовый редактор")
        self._set_app_icon()
        self.resize(1180, 780)
        self.setMinimumSize(760, 520)
        geometry = self.settings.value("window_geometry")
        if geometry:
            try:
                self.restoreGeometry(geometry)
            except Exception:
                pass
        self.setWindowOpacity(0.0)   # плавное появление окна стартует в showEvent
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.tabs.currentChanged.connect(self._refresh_close_buttons)
        self.tabs.currentChanged.connect(self._play_tab_fade)
        self.setCentralWidget(self.tabs)
        self._build_ui()
        self._apply_style()
        self._apply_shortcut_overrides()
        self._apply_mode_menus()
        if not initial_file:
            self.new_tab()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_recovery)
        self.autosave_timer.start(45000)
        if initial_file:
            self.open_file(initial_file)
        if bool(self.settings.value("minimize_to_tray", False, type=bool)):
            self.configure_tray(True)

    def current_tab(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, DocumentTab) else None

    def current_editor(self):
        tab = self.current_tab()
        return tab.editor if tab else None

    def _set_app_icon(self):
        logo = resource_path("logo.png")
        if logo:
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(logo)))
            QApplication.setWindowIcon(QIcon(str(logo)))

    def showEvent(self, event):
        super().showEvent(event)
        if not self._titlebar_done:
            self._titlebar_done = True
            self._apply_dark_titlebar()
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity", self)
            self._fade_anim.setDuration(240)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._fade_anim.start()

    def _apply_dark_titlebar(self):
        """Тёмный заголовок окна в Windows 10/11 (на других системах ничего не делает)."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            def set_attr(attr, value):
                v = ctypes.c_int(value)
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))
            set_attr(20, 1)           # DWMWA_USE_IMMERSIVE_DARK_MODE
            set_attr(19, 1)           # то же для ранних сборок Windows 10
            set_attr(35, 0x000F0E0E)  # цвет заголовка (Windows 11), формат 0x00BBGGRR = #0e0e0f
            set_attr(36, 0x00EEECEC)  # цвет текста заголовка (Windows 11)
        except Exception:
            pass

    def _read_zoom_level(self):
        try:
            return max(-5, min(24, int(self.settings.value("zoom_level", 0))))
        except (TypeError, ValueError):
            return 0

    def _load_saved_font(self):
        value = self.settings.value("editor_font", "")
        if value:
            font = QFont()
            if font.fromString(str(value)):
                return font
        return None

    def _apply_saved_font(self, editor):
        if self._saved_font is not None:
            base = QFont(self._saved_font)
        elif isinstance(editor, NotebookEditor):
            base = default_notebook_font()
        else:
            base = default_editor_font()
        if isinstance(editor, NotebookEditor):
            base.setPointSize(max(6, min(48, base.pointSize())))
            editor.setFont(base)
            applied = int(getattr(editor, "_zoom_level_applied", 0))
            delta = self.zoom_level - applied
            if delta > 0:
                editor.zoomIn(delta)
            elif delta < 0:
                editor.zoomOut(-delta)
            editor._zoom_level_applied = self.zoom_level
        else:
            base.setPointSize(max(6, min(48, base.pointSize() + self.zoom_level)))
            editor.setFont(base)

    def _build_ui(self):
        bar = self.menuBar()
        self._make_menu(bar, "Файл", [
            ("Создать", self.new_tab, "Ctrl+N"), ("Новое окно", self.new_window, "Ctrl+Shift+N"),
            ("Открыть...", self.open_dialog, "Ctrl+O"), ("Открыть в новом окне...", self.open_in_new_window, "Ctrl+Shift+O"),
            None, ("Сохранить", self.save, "Ctrl+S"), ("Сохранить как...", self.save_as, "Ctrl+Shift+S"),
            ("Сохранить копию...", self.save_copy, None), ("Экспорт в TXT", self.export_txt, None),
            None, ("Настройки...", self.open_settings, "Ctrl+,"), ("Открыть папку файла", self.open_file_folder, None),
            ("Выход", self.exit_from_tray, None)])
        self._make_menu(bar, "Правка", [
            ("Отменить", lambda: self.run_editor("undo"), "Ctrl+Z"), ("Повторить", lambda: self.run_editor("redo"), "Ctrl+Y"),
            None, ("Вырезать", lambda: self.run_editor("cut"), "Ctrl+X"), ("Копировать", lambda: self.run_editor("copy"), "Ctrl+C"),
            ("Вставить", lambda: self.run_editor("paste"), "Ctrl+V"), ("Вставить без форматирования", self.paste_plain, "Ctrl+Shift+V"),
            ("Удалить выделенное", self.delete_selection, "Delete"), ("Выделить всё", lambda: self.run_editor("selectAll"), "Ctrl+A"),
            None, ("Найти...", self.find_text, "Ctrl+F"), ("Заменить...", self.replace_text, "Ctrl+H"),
            ("Перейти к строке...", self.goto_line, "Ctrl+G"), None,
            ("Выделить строку", self.select_line, None), ("Дублировать строку", self.duplicate_line, "Ctrl+D"),
            ("Удалить строку", self.delete_line, None), ("Переместить строку вверх", lambda: self.move_line(-1), "Alt+Up"),
            ("Переместить строку вниз", lambda: self.move_line(1), "Alt+Down"), ("Удалить пустые строки", self.remove_empty_lines, None),
            None, ("Сделать строки ПРОПИСНЫМИ", lambda: self.transform_selection(str.upper), None),
            ("Сделать строки строчными", lambda: self.transform_selection(str.lower), None),
            ("Начать Каждое Слово С Заглавной", lambda: self.transform_selection(str.title), None),
            ("Обратить регистр", self.swap_case, None), ("Повторить последнее действие", self.repeat_last_action, "Ctrl+Shift+R")])
        self._make_menu(bar, "Формат", [
            ("Шрифт...", self.choose_font, None), ("Жирный", lambda: self.toggle_format("bold"), "Ctrl+B"),
            ("Курсив", lambda: self.toggle_format("italic"), "Ctrl+I"), ("Подчёркнутый", lambda: self.toggle_format("underline"), "Ctrl+U"),
            ("Зачёркнутый", lambda: self.toggle_format("strike"), None), None,
            ("Заголовок", self.format_heading, None), ("Цитата", self.format_quote, None),
            ("Маркированный список", lambda: self.insert_list(QTextListFormat.ListDisc), None),
            ("Нумерованный список", lambda: self.insert_list(QTextListFormat.ListDecimal), None),
            ("Очистить форматирование", self.clear_formatting, None)])
        self._make_menu(bar, "Вставка", [
            ("Дата", lambda: self.insert_text(datetime.now().strftime("%d.%m.%Y")), None),
            ("Время", lambda: self.insert_text(datetime.now().strftime("%H:%M:%S")), None),
            ("Разделитель", self.insert_separator, None),
            ("Символ...", self.insert_symbol, None), ("Эмодзи...", self.insert_emoji, None),
            ("Путь к файлу...", self.insert_file_path, None), ("Ссылка...", self.insert_link, None),
            None, ("Вставить изображение...", self.insert_image, None), ("Вставить таблицу...", self.insert_table, None),
            ("Объединить ячейки", self.merge_table_cells, None), ("Разделить ячейку", self.split_table_cell, None),
            ("Добавить строку ниже", self.add_table_row, None), ("Добавить столбец справа", self.add_table_column, None),
            ("Удалить строку таблицы", self.delete_table_row, None), ("Удалить столбец таблицы", self.delete_table_column, None),
            ("Убрать вертикальные линии выделения", lambda: self.set_table_inner_borders("vertical", False), None),
            ("Убрать горизонтальные линии выделения", lambda: self.set_table_inner_borders("horizontal", False), None),
            ("Вернуть границы выделения", lambda: self.set_table_inner_borders("all", True), None)])
        self._make_menu(bar, "Вид", [
            ("Увеличить масштаб", lambda: self.zoom(1), "Ctrl+="), ("Уменьшить масштаб", lambda: self.zoom(-1), "Ctrl+-"),
            ("Сбросить масштаб", self.reset_zoom, "Ctrl+0"), ("Полноэкранный режим", self.toggle_fullscreen, "F11")])
        self._make_menu(bar, "Инструменты", [
            ("Статистика документа", self.document_stats, None), ("Очистить документ", self.clear_document, None),
            ("Вставить содержимое буфера", lambda: self.insert_text(QApplication.clipboard().text()), None),
            ("Проверить скобки", self.check_brackets, None), ("Удалить дубли строк", self.remove_duplicate_lines, None),
            ("Перевернуть строки", self.reverse_lines, None), ("Открыть папку резервных копий", self.open_backup_folder, None)])
        self._make_menu(bar, "Справка", [
            ("Сочетания клавиш", self.show_shortcuts, None), ("Сайт / Скачать", self.open_website, None),
            ("О программе textDark", self.about, None)])

        corner = QWidget()
        corner_layout = QHBoxLayout(corner)
        corner_layout.setContentsMargins(6, 0, 12, 0)
        add_btn = QToolButton()
        add_btn.setObjectName("NewTabButton")
        add_btn.setText("+")
        add_btn.setFixedSize(30, 30)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setToolTip("Новая вкладка (Ctrl+N)")
        add_btn.clicked.connect(self.new_tab)
        corner_layout.addWidget(add_btn)
        self.tabs.setCornerWidget(corner, Qt.TopRightCorner)

        self.status = QStatusBar()
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)
        self.lbl_pos = QLabel("")
        self.lbl_kind = QLabel("")
        self.lbl_enc = QLabel("UTF-8")
        for label in (self.lbl_pos, self.lbl_kind, self.lbl_enc):
            self.status.addPermanentWidget(label)
        self.status.showMessage("Готово · TXT / CODE / TXTD")

    def _make_menu(self, bar, title, items):
        menu = AnimatedMenu(title, self)
        bar.addMenu(menu)
        for item in items:
            if item is None:
                menu.addSeparator()
                continue
            label, callback, shortcut = item
            action = QAction(label, self)
            action.setObjectName("action_" + hashlib.sha1(label.encode("utf-8")).hexdigest()[:12])
            action.triggered.connect(callback)
            if shortcut:
                sequence = QKeySequence(shortcut)
                action.setShortcut(sequence)
                action.setShortcutContext(Qt.WindowShortcut)
            self.action_map[label] = action
            self.shortcut_actions.append((label, action))
            self.shortcut_defaults[action.objectName()] = action.shortcut().toString(QKeySequence.PortableText)
            menu.addAction(action)
        return menu

    def _apply_shortcut_overrides(self):
        for _label, action in self.shortcut_actions:
            value = self.settings.value("shortcuts/" + action.objectName(), None)
            if value is not None:
                action.setShortcut(QKeySequence(str(value)))

    def update_shortcut(self, action, sequence):
        action.setShortcut(sequence)
        key = "shortcuts/" + action.objectName()
        value = sequence.toString(QKeySequence.PortableText)
        default = self.shortcut_defaults.get(action.objectName(), "")
        if value == default:
            self.settings.remove(key)
        else:
            self.settings.setValue(key, value)

    def _apply_mode_menus(self):
        style = current_editor_style()
        programming_only = {
            "Перейти к строке...", "Выделить строку", "Дублировать строку", "Удалить строку",
            "Переместить строку вверх", "Переместить строку вниз", "Удалить пустые строки",
            "Сделать строки ПРОПИСНЫМИ", "Сделать строки строчными", "Начать Каждое Слово С Заглавной",
            "Обратить регистр", "Проверить скобки", "Удалить дубли строк", "Перевернуть строки"
        }
        notebook_only = {
            "Заголовок", "Цитата", "Маркированный список", "Нумерованный список", "Очистить форматирование",
            "Вставить изображение...", "Вставить таблицу...", "Объединить ячейки", "Разделить ячейку", "Добавить строку ниже",
            "Добавить столбец справа", "Удалить строку таблицы", "Удалить столбец таблицы",
            "Убрать вертикальные линии выделения", "Убрать горизонтальные линии выделения", "Вернуть границы выделения"
        }
        for label, action in self.action_map.items():
            if label in programming_only:
                action.setVisible(style == STYLE_PROGRAMMING)
                action.setEnabled(style == STYLE_PROGRAMMING)
            elif label in notebook_only:
                action.setVisible(style == STYLE_NOTEBOOK)
                action.setEnabled(style == STYLE_NOTEBOOK)

        # Скрываем пустые разделители, которые могли остаться после фильтрации меню.
        for menu_action in self.menuBar().actions():
            menu = menu_action.menu()
            if menu is None:
                continue
            actions = menu.actions()
            previous_content = False
            for index, action in enumerate(actions):
                if not action.isSeparator():
                    if action.isVisible():
                        previous_content = True
                    continue
                next_content = any(
                    not candidate.isSeparator() and candidate.isVisible()
                    for candidate in actions[index + 1:]
                )
                action.setVisible(previous_content and next_content)
                previous_content = False

    def set_editor_style(self, style):
        if style not in (STYLE_PROGRAMMING, STYLE_NOTEBOOK):
            return False
        old_style = current_editor_style()
        if style == old_style:
            return True
        if style == STYLE_PROGRAMMING and any(
            isinstance(self.tabs.widget(i), DocumentTab) and self.tabs.widget(i).style == STYLE_NOTEBOOK
            for i in range(self.tabs.count())
        ):
            answer = msg_question(
                self, "Переключение в режим программирования",
                "В режиме программирования нет форматирования, изображений и таблиц.\n"
                "При переключении эти элементы будут преобразованы в обычный текст. Продолжить?",
                QMessageBox.Yes | QMessageBox.Cancel
            )
            if answer != QMessageBox.Yes:
                return False
        self.settings.setValue("editor_style", style)
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, DocumentTab):
                tab.switch_style(style)
                self._connect_tab_signals(tab)
                self._apply_saved_font(tab.editor)
        self._apply_mode_menus()
        self.status.showMessage("Стиль редактора: " + ("Программирование" if style == STYLE_PROGRAMMING else "Блокнот"), 3500)
        self.update_status()
        return True

    def _connect_tab_signals(self, tab):
        tab.editor.textChanged.connect(lambda t=tab: self.update_tab_title(t))
        tab.editor.document().modificationChanged.connect(lambda _m, t=tab: self.update_tab_title(t))
        tab.editor.cursorPositionChanged.connect(self.update_status)
        tab.editor.zoomRequested.connect(self.zoom)

    def configure_tray(self, enabled):
        if not enabled:
            if self.tray_icon is not None:
                self.tray_icon.hide()
                self.tray_icon.deleteLater()
                self.tray_icon = None
            return
        if sys.platform != "win32" or not QSystemTrayIcon.isSystemTrayAvailable():
            self.settings.setValue("minimize_to_tray", False)
            return
        if self.tray_icon is not None:
            return
        icon = self.windowIcon()
        if icon.isNull():
            icon = QIcon(str(resource_path("logo.png") or ""))
        self.tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu(self)
        open_action = tray_menu.addAction("Открыть textDark")
        open_action.triggered.connect(self.restore_from_tray)
        tray_menu.addSeparator()
        exit_action = tray_menu.addAction("Выход")
        exit_action.triggered.connect(self.exit_from_tray)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.setToolTip("textDark 3.2")
        self.tray_icon.show()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.restore_from_tray()

    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def exit_from_tray(self):
        windows = [w for w in QApplication.topLevelWidgets() if isinstance(w, TextDark)]
        # Сначала проверяем все документы, чтобы отмена выхода не закрыла другие окна.
        for window in windows:
            for index in reversed(range(window.tabs.count())):
                tab = window.tabs.widget(index)
                if not isinstance(tab, DocumentTab) or not tab.editor.document().isModified():
                    continue
                window.tabs.setCurrentIndex(index)
                answer = msg_question(
                    window, "Выход",
                    f"Сохранить изменения в «{tab.title}»?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if answer == QMessageBox.Cancel:
                    self.restore_from_tray()
                    return
                if answer == QMessageBox.Save:
                    window.save()
                    if tab.editor.document().isModified():
                        self.restore_from_tray()
                        return
                else:
                    tab.editor.document().setModified(False)
        for window in windows:
            window._really_quit = True
            window.close()
        QApplication.quit()

    # ── кнопки закрытия вкладок ──
    def _attach_close(self, index):
        button = TabCloseButton()
        button.clicked.connect(lambda _checked=False, b=button: self._close_by_button(b))
        self.tabs.tabBar().setTabButton(index, QTabBar.RightSide, button)

    def _close_by_button(self, button):
        bar = self.tabs.tabBar()
        for i in range(self.tabs.count()):
            if bar.tabButton(i, QTabBar.RightSide) is button:
                self.close_tab(i)
                return

    def _refresh_close_buttons(self, *_):
        bar = self.tabs.tabBar()
        for i in range(self.tabs.count()):
            button = bar.tabButton(i, QTabBar.RightSide)
            if button:
                button.update()

    def _play_tab_fade(self, *_):
        tab = self.current_tab()
        if tab:
            tab.play_fade()

    def _editor_text(self):
        e = self.current_editor()
        return e.toPlainText() if e else ""

    def insert_text(self, value):
        if self.current_editor(): self.current_editor().textCursor().insertText(value)

    def open_settings(self):
        SettingsDialog(self).exec()

    def open_website(self):
        QDesktopServices.openUrl(QUrl(GITHUB_URL))

    def new_window(self):
        self._spawn_window()

    def open_in_new_window(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть в новом окне", "", "Все файлы (*.*)")
        if path: self._spawn_window(path)

    def _spawn_window(self, path=None):
        window = TextDark(path)
        window.show()
        if not hasattr(QApplication.instance(), "_textdark_windows"):
            QApplication.instance()._textdark_windows = []
        QApplication.instance()._textdark_windows.append(window)

    def save_copy(self):
        tab = self.current_tab()
        if not tab: return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить копию", str(tab.path or "Копия.txt"), "Все файлы (*.*)")
        if path:
            target = Path(path)
            try:
                content = serialize_tab(tab) if target.suffix.lower() == ".txtd" else tab.editor.toPlainText()
                payload = encrypt_text(content) if target.suffix.lower() == ".txtd" else content.encode("utf-8")
                target.write_bytes(payload)
                self.status.showMessage(f"Копия сохранена: {target.name}", 3500)
            except Exception as exc:
                msg_crit(self, "Ошибка сохранения копии", str(exc))

    def export_txt(self):
        tab = self.current_tab()
        if not tab: return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в TXT", str((tab.path or Path("Документ")).stem + ".txt"), "Текстовые файлы (*.txt)")
        if path: Path(path).write_text(tab.editor.toPlainText(), encoding="utf-8")

    def open_file_folder(self):
        tab = self.current_tab()
        if tab and tab.path:
            import subprocess
            if sys.platform == "win32": os.startfile(str(tab.path.parent))
            elif sys.platform == "darwin": subprocess.Popen(["open", str(tab.path.parent)])
            else: subprocess.Popen(["xdg-open", str(tab.path.parent)])

    def paste_plain(self): self.insert_text(QApplication.clipboard().text())
    def delete_selection(self):
        e=self.current_editor()
        if e and e.textCursor().hasSelection(): e.textCursor().removeSelectedText()

    def replace_text(self):
        editor = self.current_editor()
        if not editor:
            return
        old, ok = ask_text(self, "Заменить", "Найти:")
        if not ok or not old:
            return
        new, ok = ask_text(self, "Заменить", "Заменить на:")
        if not ok:
            return
        document = editor.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        replaced = 0
        while True:
            found = document.find(old, cursor)
            if found.isNull():
                break
            found.insertText(new)
            cursor = found
            replaced += 1
        cursor.endEditBlock()
        self.status.showMessage(f"Заменено: {replaced}", 3000)

    def goto_line(self):
        e=self.current_editor()
        if not e: return
        n,ok=ask_int(self,"Перейти к строке","Номер строки:",1,1,editor_block_count(e))
        if ok:
            c=e.textCursor(); c.movePosition(QTextCursor.Start); c.movePosition(QTextCursor.Down,QTextCursor.MoveAnchor,n-1); e.setTextCursor(c)

    def select_line(self):
        e=self.current_editor()
        if e:
            c=e.textCursor(); c.select(QTextCursor.LineUnderCursor); e.setTextCursor(c)

    def duplicate_line(self):
        e=self.current_editor()
        if e:
            c=e.textCursor(); c.beginEditBlock(); c.select(QTextCursor.LineUnderCursor); t=c.selectedText(); c.movePosition(QTextCursor.EndOfBlock); c.insertText("\n"+t); c.endEditBlock()

    def delete_line(self):
        e=self.current_editor()
        if e:
            c=e.textCursor(); c.select(QTextCursor.LineUnderCursor); c.removeSelectedText(); c.deleteChar()

    def move_line(self, direction):
        e=self.current_editor()
        if not e: return
        c=e.textCursor(); b=c.blockNumber(); lines=e.toPlainText().splitlines()
        j=b+direction
        if 0 <= j < len(lines): lines[b],lines[j]=lines[j],lines[b]; pos=c.positionInBlock(); e.setPlainText("\n".join(lines)); c=e.textCursor(); c.movePosition(QTextCursor.Start); c.movePosition(QTextCursor.Down,QTextCursor.MoveAnchor,j if direction<0 else b); c.movePosition(QTextCursor.Right,QTextCursor.MoveAnchor,min(pos,len(lines[c.blockNumber()]))); e.setTextCursor(c)

    def _replace_selected_or_all(self, fn):
        e=self.current_editor()
        if not e: return
        c=e.textCursor(); selected=c.selectedText()
        if selected: c.insertText(fn(selected))
        else: e.setPlainText(fn(e.toPlainText()))

    def transform_selection(self, fn): self._replace_selected_or_all(fn)
    def swap_case(self): self._replace_selected_or_all(str.swapcase)
    def remove_empty_lines(self):
        e=self.current_editor()
        if e: e.setPlainText("\n".join(x for x in e.toPlainText().splitlines() if x.strip()))
    def remove_duplicate_lines(self):
        e=self.current_editor()
        if e:
            seen=set(); out=[]
            for line in e.toPlainText().splitlines():
                if line not in seen: seen.add(line); out.append(line)
            e.setPlainText("\n".join(out))
    def reverse_lines(self):
        e=self.current_editor()
        if e: e.setPlainText("\n".join(reversed(e.toPlainText().splitlines())))
    def repeat_last_action(self): self.status.showMessage("Нет действия для повтора", 2500)

    def choose_font(self):
        e=self.current_editor()
        if not e: return
        dialog = QFontDialog(e.font(), self)
        dialog.setWindowTitle("Выбор шрифта")
        dialog.setOption(QFontDialog.FontDialogOption.DontUseNativeDialog, True)
        enable_dialog_animation(dialog)
        if dialog.exec():
            font = dialog.selectedFont()
            self._saved_font = font
            self.settings.setValue("editor_font", font.toString())
            for i in range(self.tabs.count()):
                self._apply_saved_font(self.tabs.widget(i).editor)
            self.status.showMessage(f"Шрифт: {font.family()}, {font.pointSize()} pt", 3500)

    def toggle_format(self, kind):
        from PySide6.QtGui import QTextCharFormat
        e=self.current_editor()
        if not e: return
        c=e.textCursor(); fmt=QTextCharFormat()
        if kind=="bold": fmt.setFontWeight(QFont.Bold if c.charFormat().fontWeight()!=QFont.Bold else QFont.Normal)
        elif kind=="italic": fmt.setFontItalic(not c.charFormat().fontItalic())
        elif kind=="underline": fmt.setFontUnderline(not c.charFormat().fontUnderline())
        else: fmt.setFontStrikeOut(not c.charFormat().fontStrikeOut())
        c.mergeCharFormat(fmt); e.mergeCurrentCharFormat(fmt)

    def zoom(self, amount):
        self.zoom_level = max(-5, min(24, self.zoom_level + int(amount)))
        self.settings.setValue("zoom_level", self.zoom_level)
        for i in range(self.tabs.count()):
            self._apply_saved_font(self.tabs.widget(i).editor)

    def reset_zoom(self):
        self.zoom_level = 0
        self.settings.setValue("zoom_level", 0)
        for i in range(self.tabs.count()):
            self._apply_saved_font(self.tabs.widget(i).editor)
    def toggle_fullscreen(self): self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def open_windows_emoji_panel(self):
        if sys.platform != "win32":
            msg_info(self, "Эмодзи и символы", "Панель Win + . доступна в Windows 10/11.")
            return
        editor = self.current_editor()
        if editor:
            editor.setFocus()
        def send_hotkey():
            try:
                import ctypes
                user32 = ctypes.windll.user32
                VK_LWIN, VK_OEM_PERIOD, KEYEVENTF_KEYUP = 0x5B, 0xBE, 0x0002
                user32.keybd_event(VK_LWIN, 0, 0, 0)
                user32.keybd_event(VK_OEM_PERIOD, 0, 0, 0)
                user32.keybd_event(VK_OEM_PERIOD, 0, KEYEVENTF_KEYUP, 0)
                user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            except Exception as exc:
                msg_warn(self, "Не удалось открыть панель", str(exc))
        QTimer.singleShot(140, send_hotkey)

    def insert_symbol(self):
        self.open_windows_emoji_panel()

    def insert_emoji(self):
        self.open_windows_emoji_panel()

    def insert_separator(self):
        editor = self.current_editor()
        if isinstance(editor, NotebookEditor):
            editor.textCursor().insertHtml("<hr/>")
        else:
            self.insert_text("\n────────────────────────\n")

    def insert_image(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor):
            return
        path, _ = QFileDialog.getOpenFileName(self, "Вставить изображение", "", "Изображения (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            msg_warn(self, "Изображение", "Не удалось открыть выбранное изображение.")
            return
        name = "textdark://image/" + secrets.token_hex(12) + ".png"
        editor.document().addResource(QTextDocument.ImageResource, QUrl(name), image)
        image_format = QTextImageFormat()
        image_format.setName(name)
        max_width = max(240, editor.viewport().width() - 50)
        target_width = min(image.width(), max_width)
        scaled = image.scaled(target_width, target_width, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_format.setWidth(scaled.width())
        image_format.setHeight(scaled.height())
        cursor = editor.textCursor()
        cursor.insertImage(image_format)
        editor.setTextCursor(cursor)

    def insert_table(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Новая таблица")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        rows = QSpinBox(); rows.setRange(1, 50); rows.setValue(3)
        columns = QSpinBox(); columns.setRange(1, 20); columns.setValue(3)
        borders = QCheckBox("Показывать границы ячеек"); borders.setChecked(True)
        header = QCheckBox("Первая строка — заголовок"); header.setChecked(True)
        form.addRow("Строки:", rows)
        form.addRow("Столбцы:", columns)
        layout.addLayout(form)
        layout.addWidget(borders)
        layout.addWidget(header)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if not dialog.exec():
            return
        table_format = QTextTableFormat()
        table_format.setCellPadding(8)
        table_format.setCellSpacing(0)
        table_format.setBorder(1.0 if borders.isChecked() else 0.0)
        table_format.setBorderBrush(QColor(BORDER))
        table_format.setBorderCollapse(True)
        table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))
        table = editor.textCursor().insertTable(rows.value(), columns.value(), table_format)
        if header.isChecked():
            for col in range(columns.value()):
                cell_cursor = table.cellAt(0, col).firstCursorPosition()
                fmt = QTextCharFormat(); fmt.setFontWeight(QFont.Bold)
                cell_cursor.mergeCharFormat(fmt)
                cell_cursor.insertText(f"Столбец {col + 1}")
        editor.setTextCursor(table.cellAt(0, 0).firstCursorPosition())

    def _table_context(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor):
            return None
        cursor = editor.textCursor()
        table = cursor.currentTable()
        if table is None:
            msg_info(self, "Таблица", "Поставь курсор в ячейку таблицы или выдели нужные ячейки.")
            return None
        first_row, num_rows, first_col, num_cols = cursor.selectedTableCells()
        if num_rows <= 0 or num_cols <= 0:
            cell = table.cellAt(cursor)
            first_row, num_rows = cell.row(), 1
            first_col, num_cols = cell.column(), 1
        return editor, cursor, table, first_row, num_rows, first_col, num_cols

    def merge_table_cells(self):
        data = self._table_context()
        if not data: return
        _editor, cursor, table, row, rows, col, cols = data
        if rows < 1 or cols < 1 or (rows == 1 and cols == 1):
            msg_info(self, "Объединение ячеек", "Сначала выдели несколько соседних ячеек таблицы.")
            return
        table.mergeCells(row, col, rows, cols)

    def split_table_cell(self):
        data = self._table_context()
        if not data:
            return
        _editor, _cursor, table, row, _rows, col, _cols = data
        cell = table.cellAt(row, col)
        if cell.rowSpan() > 1 or cell.columnSpan() > 1:
            table.splitCell(row, col, cell.rowSpan(), cell.columnSpan())
        else:
            msg_info(self, "Разделить ячейку", "Эта ячейка не была объединена с другими.")

    def add_table_row(self):
        data = self._table_context()
        if data:
            _editor, _cursor, table, row, _rows, _col, _cols = data
            table.insertRows(row + 1, 1)

    def add_table_column(self):
        data = self._table_context()
        if data:
            _editor, _cursor, table, _row, _rows, col, _cols = data
            table.insertColumns(col + 1, 1)

    def delete_table_row(self):
        data = self._table_context()
        if data:
            _editor, _cursor, table, row, _rows, _col, _cols = data
            if table.rows() > 1: table.removeRows(row, 1)

    def delete_table_column(self):
        data = self._table_context()
        if data:
            _editor, _cursor, table, _row, _rows, col, _cols = data
            if table.columns() > 1: table.removeColumns(col, 1)

    def set_table_inner_borders(self, direction, restore):
        data = self._table_context()
        if not data:
            return
        _editor, _cursor, table, row, rows, col, cols = data
        width = 1.0 if restore else 0.0
        for r in range(row, row + rows):
            for c in range(col, col + cols):
                cell = table.cellAt(r, c)
                fmt = cell.format()
                if direction in ("vertical", "all"):
                    if c > col:
                        fmt.setLeftBorder(width)
                        fmt.setLeftBorderBrush(QColor(BORDER))
                    if c < col + cols - 1:
                        fmt.setRightBorder(width)
                        fmt.setRightBorderBrush(QColor(BORDER))
                if direction in ("horizontal", "all"):
                    if r > row:
                        fmt.setTopBorder(width)
                        fmt.setTopBorderBrush(QColor(BORDER))
                    if r < row + rows - 1:
                        fmt.setBottomBorder(width)
                        fmt.setBottomBorderBrush(QColor(BORDER))
                cell.setFormat(fmt)

    def insert_list(self, style):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor): return
        cursor = editor.textCursor()
        cursor.createList(style)
        editor.setTextCursor(cursor)

    def format_heading(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor): return
        cursor = editor.textCursor()
        block_format = cursor.blockFormat()
        block_format.setHeadingLevel(1 if block_format.headingLevel() == 0 else 0)
        cursor.setBlockFormat(block_format)
        char_format = QTextCharFormat()
        char_format.setFontPointSize(18 if block_format.headingLevel() else editor.font().pointSize())
        char_format.setFontWeight(QFont.Bold if block_format.headingLevel() else QFont.Normal)
        cursor.mergeCharFormat(char_format)

    def format_quote(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor): return
        cursor = editor.textCursor()
        fmt = cursor.blockFormat()
        fmt.setLeftMargin(24 if fmt.leftMargin() < 20 else 0)
        fmt.setRightMargin(12 if fmt.rightMargin() < 10 else 0)
        cursor.setBlockFormat(fmt)

    def clear_formatting(self):
        editor = self.current_editor()
        if not isinstance(editor, NotebookEditor): return
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)
        cursor.setCharFormat(QTextCharFormat())
        cursor.setBlockFormat(QTextBlockFormat())
        editor.setTextCursor(cursor)

    def insert_file_path(self):
        path,_=QFileDialog.getOpenFileName(self,"Выбрать файл")
        if path: self.insert_text(path)
    def insert_link(self):
        value, ok = ask_text(self, "Ссылка", "URL:", "https://")
        if not ok or not value:
            return
        editor = self.current_editor()
        if isinstance(editor, NotebookEditor):
            label, label_ok = ask_text(self, "Текст ссылки", "Как показать ссылку?", value)
            if not label_ok:
                return
            editor.textCursor().insertHtml(f'<a href="{html_lib.escape(value, quote=True)}">{html_lib.escape(label)}</a>')
        else:
            self.insert_text(value)

    def document_stats(self):
        t=self._editor_text(); words=len(t.split()); chars=len(t); lines=len(t.splitlines()) or 1
        msg_info(self,"Статистика документа",f"Слов: {words}\nСимволов: {chars}\nСтрок: {lines}")
    def clear_document(self):
        if msg_question(self,"Очистить документ","Удалить весь текст?")==QMessageBox.Yes and self.current_editor(): self.current_editor().clear()
    def check_brackets(self):
        t=self._editor_text(); pairs={")":"(","]":"[","}":"{"}; stack=[]; ok=True
        for ch in t:
            if ch in "([{": stack.append(ch)
            elif ch in pairs:
                if not stack or stack.pop()!=pairs[ch]: ok=False; break
        ok=ok and not stack
        msg_info(self,"Проверка скобок","Скобки сбалансированы." if ok else "Найдены несбалансированные скобки.")
    def open_backup_folder(self):
        import subprocess
        folder=app_data_dir()/"recovery"; folder.mkdir(exist_ok=True)
        if sys.platform=="win32": os.startfile(str(folder))
        elif sys.platform=="darwin": subprocess.Popen(["open",str(folder)])
        else: subprocess.Popen(["xdg-open",str(folder)])
    def show_shortcuts(self):
        lines = []
        for label, action in self.shortcut_actions:
            sequence = action.shortcut().toString(QKeySequence.NativeText)
            if sequence:
                lines.append(f"{sequence} — {label}")
        lines.extend([
            "Ctrl + колесо мыши — масштаб",
            "Win + . — эмодзи и символы Windows",
        ])
        msg_info(self, "Сочетания клавиш", "\n".join(lines) if lines else "Сочетания не назначены.")
    def about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("О программе textDark")
        dialog.setMinimumWidth(420)
        enable_dialog_animation(dialog)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(32, 30, 32, 26)
        layout.setSpacing(12)

        logo = QLabel()
        logo.setAlignment(Qt.AlignCenter)
        logo_file = resource_path("logo.png")
        pix = QPixmap(str(logo_file)) if logo_file else QPixmap()
        if not pix.isNull():
            logo.setPixmap(pix.scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setObjectName("AboutBadge")
            logo.setText("t")
            logo.setFixedSize(72, 72)
        layout.addWidget(logo, 0, Qt.AlignHCenter)

        title = QLabel("textDark")
        title.setObjectName("AboutTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        chip = QLabel(f"Версия {APP_VERSION}")
        chip.setObjectName("Chip")
        chip.setAlignment(Qt.AlignCenter)
        layout.addWidget(chip, 0, Qt.AlignHCenter)

        desc = QLabel("Это легкий текстовый редактор, поддерживающий многие текстовые файлы и имеет свой собственный формат .txtd\n\nЕго создатель - mrsiktyyy, chatGPT free, claude free")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setObjectName("AboutText")
        layout.addWidget(desc)
        layout.addSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)
        site_btn = QPushButton("Сайт / Скачать")
        site_btn.clicked.connect(self.open_website)
        close_btn = QPushButton("Закрыть")
        close_btn.setDefault(True)
        close_btn.clicked.connect(dialog.accept)
        row.addWidget(site_btn)
        row.addWidget(close_btn)
        row.addStretch(1)
        layout.addLayout(row)
        dialog.exec()

    def _apply_style(self):
        tokens = {
            "@surfaceHover": SURFACE_HOVER, "@surface": SURFACE, "@editor": EDITOR_BG,
            "@border": BORDER, "@muted": MUTED, "@accent": ACCENT, "@text": TEXT, "@bg": BG,
        }
        qss = """
        QMainWindow, QDialog { background:@bg; }
        QToolTip { background:@surfaceHover; color:@text; border:1px solid @border; border-radius:6px; padding:5px 9px; }

        /* Меню */
        QMenuBar { background:@bg; border:0; padding:6px 10px 4px 10px; }
        QMenuBar::item { background:transparent; color:@muted; padding:6px 13px; margin:0 1px; border-radius:9px; }
        QMenuBar::item:selected, QMenuBar::item:pressed { background:@surfaceHover; color:@text; }
        QMenu { background:@surface; border:1px solid @border; border-radius:12px; padding:6px; color:@text; }
        QMenu::item { background:transparent; padding:8px 32px 8px 14px; margin:1px 0; border-radius:8px; }
        QMenu::item:selected { background:@surfaceHover; color:#ffffff; }
        QMenu::item:disabled { color:#5d5d63; }
        QMenu::separator { height:1px; background:@border; margin:6px 10px; }

        /* Вкладки-«чипы». Без min-width: вкладка по ширине равна названию, крестик рядом с ним. */
        QTabWidget::pane { border:0; border-top:1px solid @border; background:@editor; top:0px; }
        QTabBar { background:transparent; qproperty-drawBase:0; }
        QTabBar::tab { background:@surface; color:#c9c9ce; border:1px solid @border; border-radius:15px;
                       height:28px; max-width:230px; padding:0 6px 0 14px; margin:7px 3px 8px 0; }
        QTabBar::tab:first { margin-left:12px; }
        QTabBar::tab:hover:!selected { background:@surfaceHover; color:@text; }
        QTabBar::tab:selected { background:@text; color:@bg; border:1px solid @text; }

        /* Кнопка «+» */
        QToolButton#NewTabButton { background:@surface; color:@text; border:1px solid @border; border-radius:15px; font-size:18px; padding:0 0 2px 0; }
        QToolButton#NewTabButton:hover { background:@surfaceHover; color:@accent; border-color:@accent; }
        QToolButton#NewTabButton:pressed { background:@border; }

        /* Редактор: шрифт НЕ задаём здесь, иначе QSS перекроет выбор шрифта.
           Фон прозрачный: его рисует вкладка (цвет или изображение из настроек). */
        QPlainTextEdit, QTextEdit { background:transparent; color:@text; border:0; padding:8px 0 0 0;
                         selection-background-color:rgba(255, 90, 31, 95); selection-color:#ffffff; }
        QKeySequenceEdit { background:@editor; color:@text; border:1px solid @border; border-radius:8px; padding:4px; }

        /* Строка состояния */
        QStatusBar { background:@bg; color:@muted; border-top:1px solid @border; padding:2px 8px; }
        QStatusBar::item { border:0; }
        QStatusBar QLabel { background:transparent; color:@muted; padding:0 10px; font-size:12px; }

        /* Кнопки */
        QPushButton { background:@surface; color:@text; border:1px solid @border; border-radius:16px; padding:7px 20px; min-width:72px; min-height:18px; }
        QPushButton:hover { background:@surfaceHover; border-color:#3a3a40; }
        QPushButton:pressed { background:@border; }
        QPushButton:disabled { color:#5d5d63; background:#171719; }
        QPushButton:default { background:@text; color:@bg; border:1px solid @text; font-weight:600; }
        QPushButton:default:hover { background:#ffffff; border-color:#ffffff; }

        /* Поля ввода и списки (диалоги ввода, выбор шрифта) */
        QLineEdit { background:@editor; color:@text; border:1px solid @border; border-radius:10px; padding:7px 12px;
                    selection-background-color:@accent; selection-color:#ffffff; }
        QLineEdit:focus { border:1px solid @accent; }
        QAbstractItemView { background:@editor; color:@text; border:1px solid @border; border-radius:10px; outline:0;
                            selection-background-color:@surfaceHover; selection-color:#ffffff; }

        /* Ползунки */
        QSlider::groove:horizontal { height:4px; background:@border; border-radius:2px; }
        QSlider::sub-page:horizontal { background:@accent; border-radius:2px; }
        QSlider::handle:horizontal { background:#ffffff; width:16px; height:16px; margin:-6px 0; border-radius:8px; }
        QSlider::handle:horizontal:hover { background:#ffd9c9; }
        QSlider::groove:horizontal:disabled { background:#222225; }
        QSlider::sub-page:horizontal:disabled { background:#3a3a3f; }
        QSlider::handle:horizontal:disabled { background:#55555a; }

        /* Полосы прокрутки */
        QScrollBar:vertical { background:transparent; width:14px; margin:0; }
        QScrollBar::handle:vertical { background:#3a3a3f; border-radius:5px; min-height:40px; margin:2px 3px; }
        QScrollBar::handle:vertical:hover { background:#5a5a61; }
        QScrollBar:horizontal { background:transparent; height:14px; margin:0; }
        QScrollBar::handle:horizontal { background:#3a3a3f; border-radius:5px; min-width:40px; margin:3px 2px; }
        QScrollBar::handle:horizontal:hover { background:#5a5a61; }
        QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
        QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }

        /* Окна «Настройки» и «О программе» */
        QLabel#DlgTitle { font-size:22px; font-weight:700; color:@text; }
        QLabel#SectionTitle { font-size:14px; font-weight:600; color:@text; padding-top:4px; }
        QLabel#RowTitle { font-size:13px; color:@text; }
        QLabel#Hint { color:@muted; font-size:12px; }
        QLabel#AboutTitle { font-size:26px; font-weight:700; color:@text; }
        QLabel#AboutText { color:#b4b4ba; font-size:13px; }
        QLabel#Chip { background:@surface; color:@muted; border:1px solid @border; border-radius:11px; padding:3px 12px; font-size:12px; }
        QLabel#AboutBadge { background:@accent; color:@bg; border-radius:20px; font-size:38px; font-weight:800; }
        """
        for key in sorted(tokens, key=len, reverse=True):
            qss = qss.replace(key, tokens[key])
        self.setStyleSheet(qss)

    def new_tab(self):
        tab = DocumentTab()
        idx = self.tabs.addTab(tab, "Безымянный")
        self._attach_close(idx)
        self._apply_saved_font(tab.editor)
        self.tabs.setCurrentIndex(idx)
        self._connect_tab_signals(tab)
        self.update_tab_title(tab)

    def update_tab_title(self, tab):
        i = self.tabs.indexOf(tab)
        if i >= 0:
            # Признак несохранённых изменений показывает кнопка закрытия (точка), а не символ в тексте.
            self.tabs.setTabText(i, tab.title)
            self.tabs.setTabToolTip(i, str(tab.path) if tab.path else tab.title)
            button = self.tabs.tabBar().tabButton(i, QTabBar.RightSide)
            if button is not None and hasattr(button, "set_modified"):
                button.set_modified(tab.editor.document().isModified())

    def update_status(self, *_):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        self.lbl_pos.setText(f"Строка {cursor.blockNumber()+1}, столбец {cursor.positionInBlock()+1}")
        ext = tab.path.suffix.lower() if tab.path else ""
        if ext == ".txtd":
            kind = "TXTD · зашифровано"
        elif ext:
            kind = ext[1:].upper()
        else:
            kind = "Обычный текст"
        self.lbl_kind.setText(f"{kind} · {editor_block_count(tab.editor)} строк")

    def run_editor(self, method):
        e = self.current_editor()
        if e:
            getattr(e, method)()

    def change_font(self, font):
        self._saved_font = QFont(font)
        self.settings.setValue("editor_font", self._saved_font.toString())
        for i in range(self.tabs.count()):
            self._apply_saved_font(self.tabs.widget(i).editor)

    def change_font_size(self, size):
        if self._saved_font is not None:
            base = QFont(self._saved_font)
        elif current_editor_style() == STYLE_NOTEBOOK:
            base = default_notebook_font()
        else:
            base = default_editor_font()
        base.setPointSize(max(6, min(48, int(size))))
        self._saved_font = base
        self.settings.setValue("editor_font", base.toString())
        for i in range(self.tabs.count()):
            self._apply_saved_font(self.tabs.widget(i).editor)

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Поддерживаемые файлы (*.txtd *.txt *.py *.js *.ts *.jsx *.tsx *.html *.htm *.css *.scss *.json *.xml *.yaml *.yml *.md *.c *.cpp *.h *.hpp *.cs *.java *.php *.sql *.sh *.bat *.ps1 *.ini *.cfg *.log *.toml);;Все файлы (*.*)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        p = Path(path)
        rich_html = None
        try:
            data = p.read_bytes()
            if p.suffix.lower() == ".txtd" or data.startswith(MAGIC):
                text = decrypt_text(data)
                if text.startswith(RICH_DOC_PREFIX):
                    rich_html = text[len(RICH_DOC_PREFIX):]
                    if current_editor_style() == STYLE_PROGRAMMING:
                        choice = msg_question(
                            self,
                            "Форматированный документ",
                            "Этот файл содержит форматирование, таблицы и/или изображения.\n"
                            "Переключить textDark в режим «Блокнот», чтобы открыть его полностью?\n\n"
                            "Да — открыть со всем оформлением.\n"
                            "Нет — открыть только текст.\n"
                            "Отмена — не открывать файл.",
                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                        )
                        if choice == QMessageBox.Cancel:
                            return
                        if choice == QMessageBox.Yes:
                            if not self.set_editor_style(STYLE_NOTEBOOK):
                                return
                            text = ""
                        else:
                            text = rich_html_to_plain_text(rich_html)
                            rich_html = None
                    else:
                        text = ""
            else:
                text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            msg_warn(self, "Не удалось открыть", "Файл не является текстовым UTF-8 документом.")
            return
        except Exception as exc:
            msg_crit(self, "Ошибка открытия", str(exc))
            return
        tab = DocumentTab(p, text, rich_html=rich_html)
        idx = self.tabs.addTab(tab, p.name)
        self._attach_close(idx)
        self._apply_saved_font(tab.editor)
        self.tabs.setCurrentIndex(idx)
        self._connect_tab_signals(tab)
        tab.editor.document().setModified(False)
        self.update_tab_title(tab)
        self.update_status()

    def save(self):
        tab = self.current_tab()
        if not tab:
            return
        if not tab.path:
            self.save_as()
            return
        self._write_tab(tab, tab.path)

    def save_as(self):
        tab = self.current_tab()
        if not tab:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", str(tab.path or "Новый файл.txtd"), "TextDark (*.txtd);;Текст (*.txt);;Все файлы (*.*)")
        if path:
            p = Path(path)
            if p.suffix.lower() == ".txtd":
                self._write_tab(tab, p)
            else:
                self._write_tab(tab, p, plain=True)

    def _write_tab(self, tab, path, plain=False):
        try:
            text = tab.editor.toPlainText()
            if plain or path.suffix.lower() != ".txtd":
                payload = text.encode("utf-8")
            else:
                payload = encrypt_text(serialize_tab(tab))
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_bytes(payload)
            temp.replace(path)
            tab.path = path
            tab.editor.document().setModified(False)
            tab.set_highlighter()
            self.update_tab_title(tab)
            self.update_status()
            self.status.showMessage(
                f"Сохранено: {path.name}" + (" · форматирование сохраняется только в .txtd" if tab.style == STYLE_NOTEBOOK and path.suffix.lower() != ".txtd" else ""),
                5000
            )
        except Exception as exc:
            msg_crit(self, "Ошибка сохранения", str(exc))

    def close_tab(self, index):
        tab = self.tabs.widget(index)
        if not isinstance(tab, DocumentTab):
            return
        if tab.editor.document().isModified():
            answer = msg_question(self, "Несохранённые изменения", f"Сохранить изменения в «{tab.title}»?",
                                  QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if answer == QMessageBox.Cancel:
                return
            if answer == QMessageBox.Save:
                self.tabs.setCurrentIndex(index)
                self.save()
                if tab.editor.document().isModified():
                    return
        self.tabs.removeTab(index)
        tab.deleteLater()
        if self.tabs.count() == 0:
            self.new_tab()

    def find_text(self):
        e = self.current_editor()
        if not e:
            return
        query, ok = ask_text(self, "Найти", "Текст:")
        if ok and query:
            found = e.find(query)
            if not found:
                cursor = e.textCursor()
                cursor.movePosition(QTextCursor.Start)
                e.setTextCursor(cursor)
                if not e.find(query):
                    msg_info(self, "Поиск", "Совпадений не найдено.")

    def autosave_recovery(self):
        try:
            folder = app_data_dir() / "recovery"
            folder.mkdir(exist_ok=True)
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, DocumentTab) and tab.editor.document().isModified():
                    name = f"tab_{i}.recovery"
                    (folder / (name + ".txtd")).write_bytes(encrypt_text(serialize_tab(tab)))
        except Exception:
            pass

    def closeEvent(self, event):
        if not self._really_quit and bool(self.settings.value("minimize_to_tray", False, type=bool)) and self.tray_icon is not None:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.hide()
            event.ignore()
            if self.tray_icon:
                self.tray_icon.showMessage("textDark", "Приложение продолжает работать в системном трее.", QSystemTrayIcon.Information, 2500)
            return
        for i in reversed(range(self.tabs.count())):
            tab = self.tabs.widget(i)
            if isinstance(tab, DocumentTab) and tab.editor.document().isModified():
                self.tabs.setCurrentIndex(i)
                answer = msg_question(self, "Выход", f"Сохранить изменения в «{tab.title}»?",
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if answer == QMessageBox.Cancel:
                    event.ignore()
                    if self._really_quit:
                        self._really_quit = False
                        self.showNormal()
                    return
                if answer == QMessageBox.Save:
                    self.save()
                    if tab.editor.document().isModified():
                        event.ignore()
                        if self._really_quit:
                            self._really_quit = False
                            self.showNormal()
                        return
        self.settings.setValue("window_geometry", self.saveGeometry())
        if self.tray_icon is not None:
            self.tray_icon.hide()
        event.accept()
        if self._really_quit:
            QApplication.quit()

def build_intro_splash():
    pixmap = QPixmap(460, 210)
    pixmap.fill(QColor(BG))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor(BORDER))
    painter.drawRoundedRect(1, 1, 458, 208, 18, 18)
    logo_path = resource_path("logo.png")
    if logo_path:
        logo = QPixmap(str(logo_path))
        if not logo.isNull():
            painter.drawPixmap(34, 65, 76, 76, logo.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    painter.setPen(QColor(TEXT))
    font = QFont("Segoe UI", 24, QFont.Bold)
    painter.setFont(font)
    painter.drawText(132, 95, "textDark")
    painter.setPen(QColor(MUTED))
    painter.setFont(QFont("Segoe UI", 10))
    painter.drawText(134, 124, "Подготавливаем рабочее пространство")
    painter.setPen(QColor(ACCENT))
    painter.drawRoundedRect(134, 151, 270, 3, 1, 1)
    painter.end()
    return QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    apply_theme(app)
    get_background()
    # Небольшая подготовка до показа первого окна.
    try:
        decrypt_text(encrypt_text("warmup"))
        QTextDocument().setPlainText("warmup")
    except Exception:
        pass
    path = sys.argv[1] if len(sys.argv) > 1 and Path(sys.argv[1]).exists() else None
    settings = QSettings("textDark", "textDark")
    first_run = not settings.value("intro_shown", False, type=bool)
    if first_run:
        splash = build_intro_splash()
        splash.show()
        app.processEvents()

        def finish_intro():
            # Создание главного окна происходит уже под заставкой — это и есть предзагрузка.
            window = TextDark(path)
            app._textdark_windows = [window]
            window.show()
            splash.finish(window)
            settings.setValue("intro_shown", True)

        QTimer.singleShot(80, finish_intro)
    else:
        window = TextDark(path)
        app._textdark_windows = [window]
        window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
