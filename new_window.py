import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import parking_client

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

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label_id)
        layout.addWidget(self.input_id)
        layout.addWidget(self.label_password)
        layout.addWidget(self.input_password)
        layout.addWidget(self.label_programa)
        layout.addWidget(self.input_programa)
        layout.addWidget(self.label_rol)
        layout.addWidget(self.combo_rol)
        layout.addWidget(self.boton_registrar)
        layout.addWidget(self.qr_label)
        self.setLayout(layout)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    url = "http://localhost:80"
    ventana = RegistroVentana(url)
    ventana.show()
    sys.exit(app.exec_())
