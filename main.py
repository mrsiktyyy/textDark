import os, sys, json, base64, secrets, traceback
from pathlib import Path
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from PySide6.QtCore import Qt, QRect, QSize, QTimer, QSettings
from PySide6.QtGui import (
    QAction, QColor, QFont, QPainter, QTextFormat, QSyntaxHighlighter,
    QTextCharFormat, QKeySequence, QTextCursor
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPlainTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStatusBar, QToolBar, QFontComboBox, QSpinBox, QSplitter, QInputDialog,
    QFontDialog, QDialog, QDialogButtonBox, QLineEdit, QMenu, QGridLayout
)

APP_NAME = "textDark"
APP_VERSION = "2.0.3"
MAGIC = b"TEXTDARK\x02"
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

def app_data_dir():
    base = os.getenv("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gutter = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_gutter_width(0)
        self.highlight_current_line()
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setFont(QFont("Cascadia Code", 11))
        self.highlighter = None

    def line_number_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * digits

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
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), QColor("#101114"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#687080"))
                painter.drawText(0, top, self.gutter.width()-8, self.fontMetrics().height(),
                                 Qt.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

    def highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            sel = QTextEditExtraSelection()
            sel.format.setBackground(QColor("#1a1d24"))
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
        if key in pairs and not cursor.hasSelection():
            cursor.insertText(key + pairs[key])
            cursor.movePosition(QTextCursor.Left)
            self.setTextCursor(cursor)
            return
        if key in closing and not cursor.hasSelection() and self.textCursor().charFormat():
            if self.textCursor().document().characterAt(cursor.position()) == key:
                cursor.movePosition(QTextCursor.Right)
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

# Qt's extra-selection class is exported from QtWidgets.
from PySide6.QtWidgets import QTextEdit
QTextEditExtraSelection = QTextEdit.ExtraSelection

class DocumentTab(QWidget):
    def __init__(self, path=None, text=""):
        super().__init__()
        self.path = Path(path) if path else None
        self.modified = False
        self.editor = Editor()
        self.editor.setPlainText(text)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.editor.document().modificationChanged.connect(self._modified)
        self.set_highlighter()

    def _modified(self, value):
        self.modified = value

    def set_highlighter(self):
        ext = self.path.suffix if self.path else ""
        self.editor.highlighter = CodeHighlighter(self.editor.document(), ext)

    @property
    def title(self):
        return self.path.name if self.path else "Безымянный"

class TextDark(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        self.settings = QSettings("textDark", "textDark")
        self.setWindowTitle("textDark - Текстовый редактор")
        self._set_app_icon()
        self.resize(1180, 780)
        self.setMinimumSize(760, 520)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)
        self.setCentralWidget(self.tabs)
        self._build_ui()
        self._apply_style()
        if not initial_file:
            self.new_tab()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_recovery)
        self.autosave_timer.start(45000)
        if initial_file:
            self.open_file(initial_file)

    def current_tab(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, DocumentTab) else None

    def current_editor(self):
        tab = self.current_tab()
        return tab.editor if tab else None

    def _set_app_icon(self):
        candidates = [Path(__file__).with_name("logo.png"), Path(getattr(sys, "_MEIPASS", "")) / "logo.png"]
        for candidate in candidates:
            if candidate.is_file():
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(str(candidate)))
                QApplication.setWindowIcon(QIcon(str(candidate)))
                break

    def _build_ui(self):
        bar = self.menuBar()
        self._make_menu(bar, "Файл", [
            ("Создать", self.new_tab, "Ctrl+N"), ("Новое окно", self.new_window, "Ctrl+Shift+N"),
            ("Открыть...", self.open_dialog, "Ctrl+O"), ("Открыть в новом окне...", self.open_in_new_window, "Ctrl+Shift+O"),
            None, ("Сохранить", self.save, "Ctrl+S"), ("Сохранить как...", self.save_as, "Ctrl+Shift+S"),
            ("Сохранить копию...", self.save_copy, None), ("Экспорт в TXT", self.export_txt, None),
            None, ("Печать...", self.print_document, "Ctrl+P"), ("Предпросмотр печати...", self.print_preview, None),
            ("Открыть папку файла", self.open_file_folder, None), None, ("Выход", self.close, "Alt+F4")])
        self._make_menu(bar, "Правка", [
            ("Отменить", lambda: self.run_editor("undo"), "Ctrl+Z"), ("Повторить", lambda: self.run_editor("redo"), "Ctrl+Y"),
            None, ("Вырезать", lambda: self.run_editor("cut"), "Ctrl+X"), ("Копировать", lambda: self.run_editor("copy"), "Ctrl+C"),
            ("Вставить", lambda: self.run_editor("paste"), "Ctrl+V"), ("Вставить без форматирования", self.paste_plain, "Ctrl+Shift+V"),
            ("Удалить выделенное", self.delete_selection, "Delete"), ("Выделить всё", lambda: self.run_editor("selectAll"), "Ctrl+A"),
            None, ("Найти...", self.find_text, "Ctrl+F"), ("Заменить...", self.replace_text, "Ctrl+H"), ("Перейти к строке...", self.goto_line, "Ctrl+G"),
            None, ("Выделить строку", self.select_line, None), ("Дублировать строку", self.duplicate_line, "Ctrl+D"),
            ("Удалить строку", self.delete_line, None), ("Переместить строку вверх", lambda: self.move_line(-1), "Alt+Up"),
            ("Переместить строку вниз", lambda: self.move_line(1), "Alt+Down"), ("Удалить пустые строки", self.remove_empty_lines, None),
            None, ("Сделать строки ПРОПИСНЫМИ", lambda: self.transform_selection(str.upper), None),
            ("Сделать строки строчными", lambda: self.transform_selection(str.lower), None),
            ("Начать Каждое Слово С Заглавной", lambda: self.transform_selection(str.title), None),
            ("Обратить регистр", self.swap_case, None), ("Повторить последнее действие", self.repeat_last_action, "Ctrl+Shift+R")])
        self._make_menu(bar, "Формат", [("Шрифт...", self.choose_font, None), ("Жирный", lambda: self.toggle_format("bold"), "Ctrl+B"),
            ("Курсив", lambda: self.toggle_format("italic"), "Ctrl+I"), ("Подчёркнутый", lambda: self.toggle_format("underline"), "Ctrl+U"),
            ("Зачёркнутый", lambda: self.toggle_format("strike"), None)])
        self._make_menu(bar, "Вставка", [("Дата", lambda: self.insert_text(datetime.now().strftime("%d.%m.%Y")), None),
            ("Время", lambda: self.insert_text(datetime.now().strftime("%H:%M:%S")), None), ("Разделитель", lambda: self.insert_text("\n────────────────────────\n"), None),
            ("Символ...", self.insert_symbol, None), ("Эмодзи...", self.insert_emoji, None), ("Путь к файлу...", self.insert_file_path, None), ("Ссылка...", self.insert_link, None)])
        self._make_menu(bar, "Вид", [("Увеличить масштаб", lambda: self.zoom(1), "Ctrl++"), ("Уменьшить масштаб", lambda: self.zoom(-1), "Ctrl+-"),
            ("Сбросить масштаб", self.reset_zoom, "Ctrl+0"), ("Полноэкранный режим", self.toggle_fullscreen, "F11")])
        self._make_menu(bar, "Инструменты", [("Статистика документа", self.document_stats, None), ("Количество слов", self.word_count, None),
            ("Количество символов", self.char_count, None), ("Количество строк", self.line_count, None), ("Очистить документ", self.clear_document, None),
            ("Вставить содержимое буфера", lambda: self.insert_text(QApplication.clipboard().text()), None), ("Проверить скобки", self.check_brackets, None),
            ("Удалить дубли строк", self.remove_duplicate_lines, None), ("Перевернуть строки", self.reverse_lines, None),
            ("Открыть папку резервных копий", self.open_backup_folder, None)])
        self._make_menu(bar, "Справка", [("Сочетания клавиш", self.show_shortcuts, None), ("О программе textDark", self.about, None)])
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Готово · TXT / CODE / TXTD")

    def _make_menu(self, bar, title, items):
        menu = bar.addMenu(title)
        for item in items:
            if item is None:
                menu.addSeparator(); continue
            label, callback, shortcut = item
            action = QAction(label, self)
            action.triggered.connect(callback)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
                action.setShortcutContext(Qt.WindowShortcut)
            menu.addAction(action)
        return menu

    def _editor_text(self):
        e = self.current_editor()
        return e.toPlainText() if e else ""

    def insert_text(self, value):
        if self.current_editor(): self.current_editor().textCursor().insertText(value)

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
                payload = tab.editor.toPlainText().encode("utf-8") if target.suffix.lower() != ".txtd" else encrypt_text(tab.editor.toPlainText())
                target.write_bytes(payload)
                self.status.showMessage(f"Копия сохранена: {target.name}", 3500)
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка сохранения копии", str(exc))

    def export_txt(self):
        tab = self.current_tab()
        if not tab: return
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в TXT", str((tab.path or Path("Документ")).stem + ".txt"), "Текстовые файлы (*.txt)")
        if path: Path(path).write_text(tab.editor.toPlainText(), encoding="utf-8")

    def print_document(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(printer, self).exec(): self.current_editor().print(printer)

    def print_preview(self):
        from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
        printer = QPrinter(QPrinter.HighResolution)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(lambda p: self.current_editor().print(p))
        preview.exec()

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
        e=self.current_editor()
        if not e: return
        old, ok=QInputDialog.getText(self,"Заменить","Найти:")
        if not ok or not old: return
        new, ok=QInputDialog.getText(self,"Заменить","Заменить на:")
        if ok: e.setPlainText(e.toPlainText().replace(old,new))

    def goto_line(self):
        e=self.current_editor()
        if not e: return
        n,ok=QInputDialog.getInt(self,"Перейти к строке","Номер строки:",1,1,e.blockCount())
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
        if e:
            font,ok=QFontDialog.getFont(e.font(),self,"Выбор шрифта")
            if ok:
                for i in range(self.tabs.count()): self.tabs.widget(i).editor.setFont(font)

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
        for i in range(self.tabs.count()): self.tabs.widget(i).editor.zoomIn(amount) if amount>0 else self.tabs.widget(i).editor.zoomOut(-amount)
    def reset_zoom(self):
        for i in range(self.tabs.count()):
            font=self.tabs.widget(i).editor.font(); font.setPointSize(11); self.tabs.widget(i).editor.setFont(font)
    def toggle_fullscreen(self): self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def insert_symbol(self):
        value,ok=QInputDialog.getText(self,"Символ","Введите символ:")
        if ok: self.insert_text(value)
    def insert_emoji(self):
        value,ok=QInputDialog.getText(self,"Эмодзи","Вставьте эмодзи:")
        if ok: self.insert_text(value)
    def insert_file_path(self):
        path,_=QFileDialog.getOpenFileName(self,"Выбрать файл")
        if path: self.insert_text(path)
    def insert_link(self):
        value,ok=QInputDialog.getText(self,"Ссылка","URL:",QLineEdit.Normal,"https://")
        if ok: self.insert_text(value)

    def document_stats(self):
        t=self._editor_text(); words=len(t.split()); chars=len(t); lines=len(t.splitlines()) or 1
        QMessageBox.information(self,"Статистика документа",f"Слов: {words}\nСимволов: {chars}\nСтрок: {lines}")
    def word_count(self): QMessageBox.information(self,"Количество слов",str(len(self._editor_text().split())))
    def char_count(self): QMessageBox.information(self,"Количество символов",str(len(self._editor_text())))
    def line_count(self): QMessageBox.information(self,"Количество строк",str(len(self._editor_text().splitlines()) or 1))
    def clear_document(self):
        if QMessageBox.question(self,"Очистить документ","Удалить весь текст?")==QMessageBox.Yes and self.current_editor(): self.current_editor().clear()
    def check_brackets(self):
        t=self._editor_text(); pairs={")":"(","]":"[","}":"{"}; stack=[]; ok=True
        for ch in t:
            if ch in "([{": stack.append(ch)
            elif ch in pairs:
                if not stack or stack.pop()!=pairs[ch]: ok=False; break
        ok=ok and not stack
        QMessageBox.information(self,"Проверка скобок","Скобки сбалансированы." if ok else "Найдены несбалансированные скобки.")
    def open_backup_folder(self):
        import subprocess
        folder=app_data_dir()/"recovery"; folder.mkdir(exist_ok=True)
        if sys.platform=="win32": os.startfile(str(folder))
        elif sys.platform=="darwin": subprocess.Popen(["open",str(folder)])
        else: subprocess.Popen(["xdg-open",str(folder)])
    def show_shortcuts(self):
        QMessageBox.information(self,"Сочетания клавиш","Ctrl+N — создать\nCtrl+O — открыть\nCtrl+S — сохранить\nCtrl+Shift+S — сохранить как\nCtrl+Z / Ctrl+Y — отменить / повторить\nCtrl+X / C / V — вырезать / копировать / вставить\nCtrl+F — найти\nCtrl+H — заменить\nCtrl+G — перейти к строке\nCtrl+A — выделить всё\nCtrl+B / I / U — жирный / курсив / подчёркнутый\nF11 — полный экран\nCtrl+0 — сброс масштаба")
    def about(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QVBoxLayout, QLabel
        dialog=QDialog(self); dialog.setWindowTitle("О программе textDark"); dialog.setMinimumWidth(380)
        layout=QVBoxLayout(dialog); logo=QLabel(); pix=QPixmap(str(Path(__file__).with_name("logo.png")))
        if not pix.isNull(): logo.setPixmap(pix.scaled(96,96,Qt.KeepAspectRatio,Qt.SmoothTransformation)); logo.setAlignment(Qt.AlignCenter); layout.addWidget(logo)
        title=QLabel("textDark 2.0.3"); title.setAlignment(Qt.AlignCenter); title.setStyleSheet("font-size:20px;font-weight:700;"); layout.addWidget(title)
        desc=QLabel("Это легкий текстовый редактор, поддерживающий многие текстовые файлы и имеет свой собственный формат .txtd\n\nЕго создатель - mrsiktyyy, chatGPT free, Geminii AI")
        desc.setWordWrap(True); desc.setAlignment(Qt.AlignCenter); layout.addWidget(desc)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok); buttons.accepted.connect(dialog.accept); layout.addWidget(buttons); dialog.exec()

    def _apply_style(self):
        self.setStyleSheet("""
        QMainWindow,QWidget { background:#111216; color:#e8eaf0; }
        QMenuBar,QMenu,QToolBar,QStatusBar { background:#15171d; color:#e8eaf0; border:0; }
        QMenuBar::item { padding:7px 12px; }
        QMenuBar::item:selected,QMenu::item:selected { background:#292d38; border-radius:6px; }
        QToolBar { spacing:7px; padding:9px; border-bottom:1px solid #292c35; }
        QToolButton,QPushButton { background:#20232b; border:1px solid #303541; border-radius:9px; padding:7px 12px; color:#f0f1f5; }
        QToolButton:hover,QPushButton:hover { background:#2b303b; border-color:#69758b; }
        QTabWidget::pane { border:1px solid #292c35; border-radius:8px; top:-1px; }
        QTabBar::tab { background:#191b21; color:#9ba2b0; padding:10px 16px; border:1px solid #292c35; border-bottom:0; margin-right:3px; border-top-left-radius:8px; border-top-right-radius:8px; }
        QTabBar::tab:selected { background:#242832; color:#fff; }
        QPlainTextEdit { background:#111216; color:#e7e9ef; border:0; selection-background-color:#3b465a; padding:10px; }
        QComboBox,QSpinBox { background:#20232b; border:1px solid #303541; border-radius:8px; padding:5px; }
        """)

    def new_tab(self):
        tab = DocumentTab()
        idx = self.tabs.addTab(tab, "Безымянный")
        self.tabs.setCurrentIndex(idx)
        tab.editor.textChanged.connect(lambda t=tab: self.update_tab_title(t))
        tab.editor.cursorPositionChanged.connect(self.update_status)
        self.update_tab_title(tab)

    def update_tab_title(self, tab):
        i = self.tabs.indexOf(tab)
        if i >= 0:
            self.tabs.setTabText(i, ("● " if tab.editor.document().isModified() else "") + tab.title)

    def update_status(self, *_):
        tab = self.current_tab()
        if not tab:
            return
        cursor = tab.editor.textCursor()
        self.status.showMessage(f"Строка {cursor.blockNumber()+1} · Столбец {cursor.positionInBlock()+1} · {tab.editor.blockCount()} строк")

    def run_editor(self, method):
        e = self.current_editor()
        if e:
            getattr(e, method)()

    def change_font(self, font):
        for i in range(self.tabs.count()):
            self.tabs.widget(i).editor.setFont(font)

    def change_font_size(self, size):
        for i in range(self.tabs.count()):
            font = self.tabs.widget(i).editor.font()
            font.setPointSize(size)
            self.tabs.widget(i).editor.setFont(font)

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Поддерживаемые файлы (*.txtd *.txt *.py *.js *.ts *.jsx *.tsx *.html *.htm *.css *.scss *.json *.xml *.yaml *.yml *.md *.c *.cpp *.h *.hpp *.cs *.java *.php *.sql *.sh *.bat *.ps1 *.ini *.cfg *.log *.toml);;Все файлы (*.*)")
        if path:
            self.open_file(path)

    def open_file(self, path):
        p = Path(path)
        try:
            data = p.read_bytes()
            if p.suffix.lower() == ".txtd" or data.startswith(MAGIC):
                text = decrypt_text(data)
            else:
                text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            QMessageBox.warning(self, "Не удалось открыть", "Файл не является текстовым UTF-8 документом.")
            return
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка открытия", str(exc))
            return
        tab = DocumentTab(p, text)
        idx = self.tabs.addTab(tab, p.name)
        self.tabs.setCurrentIndex(idx)
        tab.editor.textChanged.connect(lambda t=tab: self.update_tab_title(t))
        tab.editor.cursorPositionChanged.connect(self.update_status)
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
            payload = text.encode("utf-8") if plain or path.suffix.lower() != ".txtd" else encrypt_text(text)
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_bytes(payload)
            temp.replace(path)
            tab.path = path
            tab.editor.document().setModified(False)
            tab.set_highlighter()
            self.update_tab_title(tab)
            self.status.showMessage(f"Сохранено: {path.name}", 3500)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка сохранения", str(exc))

    def close_tab(self, index):
        tab = self.tabs.widget(index)
        if not isinstance(tab, DocumentTab):
            return
        if tab.editor.document().isModified():
            answer = QMessageBox.question(self, "Несохранённые изменения", f"Сохранить изменения в «{tab.title}»?",
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
        from PySide6.QtWidgets import QInputDialog
        e = self.current_editor()
        if not e:
            return
        query, ok = QInputDialog.getText(self, "Найти", "Текст:")
        if ok and query:
            found = e.find(query)
            if not found:
                cursor = e.textCursor()
                cursor.movePosition(QTextCursor.Start)
                e.setTextCursor(cursor)
                if not e.find(query):
                    QMessageBox.information(self, "Поиск", "Совпадений не найдено.")

    def autosave_recovery(self):
        try:
            folder = app_data_dir() / "recovery"
            folder.mkdir(exist_ok=True)
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, DocumentTab) and tab.editor.document().isModified():
                    name = f"tab_{i}.recovery"
                    (folder / (name + ".txtd")).write_bytes(encrypt_text(tab.editor.toPlainText()))
        except Exception:
            pass

    def closeEvent(self, event):
        for i in reversed(range(self.tabs.count())):
            tab = self.tabs.widget(i)
            if isinstance(tab, DocumentTab) and tab.editor.document().isModified():
                self.tabs.setCurrentIndex(i)
                answer = QMessageBox.question(self, "Выход", f"Сохранить изменения в «{tab.title}»?",
                                              QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if answer == QMessageBox.Cancel:
                    event.ignore(); return
                if answer == QMessageBox.Save:
                    self.save()
                    if tab.editor.document().isModified():
                        event.ignore(); return
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    path = sys.argv[1] if len(sys.argv) > 1 and Path(sys.argv[1]).exists() else None
    window = TextDark(path)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
