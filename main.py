import os
import sys
import dlib
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, 
                            QLabel, QWidget, QMessageBox, QListWidget, QHBoxLayout)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from getpass import getuser

class FaceRecognitionApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inicjalizacja detektorów dlib
        self.detector = dlib.get_frontal_face_detector()
        
        self.sp = dlib.shape_predictor('68_face_landmarks_model_v2.dat')
        self.facerec = dlib.face_recognition_model_v1('dlib_face_recognition_resnet_model_v1.dat')
        
        # Pobranie nazwy zalogowanego użytkownika
        self.current_user = getuser()
        
        # Sprawdzenie czy istnieje folder na dane twarzy
        self.face_data_dir = 'face_data'
        if not os.path.exists(self.face_data_dir):
            os.makedirs(self.face_data_dir)
        
        # Inicjalizacja UI
        self.initUI()
        
        # Wczytanie zapisanych twarzy
        self.load_known_faces()
        
        # Aktualizacja listy twarzy
        self.update_face_list()
        
        # Inicjalizacja kamery
        self.camera = cv2.VideoCapture(0)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
        # Zmienne stanu
        self.current_faces = []  # Przechowuje aktualnie wykryte twarze
        self.mode = None
        
    def initUI(self):
        self.setWindowTitle('FaceAuth')
        self.setGeometry(100, 100, 1400, 1000)
        
        # Główny widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Nagłówek
        self.title_label = QLabel(f'Witaj, {self.current_user}!')
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(self.title_label)
        
        # Informacja o liczbie zapisanych twarzy
        self.face_count_label = QLabel()
        self.face_count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.face_count_label)
        
        # Lista zapisanych twarzy
        self.face_list = QListWidget()
        layout.addWidget(self.face_list)
        
        # Przyciski główne
        buttons_layout = QHBoxLayout()
        
        self.add_face_btn = QPushButton('Dodaj nową twarz')
        self.add_face_btn.clicked.connect(self.start_adding_face)
        buttons_layout.addWidget(self.add_face_btn)
        
        self.delete_face_btn = QPushButton('Usuń wybraną twarz')
        self.delete_face_btn.clicked.connect(self.delete_selected_face)
        buttons_layout.addWidget(self.delete_face_btn)
        
        self.recognize_btn = QPushButton('Rozpoznaj twarz')
        self.recognize_btn.clicked.connect(self.start_recognition)
        buttons_layout.addWidget(self.recognize_btn)
        
        layout.addLayout(buttons_layout)
        
        # Przycisk zapisywania twarzy (ukryty na początku)
        self.save_face_btn = QPushButton('Zapisz twarz')
        self.save_face_btn.clicked.connect(self.save_current_face)
        self.save_face_btn.setVisible(False)
        layout.addWidget(self.save_face_btn)
        
        # Podgląd kamery
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(1280, 960)
        layout.addWidget(self.camera_label)
        
        # Status
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
    def load_known_faces(self):
        self.known_face_encodings = []
        self.known_face_files = []
        
        for filename in os.listdir(self.face_data_dir):
            if filename.startswith(self.current_user) and filename.endswith('.npy'):
                encoding = np.load(os.path.join(self.face_data_dir, filename))
                self.known_face_encodings.append(encoding)
                self.known_face_files.append(filename)
    
    def update_face_list(self):
        self.face_list.clear()
        for filename in self.known_face_files:
            self.face_list.addItem(filename)
        
        count = len(self.known_face_files)
        self.face_count_label.setText(f'Liczba zapisanych twarzy: {count}')
    
    def save_face_encoding(self, encoding):
        # Znajdź najwyższy numer dla nowego pliku
        max_num = 0
        for filename in self.known_face_files:
            name_part = filename.replace('.npy', '')
            parts = name_part.split('_')
            if len(parts) >= 3 and parts[2].isdigit():
                num = int(parts[2])
                if num > max_num:
                    max_num = num

        new_filename = f'{self.current_user}_face_{max_num + 1}.npy'
        file_path = os.path.join(self.face_data_dir, new_filename)

        np.save(file_path, encoding)
        self.known_face_encodings.append(encoding)
        self.known_face_files.append(new_filename)
        self.update_face_list()

        return new_filename
    
    def delete_selected_face(self):
        selected_items = self.face_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Błąd', 'Wybierz twarz do usunięcia!')
            return
            
        for item in selected_items:
            filename = item.text()
            file_path = os.path.join(self.face_data_dir, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
                # Usuń z list
                index = self.known_face_files.index(filename)
                del self.known_face_files[index]
                del self.known_face_encodings[index]
        
        self.update_face_list()
        QMessageBox.information(self, 'Sukces', 'Wybrana twarz została usunięta.')
    
    def start_adding_face(self):
        self.mode = 'add'
        self.status_label.setText('Tryb: Dodawanie nowej twarzy. Ustaw twarz przed kamerą i kliknij "Zapisz twarz".')
        self.save_face_btn.setVisible(True)
        self.timer.start(30)
    
    def start_recognition(self):
        if not self.known_face_encodings:
            QMessageBox.warning(self, 'Błąd', 'Brak zapisanych twarzy do rozpoznawania!')
            return
            
        self.mode = 'recognize'
        self.save_face_btn.setVisible(False)
        self.status_label.setText('Tryb: Rozpoznawanie twarzy. Szukam zapisanych twarzy...')
        self.timer.start(30)
    
    def save_current_face(self):
        if self.mode == 'add' and self.current_faces:
            # Konwersja do RGB (dlib używa RGB)
            ret, frame = self.camera.read()
            if not ret:
                return
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            shape = self.sp(rgb_frame, self.current_faces[0])
            encoding = np.array(self.facerec.compute_face_descriptor(rgb_frame, shape))
            filename = self.save_face_encoding(encoding)
            self.status_label.setText(f'Dodano nową twarz: {filename}')
            self.save_face_btn.setVisible(False)
            self.mode = None
            self.timer.stop()
    
    def update_frame(self):
        ret, frame = self.camera.read()
        if not ret:
            return
        
        # Konwersja do RGB (dlib używa RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Wykrywanie twarzy
        self.current_faces = self.detector(rgb_frame)
        
        for face in self.current_faces:
            x, y, w, h = (face.left(), face.top(), face.width(), face.height())
            
            if self.mode == 'add':
                # Tryb dodawania - pokazujemy prostokąt
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "Kliknij 'Zapisz twarz'", (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            elif self.mode == 'recognize' and self.known_face_encodings:
                # Tryb rozpoznawania
                shape = self.sp(rgb_frame, face)
                encoding = np.array(self.facerec.compute_face_descriptor(rgb_frame, shape))
                
                # Porównanie z zapisanymi twarzami
                distances = [np.linalg.norm(known_encoding - encoding) 
                            for known_encoding in self.known_face_encodings]
                match_index = np.argmin(distances)
                print("Dystanse:", distances)
                color = (255, 0, 0)
                if distances[match_index] < 0.4:  # Próg rozpoznawania
                    name = self.current_user
                    color = (0, 255, 0)

                    # Wypisz w terminalu
                    print(f"Rozpoznano użytkownika: {name}")
                else:
                    name = "Nieznana osoba"
                    color = (0, 0, 255)

                for i in range(68):  # 68 punktów na twarzy
                    part = shape.part(i)
                    cv2.circle(frame, (part.x, part.y), 2, color, -1)
                
                cv2.putText(frame, name, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        # Wyświetlanie obrazu w PyQt
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        q_img = q_img.data.tobytes()

        q_image = QImage(q_img, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        pixmap = pixmap.scaled(self.camera_label.width(), self.camera_label.height(), Qt.KeepAspectRatio)
        self.camera_label.setPixmap(pixmap)
    
    def closeEvent(self, event):
        # Zwolnienie kamery przy zamykaniu
        if self.camera.isOpened():
            self.camera.release()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FaceRecognitionApp()
    window.show()
    sys.exit(app.exec_())