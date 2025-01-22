# /usr/bin/python3
# -*- coding: utf-8 -*-
import os
import sys
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtPrintSupport import QPrintDialog
from PyQt6.QtCore import QPoint
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import base64

class FileEditor(QMainWindow):

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.textEdit = QTextEdit()
        self.setCentralWidget(self.textEdit)
        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        editMenu = menubar.addMenu('&Edit')
        helpMenu = menubar.addMenu("&Help")

        openFile = QAction('&Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open new file')
        openFile.triggered.connect(self.open_text)
        fileMenu.addAction(openFile)

        saveFile = QAction('&Save', self)
        saveFile.setShortcut('Ctrl+S')
        saveFile.setStatusTip('Save file')
        saveFile.triggered.connect(self.save_text)
        fileMenu.addAction(saveFile)
        
        printFile = QAction('&Print', self)
        printFile.setShortcut('Ctrl+P')
        printFile.setStatusTip('Print document')
        printFile.triggered.connect(self.print_text)
        fileMenu.addAction(printFile)

        exitAct = QAction('&Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.setStatusTip('Exit application')
        exitAct.triggered.connect(self.close)
        fileMenu.addAction(exitAct)
        
        fontFile = QAction('&Fonts', self)
        fontFile.setStatusTip('Change fonts')
        fontFile.triggered.connect(self.fonts)
        editMenu.addAction(fontFile)
        
        undoFile = QAction('&Undo', self)
        undoFile.setShortcut('Ctrl+Z')
        undoFile.setStatusTip('Undo last change')
        undoFile.triggered.connect(self.textEdit.undo)
        editMenu.addAction(undoFile)
        
        redoFile = QAction('&Redo', self)
        redoFile.setShortcut('Ctrl+Y')
        redoFile.setStatusTip('Undo last change')
        redoFile.triggered.connect(self.textEdit.undo)
        editMenu.addAction(redoFile)
        
        aboutFile = QAction('&About', self)
        aboutFile.setStatusTip('About SlimEditor')
        aboutFile.triggered.connect(self.about)
        helpMenu.addAction(aboutFile)
        
        findAction = QAction('&Find', self)
        findAction.setShortcut('Ctrl+F')
        findAction.setStatusTip('Find text')
        findAction.triggered.connect(self.show_find_dialog)
        editMenu.addAction(findAction)

        replaceAction = QAction('&Replace', self)
        replaceAction.setShortcut('Ctrl+H')
        replaceAction.setStatusTip('Replace text')
        replaceAction.triggered.connect(self.showReplaceDialog)
        editMenu.addAction(replaceAction)

        self.resize(900, 600)
        self.setWindowTitle('SlimEditor')
        self.setWindowIcon(QIcon('edit-icon.svg'))
        self.show()

    def save_text(self):
        fname = QFileDialog.getSaveFileName(self, 'Save file', os.getenv('HOME'))
        if fname[0]:
            data = self.textEdit.toPlainText()

            encrypt_option = QMessageBox.question(
                self, 'Encryption',
                "Do you want to encrypt the file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if encrypt_option == QMessageBox.StandardButton.Yes:
                password, ok = QInputDialog.getText(
                    self, 'Password', 'Enter a password for encryption:',
                    QLineEdit.EchoMode.Password
                )
                if ok and password:
                    key, salt = self.derive_key_from_password(password)
                    encrypted_data = self.encrypt_text(data, key)

                    # Store salt with encrypted data
                    with open(fname[0], 'w') as f:
                        f.write(base64.b64encode(salt).decode() + '\n' + encrypted_data)

                    QMessageBox.information(self, 'Encryption', "File encrypted and saved successfully!")
                else:
                    QMessageBox.warning(self, 'Warning', 'Encryption cancelled.')
            else:
                with open(fname[0], 'w') as f:
                    f.write(data)

            self.statusBar().showMessage(f'Saved to {fname[0]}', 2000)

    def open_text(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', os.getenv('HOME'))
        if fname[0]:
            try:
                with open(fname[0], 'r') as f:
                    content = f.read().split('\n', 1)  # Split salt from encrypted text
                    if len(content) == 2:
                        salt, encrypted_data = content
                    else:
                        # File not encrypted, just display it
                        self.textEdit.setText(content[0])
                        return

                decrypt_option = QMessageBox.question(
                    self, 'Decryption',
                    "Is the file encrypted?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if decrypt_option == QMessageBox.StandardButton.Yes:
                    password, ok = QInputDialog.getText(
                        self, 'Password', 'Enter the decryption password:',
                        QLineEdit.EchoMode.Password
                    )
                    if ok and password:
                        key, _ = self.derive_key_from_password(password, salt)
                        try:
                            decrypted_data = self.decrypt_text(encrypted_data, key)
                            self.textEdit.setText(decrypted_data)
                            QMessageBox.information(self, 'Decryption', "File decrypted successfully!")
                        except Exception:
                            QMessageBox.critical(self, 'Error', 'Failed to decrypt the file. Incorrect password.')
                    else:
                        QMessageBox.warning(self, 'Warning', 'Decryption cancelled.')
                else:
                    # If user says no to decryption but file seems encrypted, show original content
                    self.textEdit.setText(content[0] + '\n' + content[1])

            except Exception as e:
                QMessageBox.critical(self, 'Error', f"An error occurred while opening the file: {str(e)}")

    def encrypt_text(self, text, key):
        f = Fernet(key)
        encrypted_text = f.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted_text).decode()

    def decrypt_text(self, encrypted_text, key):
        f = Fernet(key)
        decrypted_text = f.decrypt(base64.urlsafe_b64decode(encrypted_text))
        return decrypted_text.decode()

    def derive_key_from_password(self, password, salt=None):
        if salt is None:
            salt = os.urandom(16)
        else:
            salt = base64.b64decode(salt)  # If salt is provided, decode it from base64

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
        
    def fonts(self):
        font, ok = QFontDialog.getFont(self.textEdit.font(), self)
        if ok:
            self.textEdit.setFont(font)
            print("Display Fonts", font)
            
    def print_text(self):
        dialog = QPrintDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.textEdit.document().print_(dialog.printer())
            
    def show_find_dialog(self):
        findDialog = QDialog(self)
        findDialog.setWindowTitle("Find")
        layout = QVBoxLayout()

        self.findInput = QLineEdit()
        layout.addWidget(self.findInput)

        findButton = QPushButton("Find Next")
        findButton.clicked.connect(self.findText)
        layout.addWidget(findButton)

        findDialog.setLayout(layout)
        findDialog.exec()
        
    def find_text(self):
        text = self.findInput.text()
        if not self.textEdit.find(text):
            cursor = self.textEdit.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.textEdit.setTextCursor(cursor)
            if not self.textEdit.find(text):
                QMessageBox.information(self, "Find", "Text not found")
                
    def showReplaceDialog(self):
        replaceDialog = QDialog(self)
        replaceDialog.setWindowTitle("Replace")
        layout = QVBoxLayout()

        self.findInput = QLineEdit()
        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.findInput)

        self.replaceInput = QLineEdit()
        layout.addWidget(QLabel("Replace with:"))
        layout.addWidget(self.replaceInput)

        replaceButton = QPushButton("Replace")
        replaceButton.clicked.connect(self.replace_Text)
        layout.addWidget(replaceButton)
        
        replaceAllButton = QPushButton("Replace All")
        replaceAllButton.clicked.connect(self.replace_all_text)
        layout.addWidget(replaceAllButton)

        replaceDialog.setLayout(layout)
        replaceDialog.exec()
        
    def replace_Text(self):
        cursor = self.textEdit.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self.replaceInput.text())
        self.find_text()

    def replace_all_tex(self):
        oldText = self.findInput.text()
        newText = self.replaceInput.text()
        content = self.textEdit.toPlainText()
        newContent = content.replace(oldText, newText)
        self.textEdit.setPlainText(newContent)

            
    def about(self):
        QMessageBox.about(self, "About SlimEditor",
        "A minimalist text editor by <a href='https://github.com/replicante'>Tannhausser</a>")
        
    def close_event(self, event):
        reply = QMessageBox.question(self, 'Message',
        "Are you sure you want to quit?", QMessageBox.StandardButton.Yes |
        QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileEditor()
    sys.exit(app.exec())



