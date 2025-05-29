import sys
from PyQt5.QtWidgets import QApplication
from interfaz_local import RegistroVentana  # la ventana que definiste


url = "http://localhost:80"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = RegistroVentana(url)  # Pasa la URL para usar en la clase
    ventana.show()
    sys.exit(app.exec_())



