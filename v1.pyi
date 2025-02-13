import sys
import pandas as pd
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QFileDialog, QLabel, QProgressBar, QTableWidget, QTableWidgetItem, QMainWindow, QTabWidget
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup, QSequentialAnimationGroup
import os
import time
import re
from pdf2image import convert_from_path
import easyocr
import numpy as np
from threading import Thread

class PDFProcessingApp(QWidget):
    update_progress_signal = pyqtSignal(int)
    update_message_signal = pyqtSignal(str)
    update_table_signal = pyqtSignal(str, float)

    def __init__(self):
        super().__init__()
        self.title = 'HiConv-V2'
        self.selected_folder = None
        self.initUI()
        self.is_processing = False
#C:\Users\Pc\Desktop\Work-Space\Python> pyinstaller --windowed --icon=icone.ico HiconV3.py 

        self.update_progress_signal.connect(self.update_progress)
        self.update_message_signal.connect(self.update_message)
        self.update_table_signal.connect(self.update_table)

        self.animate_elements()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Background Image
        background_label = QLabel(self)
        pixmap = QPixmap('img.jpeg')
        background_label.setPixmap(pixmap)
        background_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(background_label)

        self.setStyleSheet("""
        QWidget {
            font-family: 'Roboto', sans-serif;
            background-color: transparent;
        }
        QPushButton {
            background-color: #2196F3;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            text-transform: uppercase;
            box-shadow: 0 2px 5px 0 rgba(0,0,0,0.26);
            margin: 10px 0;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        QLabel {
            color: #212121;
            font-size: 16px;
            margin-bottom: 10px;
            background-color: rgba(255, 255, 255, 0.7);
            padding: 10px;
            border-radius: 5px;
        }
        QProgressBar {
            background-color: #BDBDBD;
            border-radius: 5px;
            height: 30px;
            margin: 20px 0;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
        }
        QTableWidget {
            background-color: rgba(255, 255, 255, 0.7);
            border: 1px solid #BDBDBD;
            border-radius: 5px;
            font-size: 14px;
            margin-top: 20px;
        }
        QHeaderView::section {
            background-color: #F5F5F5;
            padding: 10px;
            border: none;
            font-size: 14px;
        }
        """)

        # Add PDF Processing Widgets
        self.button = QPushButton('📁 Sélectionnez un dossier', self)
        self.button.setToolTip('Cliquez pour sélectionner un dossier')
        self.button.clicked.connect(self.browse_folder)
        layout.addWidget(self.button)

        self.label = QLabel('Dossier sélectionné :', self)
        layout.addWidget(self.label)

        self.button2 = QPushButton('🚀 Démarrer la conversion', self)
        self.button2.setToolTip('Cliquez pour lancer la conversion')
        self.button2.clicked.connect(self.start_conversion)
        layout.addWidget(self.button2)

        self.cancel_button = QPushButton('❌ Annuler', self)
        self.cancel_button.setToolTip('Cliquez pour annuler la conversion')
        self.cancel_button.clicked.connect(self.cancel_conversion)
        layout.addWidget(self.cancel_button)

        self.progress = QProgressBar(self)
        layout.addWidget(self.progress)

        # Table for processing times
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['📄 Fichier', '⏱ Temps de traitement (s)'])
        layout.addWidget(self.table)

        self.show()

    @pyqtSlot()
    def browse_folder(self):
        self.selected_folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.label.setText(f"Dossier sélectionné : {self.selected_folder}")

    @pyqtSlot()
    def start_conversion(self):
        if self.selected_folder:
            self.label.setText("Début de la conversion.")
            self.is_processing = True
            self.progress.setValue(0)  
            self.table.setRowCount(0)   
            self.process_files()

    @pyqtSlot(int)
    def update_progress(self, value):
        self.progress.setValue(value)

    @pyqtSlot(str)
    def update_message(self, message):
        self.label.setText(message)

    @pyqtSlot(str, float)
    def update_table(self, file_name, processing_time):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(file_name))
        self.table.setItem(row_position, 1, QTableWidgetItem(f"{processing_time:.2f}"))

    @pyqtSlot()
    def cancel_conversion(self):
        self.is_processing = False
        self.label.setText("Traitement annulé.")

    def process_files(self):
        if self.selected_folder is None:
            return

        def process_files_thread():
            # Step 1: Count total files
            total_files = sum(len([f for f in files if f.lower() == "plan.pdf"]) for _, _, files in os.walk(self.selected_folder))
            if total_files == 0:
                self.update_message_signal.emit("Aucun fichier 'plan.pdf' trouvé.")
                return

            processed_files = 0
            start_time = time.time()

            for root, dirs, files in os.walk(self.selected_folder):
                for file_name in files:
                    if file_name.lower() == "plan.pdf":
                        file_path = os.path.join(root, file_name)
                        start_file_time = time.time()
                        self.process_file(file_path)
                        processing_time = time.time() - start_file_time
                        self.update_table_signal.emit(file_name, processing_time)
                        processed_files += 1
                        progress_value = int((processed_files / total_files) * 100)
                        self.update_progress_signal.emit(progress_value)

                        if not self.is_processing:
                            break

            total_processing_time = time.time() - start_time
            self.update_message_signal.emit(f"Terminé. Temps total: {total_processing_time:.2f}secondes, Fichiers traités: {processed_files}")

        self.thread = Thread(target=process_files_thread)
        self.thread.start()

    def process_file(self, file_path):
        self.update_message_signal.emit(f"Traitement du fichier : {file_path}")

        # Conversion du PDF en images
        images = convert_from_path(file_path)

        reader = easyocr.Reader(['fr'])
        numbers = []

        for i, image in enumerate(images):
            image_np = np.array(image)
            results = reader.readtext(image_np)

            # Extraction des nombres
            for result in results:
                text = result[1]
                extracted_numbers = re.findall(r'\b\d{5,}(?:\.\d+)?\b', text)
                valid_numbers = [float(num.replace(',', '.')) for num in extracted_numbers if float(num.replace(',', '.')) > 100000]
                numbers.extend(valid_numbers)

        # Diviser la liste NUMBER en deux listes : X et Y
        X = numbers[::2]
        Y = numbers[1::2]

        # Création du fichier CSV dans le même répertoire que le PDF
        chemin_resultats_csv = os.path.splitext(file_path)[0] + ".csv"
        df = pd.DataFrame(list(zip(X, Y)), columns=['X', 'Y'])
        df.to_csv(chemin_resultats_csv, index=False, header=True, sep=';')

    def animate_elements(self):
        # Initialize animations
        self.animations = []

        # Button animation
        self.animate_widget(self.button, 0, QPoint(0, 50))
        self.animate_widget(self.button2, 500, QPoint(0, 50))
        self.animate_widget(self.cancel_button, 1000, QPoint(0, 50))

        # Label animation
        self.animate_widget(self.label, 1500, QPoint(0, 50))

        # Progress bar animation
        self.animate_widget(self.progress, 2000, QPoint(0, 50))

        # Table animation
        self.animate_widget(self.table, 2500, QPoint(0, 50))

    def animate_widget(self, widget, delay, end_pos):
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(1000)
        animation.setStartValue(widget.pos() + end_pos)
        animation.setEndValue(widget.pos())
        animation.setEasingCurve(QEasingCurve.OutBounce)
        QTimer.singleShot(delay, animation.start)
        self.animations.append(animation)

class HiConvert(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'HI CONVERT'
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 800, 600)
        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)

        self.show()

class MyTableWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = PDFProcessingApp()

        # Add tabs
        self.tabs.addTab(self.tab1, "HiConvV2")

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = HiConvert()
    sys.exit(app.exec_())
