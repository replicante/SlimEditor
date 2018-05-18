# /usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5 import QtPrintSupport

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
        
        
        self.resize(900, 600)
        self.setWindowTitle('SlimEditor')
        self.setWindowIcon(QIcon('edit-icon.svg'))
        self.center()
        self.show()
        
    def save_text(self):
        fname = QFileDialog.getSaveFileName(self, 'Open file', '/home')
        if fname[0]:
            f = open(fname[0], 'w')

            with f:
                data = self.textEdit.toPlainText()
                self.textEdit.setText(data)
                f.write(data)

    def open_text(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')
        if fname[0]:
            f = open(fname[0], 'r')

            with f:
                data = f.read()
                self.textEdit.setText(data)
        
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        
    def fonts(self):
        font, ok = QFontDialog.getFont(self.textEdit.font(), self)
        if ok:
            self.textEdit.setFont(font)
            print("Display Fonts", font)
            
    def print_text(self):
        dialog = QtPrintSupport.QPrintDialog()

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.textEdit.document().print_(dialog.printer())
            
    def about(self):
        QMessageBox.about(self, "About SlimEditor",
        "A minimalist text editor by <a href='https://github.com/replicante'>Tannhausser</a>")
        
    def closeEvent(self,event):
        reply = QMessageBox.question(self, 'Message',
        "Are you sure you want to quit?", QMessageBox.Yes |
        QMessageBox.No, QMessageBox.No)
    
        if reply == QMessageBox.Yes:
            event.accept()
        else: 
            event.ignore()
    
if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    ex = FileEditor()
    sys.exit(app.exec_())
