import cv2
import requests
import time
import pyodbc

# Configura tus credenciales de Azure Custom Vision
CUSTOM_VISION_ENDPOINT = "https://mit21-prediction.cognitiveservices.azure.com/"
CUSTOM_VISION_PREDICTION_KEY = "8aWz9lZgNNcoZ5DcnPX62AfPBixY8wta9LHcxRwm5Sa0W9XYvkkzJQQJ99AJACYeBjFXJ3w3AAAIACOGPx45"
PROJECT_ID = "d4177be7-71d1-4485-b7e3-e4c0edbffa70"
PREDICTION_ENDPOINT = "https://mit21-prediction.cognitiveservices.azure.com/customvision/v3.0/Prediction/d4177be7-71d1-4485-b7e3-e4c0edbffa70/classify/iterations/Vision%201/image"

# Configura el header para autenticarse ante Azure Custom Vision
headers = {
    'Content-Type': 'application/octet-stream',
    'Prediction-Key': CUSTOM_VISION_PREDICTION_KEY
}

# Configuración de conexión a Azure SQL
server = 'tcp:hackathon-tec21.database.windows.net'
database = 'Items'
username = 'hackathon'
password = 'Prueba2458#'
driver = '{ODBC Driver 18 for SQL Server}'


# Variable para almacenar la etiqueta con mayor probabilidad
etiqueta_mas_probable = None

# Conexión a la base de datos SQL
def conectar_a_sql():
    try:
        conexion = pyodbc.connect(
            f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
        )
        print("Conexión a SQL exitosa")
        return conexion
    except pyodbc.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# Insertar etiqueta en la base de datos
def guardar_etiqueta_en_bd(etiqueta):
    conexion = conectar_a_sql()
    if conexion:
        try:
            cursor = conexion.cursor()
            cursor.execute("UPDATE productos SET cantidad_disponible = cantidad_disponible - 1 WHERE nombre_producto = ?", (etiqueta,))
            conexion.commit()
            print(f"Etiqueta '{etiqueta}' guardada en la base de datos.")
        except pyodbc.Error as e:
            print(f"Error al insertar la etiqueta en la base de datos: {e}")
        finally:
            cursor.close()
            conexion.close()

# Enviar el fotograma a Custom Vision
def send_frame_to_custom_vision(frame):
    global etiqueta_mas_probable
    # Convierte el fotograma en un archivo binario
    _, img_encoded = cv2.imencode('.jpg', frame)
    img_bytes = img_encoded.tobytes()

    # Realiza la petición POST al servicio de Azure Custom Vision
    response = requests.post(PREDICTION_ENDPOINT, headers=headers, data=img_bytes)
    
    # Verifica la respuesta
    if response.status_code == 200:
        predictions = response.json()["predictions"]

        # Encuentra la predicción con mayor probabilidad
        best_prediction = max(predictions, key=lambda p: p['probability'])
        etiqueta = best_prediction['tagName']
        probabilidad = best_prediction['probability']
        
        print(f"Etiqueta con mayor probabilidad: {etiqueta}, Probabilidad: {probabilidad:.2f}")

        # Guarda la etiqueta con mayor probabilidad en una variable
        etiqueta_mas_probable = etiqueta
        
        # Guarda la etiqueta en la base de datos SQL
        guardar_etiqueta_en_bd(etiqueta_mas_probable)
    else:
        print(f"Error al enviar la imagen: {response.status_code} - {response.text}")

# Inicializa la cámara (0 es la cámara predeterminada)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error al abrir la cámara")
    exit()

try:
    while True:
        # Captura un fotograma de la cámara
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar el fotograma")
            break

        # Muestra el fotograma en una ventana
        cv2.imshow('Captura de Producto', frame)

        # Envía el fotograma a Custom Vision si se presiona la tecla 's'
        if cv2.waitKey(1) & 0xFF == ord('s'):
            send_frame_to_custom_vision(frame)
            print(f"Etiqueta almacenada en la variable: {etiqueta_mas_probable}")

        # Salir del bucle si se presiona la tecla 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    # Libera la cámara y cierra las ventanas abiertas
    cap.release()
    cv2.destroyAllWindows()
