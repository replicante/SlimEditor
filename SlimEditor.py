#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SlimEditor - Minimalist text editor with encryption and syntax highlighting
Author: Tannhausser (improved version)
License: MIT
"""

import os
import sys
import base64
from typing import Optional, Tuple, Dict, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QMessageBox, QFileDialog,
    QInputDialog, QLineEdit, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFontDialog, QDialogButtonBox, QStatusBar
)
from PyQt6.QtGui import (
    QIcon, QAction, QTextCursor, QFont, QCloseEvent, QSyntaxHighlighter,
    QTextCharFormat, QColor, QFontDatabase
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtCore import Qt, QRegularExpression

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet


# ---------- Syntax Highlighter ----------
class SyntaxHighlighter(QSyntaxHighlighter):
    """Generic syntax highlighter supporting multiple languages."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules: List[Tuple[QRegularExpression, QTextCharFormat]] = []
        self.multiline_comment_start = None
        self.multiline_comment_end = None
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(0x80, 0x80, 0x80))  # Gray

        # Common formats
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(0x00, 0x00, 0xFF))  # Blue
        self.keyword_format.setFontWeight(QFont.Weight.Bold)

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(0x00, 0x80, 0x00))  # Green

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(0x00, 0x80, 0x80))  # Teal

        self.comment_format.setForeground(QColor(0x80, 0x80, 0x80))
        self.comment_format.setFontItalic(True)

    def set_language(self, extension: str):
        """Configure highlighting rules based on file extension."""
        self.rules.clear()
        self.multiline_comment_start = None
        self.multiline_comment_end = None

        if extension in ['.py', '.pyw']:
            self._python_rules()
        elif extension in ['.js', '.mjs']:
            self._javascript_rules()
        elif extension in ['.html', '.htm', '.xhtml']:
            self._html_rules()
        elif extension in ['.css']:
            self._css_rules()
        elif extension in ['.json']:
            self._json_rules()
        elif extension in ['.md', '.markdown']:
            self._markdown_rules()
        elif extension in ['.c', '.h', '.cpp', '.cc', '.hpp']:
            self._c_rules()
        else:
            # No highlighting for unknown extensions, but we can still color numbers and strings minimally
            self._default_rules()
        self.rehighlight()

    def _add_rule(self, pattern: str, fmt: QTextCharFormat):
        """Helper to add a regex rule."""
        regex = QRegularExpression(pattern)
        self.rules.append((regex, fmt))

    def highlightBlock(self, text: str):
        """Apply syntax highlighting to the given block of text."""
        for pattern, fmt in self.rules:
            match = pattern.globalMatch(text)
            while match.hasNext():
                m = match.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multiline comments
        if self.multiline_comment_start and self.multiline_comment_end:
            self.setCurrentBlockState(0)
            start_index = 0
            if self.previousBlockState() != 1:
                start_index = text.find(self.multiline_comment_start)

            while start_index >= 0:
                end_index = text.find(self.multiline_comment_end, start_index + len(self.multiline_comment_start))
                if end_index == -1:
                    self.setCurrentBlockState(1)
                    comment_len = len(text) - start_index
                    self.setFormat(start_index, comment_len, self.comment_format)
                    break
                else:
                    comment_len = end_index - start_index + len(self.multiline_comment_end)
                    self.setFormat(start_index, comment_len, self.comment_format)
                    start_index = text.find(self.multiline_comment_start, end_index + len(self.multiline_comment_end))

    # ----- Language specific rules -----
    def _python_rules(self):
        keywords = [
            'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
            'def', 'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'None',
            'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'True', 'try',
            'while', 'with', 'yield'
        ]
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self._add_rule(pattern, self.keyword_format)

        # Strings
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
        self._add_rule(r'""".*?"""', self.string_format)
        self._add_rule(r"'''.*?'''", self.string_format)

        # Numbers
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?\b', self.number_format)
        self._add_rule(r'\b0x[0-9A-Fa-f]+\b', self.number_format)

        # Comments
        self._add_rule(r'#[^\n]*', self.comment_format)

        # Multiline comments (Python doesn't have multiline, but docstrings handled as strings)

    def _javascript_rules(self):
        keywords = [
            'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger',
            'default', 'delete', 'do', 'else', 'export', 'extends', 'finally',
            'for', 'function', 'if', 'import', 'in', 'instanceof', 'let', 'new',
            'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof', 'var',
            'void', 'while', 'with', 'yield', 'null', 'true', 'false'
        ]
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self._add_rule(pattern, self.keyword_format)

        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
        self._add_rule(r'`[^`\\]*(\\.[^`\\]*)*`', self.string_format)
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?\b', self.number_format)
        self._add_rule(r'//[^\n]*', self.comment_format)
        self.multiline_comment_start = '/*'
        self.multiline_comment_end = '*/'

    def _html_rules(self):
        # Tags
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor(0x00, 0x00, 0xFF))
        tag_format.setFontWeight(QFont.Weight.Bold)
        self._add_rule(r'</?[\w:-]+[^>]*>', tag_format)

        # Attributes
        attr_format = QTextCharFormat()
        attr_format.setForeground(QColor(0xFF, 0x00, 0xFF))
        self._add_rule(r'\b[\w:-]+(?=\s*=)', attr_format)

        # Strings in attributes
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)

        # Comments
        self.multiline_comment_start = '<!--'
        self.multiline_comment_end = '-->'

    def _css_rules(self):
        # Selectors
        sel_format = QTextCharFormat()
        sel_format.setForeground(QColor(0x00, 0x00, 0xFF))
        self._add_rule(r'[.#][\w-]+|[\w-]+(?=\s*\{)', sel_format)

        # Properties
        prop_format = QTextCharFormat()
        prop_format.setForeground(QColor(0x80, 0x00, 0x80))
        self._add_rule(r'[\w-]+(?=\s*:)', prop_format)

        # Values and units
        val_format = QTextCharFormat()
        val_format.setForeground(QColor(0x00, 0x80, 0x80))
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?(px|em|rem|%|vh|vw)?\b', val_format)

        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
        self.multiline_comment_start = '/*'
        self.multiline_comment_end = '*/'

    def _json_rules(self):
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"\s*:', self.keyword_format)  # keys
        self._add_rule(r'\b(true|false|null)\b', self.keyword_format)
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?\b', self.number_format)

    def _markdown_rules(self):
        # Headings
        heading_format = QTextCharFormat()
        heading_format.setForeground(QColor(0x00, 0x00, 0xFF))
        heading_format.setFontWeight(QFont.Weight.Bold)
        self._add_rule(r'^#{1,6}\s+.*', heading_format)

        # Emphasis
        italic_format = QTextCharFormat()
        italic_format.setFontItalic(True)
        self._add_rule(r'\*[^*]+\*', italic_format)
        self._add_rule(r'_[^_]+_', italic_format)

        bold_format = QTextCharFormat()
        bold_format.setFontWeight(QFont.Weight.Bold)
        self._add_rule(r'\*\*[^*]+\*\*', bold_format)

        # Links
        link_format = QTextCharFormat()
        link_format.setForeground(QColor(0x00, 0x80, 0x00))
        link_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        self._add_rule(r'\[.*?\]\(.*?\)', link_format)

        # Code blocks
        code_format = QTextCharFormat()
        code_format.setForeground(QColor(0x80, 0x40, 0x00))
        self._add_rule(r'`[^`]+`', code_format)

    def _c_rules(self):
        keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
            'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
            'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof',
            'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void',
            'volatile', 'while', 'NULL', 'true', 'false'
        ]
        pattern = r'\b(' + '|'.join(keywords) + r')\b'
        self._add_rule(pattern, self.keyword_format)

        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'(\\.|[^'\\])'", self.string_format)
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?\b', self.number_format)
        self._add_rule(r'//[^\n]*', self.comment_format)
        self.multiline_comment_start = '/*'
        self.multiline_comment_end = '*/'

    def _default_rules(self):
        # Fallback: just strings and numbers
        self._add_rule(r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format)
        self._add_rule(r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format)
        self._add_rule(r'\b[0-9]+(\.[0-9]+)?\b', self.number_format)


