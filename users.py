# Estos son los paquetes que se deben instalar
# pip install pycryptodome
# pip install pyqrcode
# pip install pypng
# pip install pyzbar
# pip install pillow

# No modificar estos módulos que se importan
from pyzbar.pyzbar import decode
from PIL import Image
from json import dumps
from json import loads
from hashlib import sha256
from Crypto.Cipher import AES
import base64
import pyqrcode
from os import urandom
import io
from datetime import datetime

# Nombre del archivo con la base de datos de usuarios
usersFileName="users.txt"

# Fecha actual
date=None
# Clave aleatoria para encriptar el texto de los códigos QR
key=None

# Función para encriptar (no modificar)
def encrypt_AES_GCM(msg, secretKey):
    aesCipher = AES.new(secretKey, AES.MODE_GCM)
    ciphertext, authTag = aesCipher.encrypt_and_digest(msg)
    return (ciphertext, aesCipher.nonce, authTag)

# Función para desencriptar (no modificar)
def decrypt_AES_GCM(encryptedMsg, secretKey):
    (ciphertext, nonce, authTag) = encryptedMsg
    aesCipher = AES.new(secretKey, AES.MODE_GCM, nonce)
    plaintext = aesCipher.decrypt_and_verify(ciphertext, authTag)
    return plaintext

# Función que genera un código QR (no modificar)
def generateQR(id,program,role,buffer):
    # Variables globales para la clave y la fecha
    global key
    global date

    # Información que irá en el código QR, antes de encriptar
    data={'id': id, 'program':program,'role':role}
    datas=dumps(data).encode("utf-8")

    # Si no se ha asignado una clave se genera
    if key is None:
        key =urandom(32) 
        # Se almacena la fecha actual
        date=datetime.today().strftime('%Y-%m-%d')
    
    # Si cambió la fecha actual se genera una nueva clave y 
    # se actualiza la fecha
    if date !=datetime.today().strftime('%Y-%m-%d'):
        key =urandom(32) 
        date=datetime.today().strftime('%Y-%m-%d')

    # Se encripta la información
    encrypted = list(encrypt_AES_GCM(datas,key))

    # Se crea un JSON convirtiendo los datos encriptados a base64 para poder usar texto en el QR
    qr_text=dumps({'qr_text0':base64.b64encode(encrypted[0]).decode('ascii'),
                                'qr_text1':base64.b64encode(encrypted[1]).decode('ascii'),
                                'qr_text2':base64.b64encode(encrypted[2]).decode('ascii')})
    
    # Se crea el código QR a partir del JSON
    qrcode = pyqrcode.create(qr_text)

    # Se genera una imagen PNG que se escribe en el buffer                    
    qrcode.png(buffer,scale=8)          


# Se debe codificar esta función
# Argumentos: id (entero), password (cadena), program (cadena) y role (cadena)
# Si el usuario ya existe deber retornar  "User already registered"
# Si el usuario no existe debe registar el usuario en la base de datos y retornar  "User succesfully registered"

rolDiferente = None

