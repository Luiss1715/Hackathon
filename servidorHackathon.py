from flask import Flask, render_template, request, redirect, url_for, flash,jsonify
import requests
import pyodbc
import cv2
import numpy as np
import base64
import datetime

import re

def extraer_comillas_simples(texto):
    # Usamos una expresión regular para encontrar el texto entre comillas simples
    resultado = re.search(r"'(.*?)'", texto)
    if resultado:
        return resultado.group(1)  # Devuelve el contenido entre comillas simples
    return None  # Si no encuentra comillas simples, devuelve None

app = Flask(__name__)
app.secret_key = 'secretkey'  # Para las sesiones de Flask

# Configura tus credenciales de Azure Custom Vision
CUSTOM_VISION_ENDPOINT = "https://mit21-prediction.cognitiveservices.azure.com/"
CUSTOM_VISION_PREDICTION_KEY = "8aWz9lZgNNcoZ5DcnPX62AfPBixY8wta9LHcxRwm5Sa0W9XYvkkzJQQJ99AJACYeBjFXJ3w3AAAIACOGPx45"
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
def send_image_to_custom_vision(image_bytes):
    global etiqueta_mas_probable

    # Realiza la petición POST al servicio de Azure Custom Vision
    response = requests.post(PREDICTION_ENDPOINT, headers=headers, data=image_bytes)
    
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

# Ruta para cerrar la venta y registrar los productos en la tabla 'ventas'
@app.route('/close_sale', methods=['POST'])
def cerrar_venta():
    data = request.json
    productos = data.get('productos', [])

    if not productos:
        return jsonify({"message": "No hay productos para registrar en la venta."}), 400

    try:
        conexion = conectar_a_sql()
        cursor = conexion.cursor()

        # Obtener la fecha y hora actual
        fecha_comprada = datetime.datetime.now().date()
        hora_comprada = datetime.datetime.now().time()
        
        for producto_nombre in productos:
            # Obtener producto_id y proveedor_id desde la base de datos
            print("si llega1")
            producto_id = obtener_producto_id(cursor, producto_nombre)
            print("si llega2")
            proveedor_id = obtener_proveedor_id(cursor, producto_nombre)
            print("si llega3")
            
            print(producto_id)
            print(proveedor_id)
            if producto_id is None or proveedor_id is None:
                return jsonify({"message": f"Error: No se encontró el producto o proveedor para '{producto_nombre}'."}), 400

            # Insertar en la tabla ventas
            cursor.execute(
                "INSERT INTO ventas (producto_id, fecha_comprada, hora_comprada, proveedor_id) VALUES (?, ?, ?, ?)",
                (producto_id, fecha_comprada, hora_comprada, proveedor_id)
            )

        conexion.commit()
        return jsonify({"message": "Venta registrada correctamente."}), 200
    except Exception as e:
        return jsonify({"message": f"Error al registrar la venta: {e}"}), 500
    finally:
        cursor.close()
        conexion.close()


# Función para obtener el producto_id desde la base de datos
@app.route('/obtener_producto', methods=['POST'])
def obtener_producto_id(cursor, nombre_producto):
    nombre_producto = extraer_comillas_simples(nombre_producto)
    cursor.execute("SELECT producto_id FROM productos WHERE nombre_producto = ?", (nombre_producto,))
    resultado = cursor.fetchone()
    print(resultado[0])
    return resultado[0] if resultado else None

# Función para obtener el proveedor_id desde la base de datos
def obtener_proveedor_id(cursor, nombre_producto):
    nombre_producto = extraer_comillas_simples(nombre_producto)
    # Paso 1: Obtener el nombre del proveedor desde la tabla productos
    print(f"nombre pro: {nombre_producto}")
    cursor.execute("""
        SELECT proveedor 
        FROM productos
        WHERE nombre_producto = ?
    """, (nombre_producto,))
    resultado = cursor.fetchone()

    if not resultado:
        return None  # Si no se encuentra el producto, retorna None

    nombre_proveedor = resultado[0]  # Extrae el nombre del proveedor
    #nombre_proveedor = extraer_comillas_simples(nombre_proveedor)
    # Paso 2: Usar el nombre del proveedor para buscar su proveedor_id
    cursor.execute("""
        SELECT proveedor_id
        FROM proveedores
        WHERE nombre_proveedor = ?
    """, (nombre_proveedor,))
    resultado_proveedor = cursor.fetchone()

    return resultado_proveedor[0] if resultado_proveedor else None



@app.route('/capture', methods=['POST'])
def capture():
    # Recibe la imagen desde la petición POST (en formato base64)
    data = request.json['image']
    image_data = base64.b64decode(data.split(",")[1])  # Decodifica la imagen base64

    # Envía la imagen a Custom Vision
    send_image_to_custom_vision(image_data)

    return jsonify({"message": f"Etiqueta '{etiqueta_mas_probable}' guardada correctamente."})


@app.route('/increase_quantity', methods=['POST'])
def increase_quantity():
    print("si entra")

    data = request.json
    producto = data['producto']

    # Conectar a la base de datos y aumentar la cantidad del producto en 1
    conexion = conectar_a_sql()
    if conexion:
        try:
            producto = extraer_comillas_simples(producto)
            cursor = conexion.cursor()
            cursor.execute("UPDATE productos SET cantidad_disponible = cantidad_disponible + 1 WHERE nombre_producto = ?", (producto,))
            conexion.commit()
            return jsonify({"message": f"Cantidad aumentada en 1 para {producto}"})
        except pyodbc.Error as e:
            print(f"Error al aumentar la cantidad: {e}")
            return jsonify({"message": f"Error al aumentar la cantidad: {e}"}), 500
        finally:
            cursor.close()
            conexion.close()
    return jsonify({"message": "Error de conexión a la base de datos"}), 500


