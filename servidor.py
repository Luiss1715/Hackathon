from flask import Flask, jsonify, render_template
from flask import Flask, request, render_template

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ventas')
def ventas():
    return render_template('ventas.html')

@app.route('/inventario')
def inventario():
    return render_template('inventario.html')

@app.route('/estadisticas')
def estadisticas():
    return render_template('estadisticas.html')

@app.route('/agregar-producto')
def agregar_producto():
    return render_template('agregar-producto.html')

if __name__ == '__main__':
    app.run(debug=True)