def registerUser(id, password, program, role):

    global rolDiferente

    id_str = str(id)

    try:
        with open('users.txt', 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 4:
                    existing_id, _, _, existing_role = parts
                    if existing_id == id_str:
                        if existing_role.lower() != role.lower():
                            rolDiferente = "Error: El usuario ya está registrado con un rol diferente"
                            return rolDiferente
                        else:
                            return "Usuario ya está registrado"

    except FileNotFoundError:
        pass

    with open('users.txt', 'a') as file:
        file.write(f"{id},{password},{program},{role}\n")

    return "User succesfully registered"

  

# Se debe complementar esta función
# Función que genera el código QR
# retorna el código QR si el id y la contraseña son correctos (usuario registrado)
# Ayuda (debe usar la función generateQR)
def getQR(id, password):

    global rolDiferente

    if rolDiferente == "Error: El usuario ya está registrado con un rol diferente":
        return
        


    buffer = io.BytesIO()
    id_str = str(id)
    
    try:
        with open('users.txt', 'r') as file:
            for line in file:
                parts = line.strip().split(',')
                if len(parts) == 4:
                    existing_id, existing_password, program, role = parts
                    if existing_id == id_str and existing_password == password:
                        generateQR(id, program, role, buffer)
                        
                        # Guardar el archivo ANTES de retornar
                        with open("qr.png", "wb") as qr_file:
                            qr_file.write(buffer.getvalue())
                            
                        return buffer
    except FileNotFoundError:
        print("El archivo users.txt no existe")
        return None

# Se debe complementar esta función
# Función que recibe el código QR como PNG
# debe verificar si el QR contiene datos que pueden ser desencriptados con la clave (key), y si el usuario está registrado
# Debe asignar un puesto de parqueadero dentro de los disponibles.

import cv2
import numpy as np

def sendQR(png):

    global rolDiferente

    if rolDiferente == "Error: El usuario ya está registrado con un rol diferente":
        return
    
    try:

        image = Image.open(io.BytesIO(png))
        decoded_list = decode(image)

        if not decoded_list:
            return "Error: No se pudo leer ningún código QR"

        qr_data = decoded_list[0].data.decode('ascii')
        data = loads(qr_data)

        # Desencriptar los datos del QR
        decrypted = loads(decrypt_AES_GCM(
            (base64.b64decode(data["qr_text0"]),
             base64.b64decode(data["qr_text1"]),
             base64.b64decode(data["qr_text2"])),
            key))

        print("Datos decodificados:", decrypted)

        user_id = str(decrypted['id'])
        user_role = decrypted['role'].lower()

        # Verificar si el usuario está registrado
        try:
            with open('users.txt', 'r') as file:
                user_found = False
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) == 4 and parts[0] == user_id:
                        user_found = True
                        if parts[3].lower() != user_role:
                            return "Error: Rol no coincide con el usuario registrado"
                        break
                if not user_found:
                    return "Error: Usuario no registrado"
        except FileNotFoundError:
            return "Error: Base de datos de usuarios no encontrada"

        # Asignación de puestos por rol
        spots_por_rol = {
            "profesor": ["A1", "A2", "A3", "A4"],
            "estudiante": ["B1", "B2", "B3", "B4"]
        }

        available_spots = spots_por_rol.get(user_role, [])
        if not available_spots:
            return "Error: Rol no tiene puestos asignados"


        # Capturar imagen de cámara
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Error: No se pudo abrir la cámara para verificar ocupación"

        for i in range(0,30):
            ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Error en la captura de imagen desde la cámara"
        
        #cv2.imshow("Detección de Parqueaderos", frame)
        cv2.imwrite("s.png",frame)

        # Coordenadas de parqueaderos
        parqueaderos = {
            "A1": (50, 100, 120, 60), "A2": (50, 160, 120, 60),
            "A3": (50, 220, 120, 60), "A4": (50, 280, 120, 60),
            "B1": (500, 100, 120, 60), "B2": (500, 160, 120, 60),
            "B3": (500, 220, 120, 60), "B4": (500, 280, 120, 60)
        }

        # Detectar puestos ocupados
        occupied_spots = set()
        for nombre, (x, y, w, h) in parqueaderos.items():
            color_detectado = identificarSpot(frame[y:y+h, x:x+w])
            if color_detectado == "Rojo":
                occupied_spots.add(nombre)

        # Asignar primer puesto libre
        for spot in available_spots:
            if spot not in occupied_spots:
                return f"Puesto asignado: {spot}"

        return "No hay puestos disponibles para su rol en este momento"

    

    except FileNotFoundError:
        return "Error: Archivo QR no encontrado"
    except Exception:
        return "Error general al procesar el código QR"
    

    # Función para detectar color en un spot
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