# Función para obtener los productos desde la base de datos
def obtener_productos():
    conexion = conectar_a_sql()
    cursor = conexion.cursor()
    cursor.execute("SELECT producto_id, nombre_producto, cantidad_disponible, precio FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    conexion.close()
    return productos




# Ruta para eliminar un producto
@app.route('/eliminar-producto/<int:id>', methods=['POST'])
def eliminar_producto(id):
    conexion = conectar_a_sql()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE producto_id = ?", (id,))
    conexion.commit()
    cursor.close()
    conexion.close()
    flash('Producto eliminado correctamente.')
    return redirect(url_for('inventario'))

# Ruta para mostrar el formulario de edición de un producto
@app.route('/editar-producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    conexion = conectar_a_sql()
    cursor = conexion.cursor()

    if request.method == 'POST':
        nuevo_nombre = request.form['nombre_producto']
        nueva_cantidad = request.form['cantidad_disponible']
        nuevo_precio = request.form['precio']

        cursor.execute("""
            UPDATE productos 
            SET nombre_producto = ?, cantidad_disponible = ?, precio = ? 
            WHERE producto_id = ?""",
            (nuevo_nombre, nueva_cantidad, nuevo_precio, id)
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        flash('Producto actualizado correctamente.')
        return redirect(url_for('inventario'))

    # Obtener el producto actual para editar
    cursor.execute("SELECT nombre_producto, cantidad_disponible, precio FROM productos WHERE producto_id = ?", (id,))
    producto = cursor.fetchone()
    cursor.close()
    conexion.close()
    return render_template('editar_producto.html', producto=producto)

# Ruta para mostrar el inventario
@app.route('/inventario')
def inventario():
    productos = obtener_productos()  # Obtener los productos desde la base de datos
    return render_template('inventario.html', productos=productos)

@app.route('/')
def index():
    conexion = conectar_a_sql()
    cursor = conexion.cursor()

    # Obtener ventas totales
    cursor.execute("SELECT SUM(precio) FROM vista_ventas")
    ventas_totales = cursor.fetchone()[0] or 0

    # Obtener cantidad de productos en inventario
    cursor.execute("SELECT COUNT(*) FROM productos")
    productos_totales = cursor.fetchone()[0] or 0

    # Obtener productos con bajo stock (menos de 5 en stock)
    cursor.execute("SELECT COUNT(*) FROM productos WHERE cantidad_disponible < 5")
    bajo_stock = cursor.fetchone()[0] or 0

    # Obtener las ventas diarias de la tabla 'vista_ventas'
    cursor.execute("""
        SELECT fecha_comprada, SUM(precio) 
        FROM vista_ventas 
        GROUP BY fecha_comprada 
        ORDER BY fecha_comprada
    """)
    ventas_diarias = cursor.fetchall()

    cursor.close()
    conexion.close()

    # Extraer los días y las ventas para enviar al frontend
    fechas = [str(v[0]) for v in ventas_diarias]
    totales = [v[1] for v in ventas_diarias]

    return render_template('index.html',
                           ventas_totales=ventas_totales,
                           productos_totales=productos_totales,
                           bajo_stock=bajo_stock,
                           fechas=fechas,
                           totales=totales)


@app.route('/ventas')
def ventas():
    conexion = conectar_a_sql()  # Conectar a la base de datos
    cursor = conexion.cursor()

    # Ejecutar una consulta SQL para obtener todas las ventas desde la vista 'venta'
    cursor.execute("SELECT nombre_producto,precio, fecha_comprada, hora_comprada, proveedor FROM vista_ventas")
    ventas = cursor.fetchall()

    cursor.close()
    conexion.close()

    # Renderizar la plantilla 'ventas.html' y pasar los datos de las ventas
    return render_template('ventas.html', ventas=ventas)


@app.route('/dashboard')
def dashboard():
    print("si entra dashboard")
    conexion = conectar_a_sql()
    cursor = conexion.cursor()

    # Obtener ventas totales
    cursor.execute("SELECT SUM(total) FROM ventas")
    ventas_totales = cursor.fetchone()[0] or 0

    # Obtener cantidad de productos en inventario
    cursor.execute("SELECT COUNT(*) FROM productos")
    productos_totales = cursor.fetchone()[0] or 0

    # Obtener productos con bajo stock (menos de 5 en stock)
    cursor.execute("SELECT COUNT(*) FROM productos WHERE cantidad_disponible < 5")
    bajo_stock = cursor.fetchone()[0] or 0

    # Obtener recomendaciones (o un criterio similar)
    cursor.execute("SELECT COUNT(*) FROM recomendaciones WHERE nueva = 1")
    recomendaciones = cursor.fetchone()[0] or 0

    cursor.close()
    conexion.close()

    # Renderizar el template con los datos
    return render_template('dashboard.html',
                           ventas_totales=ventas_totales,
                           productos_totales=productos_totales,
                           bajo_stock=bajo_stock,
                           recomendaciones=recomendaciones)

@app.route('/estadisticas')
def estadisticas():
    return render_template('estadisticas.html')

@app.route('/agregar-producto')
def agregar_producto():
    return render_template('agregar-producto.html')

@app.route('/cobrar')
def cobrar():
    return render_template('prueba.html')

if __name__ == '__main__':
      app.run(debug=True, host='0.0.0.0', port=5000)
