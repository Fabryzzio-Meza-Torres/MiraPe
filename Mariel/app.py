from flask import Flask, jsonify, send_from_directory, render_template
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    try:
        # Intentar primero con wardrobe_updated.json (filtrado)
        try:
            with open('../Deteccion_de_ropa/data/wardrobe_updated.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Cargado wardrobe_updated.json con {len(data)} entradas")
        except FileNotFoundError:
            # Si no existe, usar el original
            with open('../Deteccion_de_ropa/data/wardrobe.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"⚠️ Usando wardrobe.json original con {len(data)} entradas")
        
        return jsonify(data)
    except FileNotFoundError:
        print("❌ No se encontró ningún archivo wardrobe")
        return jsonify([])

@app.route('/upload_images/<path:filename>')
def uploaded_file(filename):
    try:
        # Construir la ruta completa
        upload_dir = os.path.join('..', 'Deteccion_de_ropa', 'upload_images')
        file_path = os.path.join(upload_dir, filename)
        
        # Verificar si el archivo existe
        if os.path.exists(file_path):
            return send_from_directory(upload_dir, filename)
        else:
            # Log para debugging
            print(f"Archivo no encontrado: {file_path}")
            # Listar archivos disponibles para debugging
            available_files = os.listdir(upload_dir) if os.path.exists(upload_dir) else []
            print(f"Archivos disponibles: {available_files}")
            
            # Retornar un 404 personalizado
            return "Imagen no encontrada", 404
    except Exception as e:
        print(f"Error al servir imagen: {e}")
        return "Error al cargar imagen", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