# ---------- Main Editor Class ----------
class FileEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.highlighter: Optional[SyntaxHighlighter] = None
        self.initUI()
        self.setup_signals()

    def initUI(self):
        # Text edit
        self.textEdit = QTextEdit()
        self.setCentralWidget(self.textEdit)
        
        # Syntax highlighter
        self.highlighter = SyntaxHighlighter(self.textEdit.document())
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready", 2000)

        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        edit_menu = menubar.addMenu("&Edit")
        view_menu = menubar.addMenu("&View")
        help_menu = menubar.addMenu("&Help")

        # File actions
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.setStatusTip("Create a new file")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("&Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open an existing file")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save the current file")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.setStatusTip("Save with a new name")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        print_action = QAction("&Print", self)
        print_action.setShortcut("Ctrl+P")
        print_action.setStatusTip("Print document")
        print_action.triggered.connect(self.print_text)
        file_menu.addAction(print_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit actions
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.setStatusTip("Undo last change")
        undo_action.triggered.connect(self.textEdit.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.setStatusTip("Redo last undone change")
        redo_action.triggered.connect(self.textEdit.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        find_action = QAction("&Find", self)
        find_action.setShortcut("Ctrl+F")
        find_action.setStatusTip("Find text")
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)

        replace_action = QAction("&Replace", self)
        replace_action.setShortcut("Ctrl+H")
        replace_action.setStatusTip("Find and replace text")
        replace_action.triggered.connect(self.show_replace_dialog)
        edit_menu.addAction(replace_action)

        edit_menu.addSeparator()

        font_action = QAction("&Font", self)
        font_action.setStatusTip("Change editor font")
        font_action.triggered.connect(self.choose_font)
        edit_menu.addAction(font_action)

        # View actions
        wrap_action = QAction("&Line Wrap", self)
        wrap_action.setCheckable(True)
        wrap_action.setChecked(True)
        wrap_action.setStatusTip("Toggle line wrapping")
        wrap_action.triggered.connect(self.toggle_wrap)
        view_menu.addAction(wrap_action)

        # Help actions
        about_action = QAction("&About", self)
        about_action.setStatusTip("About SlimEditor")
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

        # Window setup
        self.setGeometry(100, 100, 900, 600)
        self.setWindowTitle("SlimEditor - Untitled")
        self.setWindowIcon(QIcon.fromTheme("accessories-text-editor"))
        self.show()

    def setup_signals(self):
        self.textEdit.document().modificationChanged.connect(self.document_modified)

    def document_modified(self, modified: bool):
        title = "SlimEditor"
        if self.current_file:
            title += f" - {os.path.basename(self.current_file)}"
        else:
            title += " - Untitled"
        if modified:
            title += " [modified]"
        self.setWindowTitle(title)

    def document_modified_since_save(self) -> bool:
        return self.textEdit.document().isModified()

    def closeEvent(self, event: QCloseEvent):
        if self.document_modified_since_save():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "The document has unsaved changes. Do you want to save before exiting?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file():
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

    def new_file(self):
        if self.document_modified_since_save():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save the current document?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self.textEdit.clear()
        self.current_file = None
        self.textEdit.document().setModified(False)
        self.highlighter.set_language("")  # default
        self.statusBar.showMessage("New document created", 2000)

    def open_file(self):
        if self.document_modified_since_save():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save the current document before opening another?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            os.path.expanduser("~"),
            "All Files (*);;Text Files (*.txt);;Encrypted Files (*.enc)"
        )
        if not fname:
            return

        try:
            with open(fname, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                second_line = f.readline().strip()
                is_encrypted = False
                if first_line and second_line:
                    try:
                        salt_bytes = base64.b64decode(first_line)
                        if len(salt_bytes) == 16:
                            is_encrypted = True
                    except Exception:
                        pass

                if is_encrypted:
                    password, ok = QInputDialog.getText(
                        self,
                        "Encrypted File",
                        "Enter password to decrypt:",
                        QLineEdit.EchoMode.Password
                    )
                    if not ok or not password:
                        self.statusBar.showMessage("Decryption cancelled", 2000)
                        return

                    f.seek(0)
                    lines = f.read().splitlines()
                    salt_b64 = lines[0].strip()
                    encrypted_token = lines[1].strip()
                    salt = base64.b64decode(salt_b64)
                    try:
                        key = self.derive_key(password, salt)
                        decrypted = self.decrypt_text(encrypted_token, key)
                        self.textEdit.setPlainText(decrypted)
                        self.current_file = fname
                        self.textEdit.document().setModified(False)
                        self.update_highlighter_for_file(fname)
                        self.statusBar.showMessage(f"Decrypted and opened {fname}", 3000)
                    except Exception as e:
                        QMessageBox.critical(self, "Decryption Failed", f"Wrong password or corrupted file.\n{str(e)}")
                        return
                else:
                    f.seek(0)
                    content = f.read()
                    self.textEdit.setPlainText(content)
                    self.current_file = fname
                    self.textEdit.document().setModified(False)
                    self.update_highlighter_for_file(fname)
                    self.statusBar.showMessage(f"Opened {fname}", 2000)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot open file:\n{str(e)}")

    def save_file(self) -> bool:
        if self.current_file is None:
            return self.save_as_file()
        else:
            return self._save_to_file(self.current_file)

    def save_as_file(self) -> bool:
        fname, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            os.path.expanduser("~"),
            "All Files (*);;Text Files (*.txt);;Encrypted Files (*.enc)"
        )
        if not fname:
            return False
        return self._save_to_file(fname)

    def _save_to_file(self, filename: str) -> bool:
        data = self.textEdit.toPlainText()
        encrypt = QMessageBox.question(
            self,
            "Encryption",
            "Do you want to encrypt this file?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

        try:
            if encrypt:
                password, ok = QInputDialog.getText(
                    self,
                    "Set Password",
                    "Enter a password for encryption:",
                    QLineEdit.EchoMode.Password
                )
                if not ok or not password:
                    self.statusBar.showMessage("Encryption cancelled", 2000)
                    return False

                confirm, ok = QInputDialog.getText(
                    self,
                    "Confirm Password",
                    "Enter the same password again:",
                    QLineEdit.EchoMode.Password
                )
                if not ok or password != confirm:
                    QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
                    return False

                key, salt = self.derive_key_with_salt(password)
                encrypted_token = self.encrypt_text(data, key)
                salt_b64 = base64.b64encode(salt).decode()
                content = f"{salt_b64}\n{encrypted_token}"
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.statusBar.showMessage(f"Encrypted and saved to {filename}", 3000)
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(data)
                self.statusBar.showMessage(f"Saved to {filename}", 2000)

            self.current_file = filename
            self.textEdit.document().setModified(False)
            self.update_highlighter_for_file(filename)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Cannot save file:\n{str(e)}")
            return False

    def update_highlighter_for_file(self, filename: str):
        """Set the syntax highlighter based on file extension."""
        _, ext = os.path.splitext(filename)
        self.highlighter.set_language(ext.lower())

    def toggle_wrap(self, checked: bool):
        """Toggle line wrapping mode."""
        if checked:
            self.textEdit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.textEdit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    # ---------- Encryption helpers (unchanged) ----------
    def derive_key_with_salt(self, password: str) -> Tuple[bytes, bytes]:
        salt = os.urandom(16)
        return self.derive_key(password, salt), salt

    def derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt_text(self, text: str, key: bytes) -> str:
        f = Fernet(key)
        token = f.encrypt(text.encode())
        return token.decode()

    def decrypt_text(self, token: str, key: bytes) -> str:
        f = Fernet(key)
        decrypted = f.decrypt(token.encode())
        return decrypted.decode()

    # ---------- Find / Replace (as before, functional) ----------
    def show_find_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Find")
        layout = QVBoxLayout(dialog)
        find_label = QLabel("Find:")
        find_input = QLineEdit()
        layout.addWidget(find_label)
        layout.addWidget(find_input)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Find |
                                      QDialogButtonBox.StandardButton.Close)
        layout.addWidget(button_box)

        def do_find():
            text = find_input.text()
            if not text:
                return
            if not self.textEdit.find(text):
                cursor = self.textEdit.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.textEdit.setTextCursor(cursor)
                if not self.textEdit.find(text):
                    QMessageBox.information(dialog, "Find", "Text not found.")

        button_box.clicked.connect(lambda btn: dialog.close() if button_box.standardButton(btn) == QDialogButtonBox.StandardButton.Close else do_find())
        dialog.exec()

    def show_replace_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Replace")
        layout = QVBoxLayout(dialog)
        find_label = QLabel("Find:")
        find_input = QLineEdit()
        layout.addWidget(find_label)
        layout.addWidget(find_input)
        replace_label = QLabel("Replace with:")
        replace_input = QLineEdit()
        layout.addWidget(replace_label)
        layout.addWidget(replace_input)

        button_layout = QHBoxLayout()
        replace_btn = QPushButton("Replace")
        replace_all_btn = QPushButton("Replace All")
        close_btn = QPushButton("Close")
        button_layout.addWidget(replace_btn)
        button_layout.addWidget(replace_all_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        def find_next() -> bool:
            text = find_input.text()
            if not text:
                return False
            return self.textEdit.find(text)

        def replace_current():
            cursor = self.textEdit.textCursor()
            if cursor.hasSelection():
                selected = cursor.selectedText()
                if selected == find_input.text():
                    cursor.insertText(replace_input.text())
            find_next()

        def replace_all():
            old = find_input.text()
            new = replace_input.text()
            if not old:
                return
            cursor = self.textEdit.textCursor()
            start_pos = cursor.position()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.textEdit.setTextCursor(cursor)
            count = 0
            while self.textEdit.find(old):
                cursor = self.textEdit.textCursor()
                cursor.insertText(new)
                count += 1
            cursor.setPosition(start_pos)
            self.textEdit.setTextCursor(cursor)
            QMessageBox.information(dialog, "Replace All", f"Replaced {count} occurrences.")

        replace_btn.clicked.connect(replace_current)
        replace_all_btn.clicked.connect(replace_all)
        close_btn.clicked.connect(dialog.close)
        dialog.exec()

    # ---------- Other features ----------
    def choose_font(self):
        font, ok = QFontDialog.getFont(self.textEdit.font(), self)
        if ok:
            self.textEdit.setFont(font)
            self.statusBar.showMessage(f"Font changed to {font.family()}", 2000)

    def print_text(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.textEdit.document().print_(printer)
            self.statusBar.showMessage("Printing started", 2000)

    def about(self):
        QMessageBox.about(
            self,
            "About SlimEditor",
            "<h3>SlimEditor 2.0</h3>"
            "<p>A minimalist text editor with encryption and syntax highlighting.</p>"
            "<p><b>Supported syntax:</b> Python, JavaScript, HTML, CSS, JSON, Markdown, C/C++</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>AES-256 encryption (Fernet) with PBKDF2 key derivation</li>"
            "<li>Find and replace with wrap-around</li>"
            "<li>Print support</li>"
            "<li>Font customization and line wrapping</li>"
            "<li>Unsaved changes protection</li>"
            "</ul>"
            "<p>Author: <a href='https://github.com/replicante'>Tannhausser</a><br>"
            "Improved version released under MIT License</p>"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SlimEditor")
    app.setApplicationVersion("2.0")
    editor = FileEditor()
    sys.exit(app.exec())



