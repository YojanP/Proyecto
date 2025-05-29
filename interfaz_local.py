import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import cv2
import numpy as np
import parking_client

#Función para detectar color en un spot
def identificarSpot(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    colores = {
        "Rojo": [(np.array([0, 120, 70]), np.array([10, 255, 255])),
                 (np.array([170, 120, 70]), np.array([180, 255, 255]))],
        "Azul": [(np.array([100, 150, 70]), np.array([140, 255, 255]))],
        "Amarillo": [(np.array([20, 100, 100]), np.array([30, 255, 255]))]
    }
    for color, rangos in colores.items():
        mask = sum(cv2.inRange(hsv, rango[0], rango[1]) for rango in rangos)
        if np.count_nonzero(mask) > (img.shape[0] * img.shape[1] * 0.3):
            return color
    return "Disponible"


# Coordenadas de parqueaderos
parqueaderos = {
    "A1": (50, 100, 120, 60), "A2": (50, 160, 120, 60),
    "A3": (50, 220, 120, 60), "A4": (50, 280, 120, 60),
    "B1": (500, 100, 120, 60), "B2": (500, 160, 120, 60),
    "B3": (500, 220, 120, 60), "B4": (500, 280, 120, 60)
}

# Hilo para cámara y detección
class CamThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._run_flag = True

    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            self._run_flag = False
            return

        while self._run_flag:
            ret, frame = cap.read()
            if ret:
                # Dibuja rectángulos con colores según detección
                for nombre, (x, y, w, h) in parqueaderos.items():
                    roi = frame[y:y+h, x:x+w]
                    color_detectado = identificarSpot(roi)

                    if color_detectado == "Rojo":
                        color = (0, 0, 255)
                    elif color_detectado == "Azul":
                        color = (255, 0, 0)
                    elif color_detectado == "Amarillo":
                        color = (0, 255, 255)
                    else:
                        color = (0, 255, 0)  # Disponible (verde)

                    # Dibujar el rectángulo del spot
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

                    # Texto con nombre del puesto (ej. A1)
                    cv2.putText(frame, nombre, (x+5, y+20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    # Texto adicional: color o disponible
                    texto_estado = color_detectado if color_detectado != "Disponible" else "Disponible"
                    cv2.putText(frame, texto_estado, (x+5, y+45),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


                self.change_pixmap_signal.emit(frame)

        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()


class RegistroVentana(QWidget):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.setWindowTitle("Registro de Usuario")

        # Elementos de la interfaz
        self.label_id = QLabel("ID:")
        self.input_id = QLineEdit()

        self.label_password = QLabel("Contraseña:")
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)

        self.label_programa = QLabel("Programa:")
        self.input_programa = QLineEdit()

        self.label_rol = QLabel("Rol:")
        self.combo_rol = QComboBox()
        self.combo_rol.addItems(["profesor", "estudiante"])

        self.boton_registrar = QPushButton("Registrar")
        self.boton_registrar.clicked.connect(self.registrar_usuario)

        self.qr_label = QLabel()
        self.qr_label.setFixedSize(250, 250)
        self.qr_label.setAlignment(Qt.AlignCenter)

        self.camera_label = QLabel()
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("background-color: black;")  # Para ver el área

        # Nuevo botón para abrir/cerrar cámara
        self.btn_toggle_camera = QPushButton("Abrir cámara")
        self.btn_toggle_camera.clicked.connect(self.toggle_camera)

        # Layouts
        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.label_id)
        left_layout.addWidget(self.input_id)
        left_layout.addWidget(self.label_password)
        left_layout.addWidget(self.input_password)
        left_layout.addWidget(self.label_programa)
        left_layout.addWidget(self.input_programa)
        left_layout.addWidget(self.label_rol)
        left_layout.addWidget(self.combo_rol)
        left_layout.addWidget(self.boton_registrar)
        left_layout.addWidget(QLabel("Código QR generado:"))
        left_layout.addWidget(self.qr_label)
        left_layout.addWidget(self.btn_toggle_camera)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Vista en tiempo real de la cámara:"))
        right_layout.addWidget(self.camera_label)
        right_layout.addStretch()

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)

        self.thread = None

    def toggle_camera(self):
        if self.thread is None:
            # Abrir cámara y arrancar hilo
            self.thread = CamThread()
            self.thread.change_pixmap_signal.connect(self.update_image)
            self.thread.start()
            self.btn_toggle_camera.setText("Cerrar cámara")
        else:
            # Detener hilo y cerrar cámara
            self.thread.stop()
            self.thread = None
            self.camera_label.clear()
            self.btn_toggle_camera.setText("Abrir cámara")

    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(qt_image))

    def registrar_usuario(self):
        self.boton_registrar.setEnabled(False)
        user_id = self.input_id.text()
        password = self.input_password.text()
        program = self.input_programa.text()
        role = self.combo_rol.currentText()

        if not user_id or not password or not program:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios")
            return

        try:
            id_num = int(user_id)
        except ValueError:
            QMessageBox.warning(self, "Error", "El ID debe ser un número")
            return

        resultado = parking_client.registerUser(self.url, id_num, password, program, role)
        QMessageBox.information(self, "Resultado", resultado)

        if resultado == "User succesfully registered" or "Usuario ya está registrado":
            qr_bytes = parking_client.getQR(self.url, id_num, password)
            if qr_bytes:
                # Mostrar QR
                pixmap = QPixmap()
                pixmap.loadFromData(qr_bytes)
                pixmap = pixmap.scaled(self.qr_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.qr_label.setPixmap(pixmap)

                # Guardar QR para enviarlo
                with open("qr.png", "wb") as f:
                    f.write(qr_bytes)

                # Enviar QR y mostrar puesto asignado
                puesto = parking_client.sendQR(self.url, "qr.png")

                if isinstance(puesto, bytes):
                    try:
                        puesto = puesto.decode('utf-8')
                    except:
                            puesto = str(puesto)  # fallback, si falla la decodificación
                QMessageBox.information(self, "Puesto Asignado", puesto)
            else:
                QMessageBox.warning(self, "Error", "No se pudo generar el código QR")
                self.qr_label.clear()
        else:
            self.qr_label.clear()

    def closeEvent(self, event):
        if self.thread is not None:
            self.thread.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    url = "http://localhost:80"
    ventana = RegistroVentana(url)
    ventana.show()
    sys.exit(app.exec_())





    