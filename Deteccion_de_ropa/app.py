from flask import Flask, request, jsonify, send_from_directory, render_template, abort
import os
import time
import json
import base64
import io
import cv2
import numpy as np
import torch
import colorsys
from transformers import AutoImageProcessor, AutoModelForObjectDetection
from sklearn.cluster import KMeans
from werkzeug.utils import secure_filename

app = Flask(__name__)

if not os.path.exists("upload_images"):
    os.makedirs("upload_images")
if not os.path.exists("data"):
    os.makedirs("data")

DB_JSON = "data/wardrobe.json"

processor = AutoImageProcessor.from_pretrained("valentinafeve/yolos-fashionpedia")
model = AutoModelForObjectDetection.from_pretrained("valentinafeve/yolos-fashionpedia")

FILTERED_ITEMS = [
    "leg warmer",
    "sleeve",
    "pocket",
    "neckline",
    "zipper",
    "bead",
    "bow",
    "collar",
    "wallet",
    "pikachu",
    "rivet",
    "ruffle",
    "sequin",
    "tassel",
    "applique",
    "flower",
    "fringe",
    "lapel",
    "epaulette",
]


def is_filtered_item(item_type):
    return any(filtered.lower() in item_type.lower() for filtered in FILTERED_ITEMS)


def test_color_detection():
    """
    Función para probar la detección de colores con ejemplos conocidos
    """
    test_colors = [
        ([107, 142, 35], "Verde oliva clásico"),
        ([85, 107, 47], "Verde oliva oscuro"),
        ([128, 128, 0], "Verde oliva amarillento"),
        ([90, 100, 85], "Verde oliva sutil"),
        ([95, 105, 80], "Verde oliva militar"),
        ([120, 130, 100], "Verde oliva claro"),
        ([128, 128, 128], "Gris verdadero"),
        ([100, 100, 100], "Gris medio"),
        ([0, 128, 0], "Verde puro"),
        ([50, 205, 50], "Verde lima"),
        ([34, 139, 34], "Verde bosque"),
    ]

    print("=== PRUEBA DE DETECCIÓN DE COLORES ===")
    for rgb, expected in test_colors:
        detected = rgb_to_color_name(rgb)
        print(f"RGB {rgb} -> Esperado: {expected}, Detectado: {detected}")
    print("=====================================")


def rgb_to_color_name(rgb):
    r, g, b = rgb

    # Función más directa basada en valores RGB reales
    print(f"DEBUG - Analizando RGB: ({r}, {g}, {b})")

    # Calcular valores para análisis
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    brightness = (r + g + b) / 3

    # DETECCIÓN PRIORITARIA DE VERDES (ANTES QUE GRISES)
    # Verde oliva y similares - MÁXIMA PRIORIDAD
    if (
        g >= r and g >= b and g > 60
    ):  # Verde es mayor o igual, no necesariamente dominante
        print(f"DEBUG - Detectando verde: g={g}, r={r}, b={b}")

        # Verde oliva (componentes similares pero verde ligeramente mayor)
        if abs(r - g) < 40 and abs(b - g) < 40 and r > 50 and b > 40:
            return "Verde oliva"

        # Verde puro (gran diferencia con otros canales)
        elif r < 80 and b < 80:
            if g > 180:
                return "Verde brillante"
            elif g > 140:
                return "Verde"
            else:
                return "Verde oscuro"

        # Verde con tonos marrones/tierra
        elif r > 80 and b < 80:
            return "Verde oliva"

        # Verde con azul (aguamarina)
        elif b > 100:
            return "Verde agua"

        # Verde general
        else:
            if g > 140:
                return "Verde"
            else:
                return "Verde oscuro"

    # Verde sutiles donde G no es dominante pero es claramente verde
    elif g > r + 10 and g > b + 5 and g > 70:
        return "Verde"

    # Solo DESPUÉS de verificar verdes, verificar grises (para colores realmente neutros)
    if diff < 12 and abs(r - g) < 8 and abs(g - b) < 8 and abs(r - b) < 8:
        print(f"DEBUG - Color neutro detectado: diff={diff}")
        if brightness < 40:
            return "Negro"
        elif brightness < 80:
            return "Gris oscuro"
        elif brightness < 140:
            return "Gris"
        elif brightness < 200:
            return "Gris claro"
        else:
            return "Blanco"

    # ROJOS
    if r > g and r > b and r > 100:
        if g < 80 and b < 80:  # Rojo puro
            return "Rojo"
        elif g > 120:  # Con amarillo
            if b < 80:
                return "Naranja"
            else:
                return "Rosa"
        elif b > 120:  # Con azul
            return "Magenta"
        elif g > 60 and b < 60:  # Marrón
            return "Marrón"
        else:
            return "Rojizo"

    # AZULES
    elif b > r and b > g and b > 100:
        if r < 80 and g < 80:  # Azul puro
            return "Azul"
        elif g > 120:  # Con verde
            return "Turquesa"
        elif r > 120:  # Con rojo
            return "Morado"
        else:
            return "Azul"

    # AMARILLOS
    elif r > 140 and g > 140 and b < 100:
        return "Amarillo"

    # MORADOS
    elif r > 120 and b > 120 and g < 100:
        return "Morado"

    # ROSAS
    elif r > 180 and g > 120 and b > 120:
        return "Rosa"

    # Análisis final por canal dominante
    if max_val == r and r > g + 15:
        return "Rojizo"
    elif max_val == g and g > r + 15:
        return "Verdoso"
    elif max_val == b and b > r + 15:
        return "Azulado"

    # Si todo falla
    return f"Color indefinido (R:{r}, G:{g}, B:{b})"


def enhance_color_by_garment_type(color_rgb, item_type):
    try:
        r, g, b = color_rgb

        # Para prendas verdes, asegurar que el verde sea más prominente
        if g > max(r, b) or (g >= r + 10 and g >= b + 5):
            # Es verde, mejorarlo
            if g < 140:  # Verde muy sutil
                g = min(g * 1.2, 200)  # Intensificar el verde
                r = max(r * 0.9, 0)  # Reducir ligeramente otros canales
                b = max(b * 0.9, 0)

            # Para camisas verdes, hacer más vivido
            if item_type in ["shirt", "polo", "blouse", "top"]:
                g = min(g * 1.1, 220)

        # Para jeans, intensificar azules
        elif item_type in ["jeans", "pants"] and b > max(r, g):
            b = min(b * 1.15, 200)
            r = max(r * 0.95, 0)
            g = max(g * 0.95, 0)

        # Para prendas oscuras, iluminar ligeramente
        elif item_type in ["jacket", "coat", "blazer"]:
            brightness = (r + g + b) / 3
            if brightness < 80:  # Muy oscuro
                factor = 1.3
                r = min(r * factor, 160)
                g = min(g * factor, 160)
                b = min(b * factor, 160)

        return [int(r), int(g), int(b)]

    except Exception as e:
        print(f"Error en enhance_color_by_garment_type: {e}")
        return color_rgb


def get_dominant_color(image_bgr, k=8, size=(200, 200)):
    """
    Extrae el color dominante de una imagen usando K-means clustering mejorado
    """
    try:
        # Redimensionar la imagen para acelerar el procesamiento
        small = cv2.resize(image_bgr, size, interpolation=cv2.INTER_AREA)

        # Convertir de BGR a RGB para obtener los colores correctos
        rgb_image = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # Aplicar un pequeño filtro gaussiano para suavizar ruido
        rgb_image = cv2.GaussianBlur(rgb_image, (3, 3), 0)

        # Remodelar la imagen a un array de pixeles
        pixels = rgb_image.reshape(-1, 3).astype(np.float64)

        # Filtro más inteligente: eliminar píxeles extremos y de fondo
        # Calcular la media y desviación estándar para detectar outliers
        mean_color = np.mean(pixels, axis=0)
        std_color = np.std(pixels, axis=0)

        # Filtrar píxeles que estén dentro de 2 desviaciones estándar
        mask = np.all(np.abs(pixels - mean_color) <= 2 * std_color, axis=1)

        # También filtrar píxeles muy oscuros o muy claros
        brightness_mask = np.all(pixels > 15, axis=1) & np.all(pixels < 240, axis=1)

        # Combinar ambas máscaras
        final_mask = mask & brightness_mask
        filtered_pixels = pixels[final_mask]

        # Si quedan muy pocos píxeles, usar un filtro más permisivo
        if len(filtered_pixels) < 50:
            filtered_pixels = pixels[brightness_mask]

        if len(filtered_pixels) < 10:
            filtered_pixels = pixels

        # Aplicar K-means clustering con más clusters para mejor precisión
        clt = KMeans(
            n_clusters=min(k, len(filtered_pixels)), random_state=42, n_init=10
        )
        clt.fit(filtered_pixels)

        # Obtener los colores y sus frecuencias
        colors = clt.cluster_centers_
        labels = clt.labels_
        counts = np.bincount(labels)

        # Encontrar el color más frecuente que no sea muy extremo
        sorted_indices = np.argsort(counts)[::-1]  # Ordenar por frecuencia descendente

        for idx in sorted_indices:
            candidate_color = colors[idx]
            # Verificar que el color no sea muy extremo
            if not (np.all(candidate_color < 30) or np.all(candidate_color > 225)):
                dominant_color = candidate_color
                break
        else:
            # Si todos los colores son extremos, usar el más frecuente
            dominant_color = colors[np.argmax(counts)]

        # Asegurar que los valores estén en el rango 0-255 y convertir a enteros
        dominant_color = np.clip(dominant_color, 0, 255).astype(int)

        return [int(dominant_color[0]), int(dominant_color[1]), int(dominant_color[2])]

    except Exception as e:
        print(f"Error en get_dominant_color: {e}")
        # Color gris por defecto en caso de error
        return [128, 128, 128]


def validate_and_enhance_color(rgb_color, item_type):
    """
    Valida y mejora la extracción de color basado en el contexto del tipo de prenda
    """
    r, g, b = rgb_color

    # Verificar que el color no sea demasiado extremo
    if r < 10 and g < 10 and b < 10:
        return [20, 20, 20]  # Negro suave en lugar de negro puro
    elif r > 245 and g > 245 and b > 245:
        return [240, 240, 240]  # Blanco suave en lugar de blanco puro

    return rgb_color


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/wardrobe-view")
def wardrobe_view():
    """Ruta para mostrar el armario virtual"""
    return render_template("wardrobe.html")


@app.route("/agenda-view")
def agenda_view():
    """Ruta para mostrar la agenda de looks"""
    return render_template("agenda.html")


@app.route("/combinaciones-view")
def combinaciones_view():
    """Ruta para mostrar las combinaciones de ropa"""
    return render_template("combinaciones.html")


@app.route("/wardrobe-test")
def wardrobe_test():
    """Ruta de prueba para el armario virtual"""
    return render_template("wardrobe_simple.html")


@app.route("/test-image-paths")
def test_image_paths():
    """Test para verificar rutas de imágenes"""
    import os

    current_dir = os.getcwd()
    file_dir = os.path.dirname(__file__)

    # Ruta que estamos usando para Mariel
    mariel_upload_path = os.path.join(file_dir, "..", "Mariel", "upload_images")
    mariel_upload_path = os.path.abspath(mariel_upload_path)

    test_info = {
        "current_dir": current_dir,
        "file_dir": file_dir,
        "mariel_upload_path": mariel_upload_path,
        "mariel_upload_exists": os.path.exists(mariel_upload_path),
    }

    # Listar archivos en esa ruta
    if os.path.exists(mariel_upload_path):
        test_info["files_in_mariel"] = os.listdir(mariel_upload_path)

        # Probar ruta específica de camiseta_azul.svg
        test_file = os.path.join(mariel_upload_path, "camiseta_azul.svg")
        test_info["camiseta_azul_path"] = test_file
        test_info["camiseta_azul_exists"] = os.path.exists(test_file)

    return jsonify(test_info)


@app.route("/debug-wardrobe")
def debug_wardrobe():
    """Ruta de debug para verificar los datos del armario"""
    try:
        # Verificar ruta de Mariel
        mariel_metadata_path = os.path.join(
            os.path.dirname(__file__), "..", "Mariel", "metadata.json"
        )
        mariel_metadata_path = os.path.abspath(mariel_metadata_path)

        mariel_upload_path = os.path.join(
            os.path.dirname(__file__), "..", "Mariel", "upload_images"
        )
        mariel_upload_path = os.path.abspath(mariel_upload_path)

        debug_info = {
            "mariel_metadata_path": mariel_metadata_path,
            "mariel_metadata_exists": os.path.exists(mariel_metadata_path),
            "mariel_upload_path": mariel_upload_path,
            "mariel_upload_exists": os.path.exists(mariel_upload_path),
            "current_dir": os.getcwd(),
            "file_dir": os.path.dirname(__file__),
        }

        # Listar archivos en Mariel
        if os.path.exists(mariel_upload_path):
            debug_info["mariel_files"] = os.listdir(mariel_upload_path)

        if os.path.exists(mariel_metadata_path):
            with open(mariel_metadata_path, "r", encoding="utf-8") as f:
                mariel_data = json.load(f)
            debug_info["mariel_data"] = mariel_data
            debug_info["mariel_count"] = len(mariel_data)

            # Verificar si cada imagen existe
            debug_info["image_check"] = []
            for item in mariel_data:
                image_name = item["image"]
                image_path = os.path.join(mariel_upload_path, image_name)
                debug_info["image_check"].append(
                    {
                        "name": image_name,
                        "path": image_path,
                        "exists": os.path.exists(image_path),
                    }
                )

        return jsonify(debug_info)

    except Exception as e:
        return jsonify({"error": str(e), "traceback": str(e.__traceback__)})


@app.route("/wardrobe-data")
def get_wardrobe_data():
    """API para obtener datos del armario"""
    try:
        # Usar datos locales reales en lugar de los SVG de Mariel
        try:
            with open("data/wardrobe_updated.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ Cargado wardrobe_updated.json con {len(data)} entradas")
            return jsonify(data)
        except FileNotFoundError:
            # Si no existe, usar el original
            with open("data/wardrobe.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"⚠️ Usando wardrobe.json original con {len(data)} entradas")
            return jsonify(data)

    except FileNotFoundError:
        print("❌ No se encontró ningún archivo de datos del armario")
        return jsonify([])
    except Exception as e:
        print(f"❌ Error cargando datos del armario: {e}")
        return jsonify([])


@app.route("/upload_images/<path:filename>")
def serve_upload_image(filename):
    """Sirve las imágenes del armario"""
    try:
        print(f"🔍 Buscando imagen: {filename}")

        # Buscar en la carpeta upload_images local
        local_uploads_path = os.path.join(os.getcwd(), "upload_images")
        local_file_path = os.path.join(local_uploads_path, filename)
        print(f"   Intentando ruta local: {local_file_path}")

        if os.path.exists(local_file_path):
            print(f"✅ Encontrada en ruta local")
            # Configurar MIME type para diferentes tipos de archivo
            if filename.lower().endswith(".svg"):
                return send_from_directory(
                    local_uploads_path, filename, mimetype="image/svg+xml"
                )
            elif filename.lower().endswith((".jpg", ".jpeg")):
                return send_from_directory(
                    local_uploads_path, filename, mimetype="image/jpeg"
                )
            elif filename.lower().endswith(".png"):
                return send_from_directory(
                    local_uploads_path, filename, mimetype="image/png"
                )
            else:
                return send_from_directory(local_uploads_path, filename)

        # Listar archivos disponibles para debug
        print(f"❌ Imagen no encontrada: {filename}")
        if os.path.exists(local_uploads_path):
            local_files = os.listdir(local_uploads_path)
            print(
                f"   Archivos disponibles: {local_files[:10]}"
            )  # Solo mostrar primeros 10

        abort(404)
    except Exception as e:
        print(f"Error serving image {filename}: {e}")
        abort(404)


@app.route("/upload", methods=["POST"])
def upload():
    try:
        # Ejecutar prueba de colores al inicio (solo para debug)
        test_color_detection()

        img = None
        timestamp = str(int(time.time()))
        original_image_path = None
        is_file_upload = False

        if "image" in request.form:
            base64_data = request.form.get("image")
            if base64_data.startswith("data:image"):
                base64_data = base64_data.split(",")[1]

            image_data = base64.b64decode(base64_data)
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            filename = f"{timestamp}.jpg"
            file_path = os.path.join("upload_images", filename)
            cv2.imwrite(file_path, img)

        elif "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400

            filename = secure_filename(f"{timestamp}_{file.filename}")
            file_path = os.path.join("upload_images", filename)
            file.save(file_path)
            img = cv2.imread(file_path)
            original_image_path = f"upload_images/{filename}"
            is_file_upload = True

        else:
            return jsonify({"error": "No image provided"}), 400

        if img is None:
            return jsonify({"error": "Could not process image"}), 400

        h, w = img.shape[:2]
        inputs = processor(images=img[:, :, ::-1], return_tensors="pt")
        outputs = model(**inputs)
        results = processor.post_process_object_detection(
            outputs, threshold=0.5, target_sizes=torch.tensor([[h, w]])
        )[0]

        items = []

        for i, (score, label, box) in enumerate(
            zip(results["scores"], results["labels"], results["boxes"])
        ):
            x1, y1, x2, y2 = [int(coord) for coord in box.tolist()]

            if x2 - x1 < 30 or y2 - y1 < 30:
                continue

            item_type = model.config.id2label[label.item()]

            if is_filtered_item(item_type):
                continue

            crop = img[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            # Extraer color dominante y validarlo/mejorarlo
            dominant_rgb = get_dominant_color(crop)
            dominant_rgb = enhance_color_by_garment_type(dominant_rgb, item_type)
            dominant_rgb = validate_and_enhance_color(dominant_rgb, item_type)

            # Debug: imprimir el color extraído
            color_name = rgb_to_color_name(dominant_rgb)
            print(f"Tipo: {item_type}, Color RGB: {dominant_rgb}, Nombre: {color_name}")

            crop_filename = f"{timestamp}_{item_type}_{i}.jpg"
            crop_path = os.path.join("upload_images", crop_filename)
            cv2.imwrite(crop_path, crop)

            items.append(
                {
                    "tipo": item_type,
                    "color_rgb": dominant_rgb,
                    "color_name": color_name,
                    "img_path": f"upload_images/{crop_filename}",
                    "score": float(score.item()),
                }
            )

        wardrobe_data = []
        if os.path.exists(DB_JSON):
            with open(DB_JSON, "r") as f:
                wardrobe_data = json.load(f)

        wardrobe_data.extend(items)

        with open(DB_JSON, "w") as f:
            json.dump(wardrobe_data, f, indent=2)

        if not items:
            response_data = {"detected": []}
            if is_file_upload and original_image_path:
                response_data["original_image"] = original_image_path
            return jsonify(response_data)

        response_data = {"detected": items}
        if is_file_upload and original_image_path:
            response_data["original_image"] = original_image_path

        return jsonify(response_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/wardrobe")
def get_wardrobe():
    if os.path.exists(DB_JSON):
        with open(DB_JSON, "r") as f:
            wardrobe_data = json.load(f)
        return jsonify(wardrobe_data)
    return jsonify([])


# ===================== RUTAS PARA AGENDA DE LOOKS =====================

# Lista de eventos (simulando base de datos en memoria)
agenda_eventos = []

# Importar funciones necesarias para la agenda
import requests
from transformers import CLIPProcessor, CLIPModel
import torch
from sklearn.metrics.pairwise import cosine_similarity

# Configuración para agenda
WEATHER_API_KEY = "53c0cdba3f617d813f3043fa38c3225c"

# Cargar modelo CLIP (solo si no está cargado)
try:
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
except:
    clip_model = None
    clip_processor = None
    print("⚠️ No se pudo cargar el modelo CLIP para recomendaciones")


def load_wardrobe_for_agenda():
    """Cargar prendas del armario para la agenda"""
    try:
        # Intentar cargar el archivo actualizado primero
        try:
            with open("data/wardrobe_updated.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # Si no existe, usar el original
            with open("data/wardrobe.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        return []


def sugerir_outfit_agenda(descripcion):
    """Sugerencia de outfit según descripción usando CLIP"""
    if not clip_model or not clip_processor:
        return "Sistema de recomendaciones no disponible"

    wardrobe = load_wardrobe_for_agenda()
    if not wardrobe:
        return "No se encontraron prendas en el guardarropa"

    try:
        textos = [descripcion] + [
            f"{item['tipo']} en color {item['color_name']}" for item in wardrobe
        ]
        inputs = clip_processor(text=textos, return_tensors="pt", padding=True)
        with torch.no_grad():
            embeddings = clip_model.get_text_features(**inputs)

        query_vec = embeddings[0].unsqueeze(0)
        item_vecs = embeddings[1:]
        similarities = cosine_similarity(query_vec.numpy(), item_vecs.numpy())[0]

        top_indices = similarities.argsort()[-2:][::-1]
        selected_items = [wardrobe[i] for i in top_indices]

        if len(selected_items) > 1:
            return f"Te sugiero combinar {selected_items[0]['tipo']} en color {selected_items[0]['color_name']} con {selected_items[1]['tipo']} en color {selected_items[1]['color_name']}"
        else:
            return f"Te sugiero usar {selected_items[0]['tipo']} en color {selected_items[0]['color_name']}"
    except Exception as e:
        return f"Error al generar recomendación: {str(e)}"


def get_weather_agenda(ciudad="Lima"):
    """Función clima con OpenWeatherMap"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={ciudad}&appid={WEATHER_API_KEY}&units=metric"
    try:
        r = requests.get(url)
        data = r.json()
        return {
            "temp": data["main"]["temp"],
            "desc": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"],
        }
    except:
        return {"temp": "?", "desc": "No disponible", "icon": "01d"}


@app.route("/agenda-eventos")
def obtener_eventos_agenda():
    """Listar eventos de la agenda"""
    return jsonify(agenda_eventos)


@app.route("/agenda-agregar-evento", methods=["POST"])
def agregar_evento_agenda():
    """Guardar eventos en la agenda"""
    data = request.get_json()
    evento = {
        "titulo": data["titulo"],
        "fecha": data["fecha"],
        "descripcion": data["descripcion"],
    }
    agenda_eventos.append(evento)
    return jsonify({"status": "ok", "evento": evento})


@app.route("/agenda-clima")
def clima_agenda():
    """Obtener clima para la agenda"""
    ciudad = request.args.get("ciudad", "Lima")
    return jsonify(get_weather_agenda(ciudad))


@app.route("/agenda-recomendar", methods=["POST"])
def recomendar_agenda():
    """Obtener sugerencia de outfit para la agenda"""
    data = request.get_json()
    descripcion = data.get("descripcion", "")
    recomendacion = sugerir_outfit_agenda(descripcion)
    return jsonify({"recomendacion": recomendacion})


# ===================== RUTAS PARA COMBINACIONES =====================


def generar_combinaciones():
    """Genera combinaciones automáticas de ropa"""
    try:
        # Cargar datos del armario
        try:
            with open("data/wardrobe_updated.json", "r", encoding="utf-8") as f:
                wardrobe = json.load(f)
        except FileNotFoundError:
            with open("data/wardrobe.json", "r", encoding="utf-8") as f:
                wardrobe = json.load(f)

        if not wardrobe:
            return []

        # Separar por categorías
        tops = [
            item
            for item in wardrobe
            if any(
                tipo in item["tipo"].lower()
                for tipo in ["shirt", "blouse", "top", "t-shirt", "sweatshirt"]
            )
        ]
        bottoms = [
            item
            for item in wardrobe
            if any(tipo in item["tipo"].lower() for tipo in ["pants", "jeans", "skirt"])
        ]
        dresses = [item for item in wardrobe if "dress" in item["tipo"].lower()]
        outerwear = [
            item
            for item in wardrobe
            if any(
                tipo in item["tipo"].lower()
                for tipo in ["jacket", "coat", "blazer", "cardigan"]
            )
        ]
        accessories = [
            item
            for item in wardrobe
            if any(
                tipo in item["tipo"].lower()
                for tipo in ["glasses", "hat", "bag", "belt", "tie"]
            )
        ]

        combinaciones = []

        # Tipo 1: Combinaciones con vestidos
        for dress in dresses:
            combo = {
                "id": len(combinaciones) + 1,
                "nombre": f"Look con {dress['color_name']}",
                "tipo": "vestido",
                "ocasion": "elegante",
                "prendas": [dress],
                "puntuacion": 85 + (len(combinaciones) % 15),  # Variación en puntuación
            }

            # Agregar chaqueta si hay
            if outerwear:
                jacket = outerwear[len(combinaciones) % len(outerwear)]
                combo["prendas"].append(jacket)
                combo["nombre"] = (
                    f"Look {dress['color_name']} con {jacket['color_name']}"
                )

            # Agregar accesorio ocasionalmente
            if accessories and len(combinaciones) % 3 == 0:
                acc = accessories[len(combinaciones) % len(accessories)]
                combo["prendas"].append(acc)

            combinaciones.append(combo)

        # Tipo 2: Combinaciones top + bottom
        for i, top in enumerate(tops):
            for j, bottom in enumerate(bottoms):
                if len(combinaciones) >= 20:  # Limitar a 20 combinaciones
                    break

                # Lógica básica de combinación de colores
                combo_score = 70
                ocasion = "casual"

                # Mejorar puntuación si los colores combinan bien
                if top["color_name"].lower() in ["blanco", "negro", "gris"] or bottom[
                    "color_name"
                ].lower() in ["blanco", "negro", "gris"]:
                    combo_score += 15
                    ocasion = "versátil"

                # Combinaciones específicas
                if (
                    "azul" in top["color_name"].lower()
                    and "negro" in bottom["color_name"].lower()
                ) or (
                    "negro" in top["color_name"].lower()
                    and "azul" in bottom["color_name"].lower()
                ):
                    combo_score += 10
                    ocasion = "profesional"

                combo = {
                    "id": len(combinaciones) + 1,
                    "nombre": f"Combo {top['color_name']} & {bottom['color_name']}",
                    "tipo": "combinacion",
                    "ocasion": ocasion,
                    "prendas": [top, bottom],
                    "puntuacion": combo_score + (i + j) % 20,
                }

                # Agregar chaqueta para algunas combinaciones
                if outerwear and (i + j) % 4 == 0:
                    jacket = outerwear[(i + j) % len(outerwear)]
                    combo["prendas"].append(jacket)
                    combo["puntuacion"] += 5
                    combo["ocasion"] = "formal"

                # Agregar accesorio
                if accessories and (i + j) % 5 == 0:
                    acc = accessories[(i + j) % len(accessories)]
                    combo["prendas"].append(acc)
                    combo["puntuacion"] += 3

                combinaciones.append(combo)

        # Ordenar por puntuación
        combinaciones.sort(key=lambda x: x["puntuacion"], reverse=True)

        return combinaciones[:15]  # Devolver top 15

    except Exception as e:
        print(f"Error generando combinaciones: {e}")
        return []


@app.route("/combinaciones-data")
def get_combinaciones_data():
    """API para obtener combinaciones generadas"""
    combinaciones = generar_combinaciones()
    return jsonify(combinaciones)


@app.route("/combinacion-detalle/<int:combo_id>")
def get_combinacion_detalle(combo_id):
    """API para obtener detalles de una combinación específica"""
    combinaciones = generar_combinaciones()
    combo = next((c for c in combinaciones if c["id"] == combo_id), None)

    if combo:
        return jsonify(combo)
    else:
        return jsonify({"error": "Combinación no encontrada"}), 404


# ===================== RUTAS PARA COMUNIDAD =====================

def load_community_data():
    """Cargar datos de la comunidad desde JSON"""
    try:
        with open("data/community.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"posts": []}
    except Exception as e:
        print(f"Error cargando datos de comunidad: {e}")
        return {"posts": []}


def load_users_data():
    """Cargar datos de usuarios desde JSON"""
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}
    except Exception as e:
        print(f"Error cargando datos de usuarios: {e}")
        return {"users": []}


def save_community_data(data):
    """Guardar datos de la comunidad en JSON"""
    try:
        with open("data/community.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error guardando datos de comunidad: {e}")
        return False


@app.route("/api/community/posts", methods=["GET"])
def get_community_posts():
    """API para obtener todos los posts de la comunidad"""
    try:
        community_data = load_community_data()
        users_data = load_users_data()
        
        # Enriquecer posts con información de usuarios
        for post in community_data.get("posts", []):
            user = next((u for u in users_data.get("users", []) if u["id"] == post["user_id"]), None)
            if user:
                post["user"] = {
                    "name": user["name"],
                    "username": user["username"],
                    "avatar": user["avatar"],
                    "verified": user.get("verified", False)
                }
        
        return jsonify(community_data)
    except Exception as e:
        print(f"Error obteniendo posts: {e}")
        return jsonify({"error": "Error al cargar posts"}), 500


@app.route("/api/community/post", methods=["POST"])
def create_community_post():
    """API para crear un nuevo post en la comunidad"""
    try:
        # Obtener datos del formulario
        description = request.form.get("description")
        ocasion = request.form.get("ocasion", "")
        tags_json = request.form.get("tags", "[]")
        
        # Parsear tags
        try:
            tags = json.loads(tags_json)
        except:
            tags = []
        
        # Manejar imagen
        image_file = request.files.get("image")
        if not image_file:
            return jsonify({"error": "Imagen requerida"}), 400
        
        # Guardar imagen
        timestamp = int(time.time())
        filename = secure_filename(f"{timestamp}_{image_file.filename}")
        image_path = os.path.join("upload_images", filename)
        image_file.save(image_path)
        
        # Crear nuevo post
        community_data = load_community_data()
        
        # Generar ID único para el post
        existing_ids = [post.get("id", "").replace("post", "") for post in community_data.get("posts", [])]
        numeric_ids = [int(id_num) for id_num in existing_ids if id_num.isdigit()]
        new_id = max(numeric_ids, default=0) + 1
        
        new_post = {
            "id": f"post{new_id}",
            "user_id": "user1",  # En una implementación real, esto vendría de la sesión
            "image": f"/{image_path}",  # URL relativa para la imagen
            "description": description,
            "tags": tags,
            "ocasion": ocasion,
            "weather": "templado",  # Se podría integrar con API del clima
            "timestamp": f"{time.strftime('%Y-%m-%dT%H:%M:%S')}Z",
            "likes": 0,
            "comments": [],
            "saved_by": []
        }
        
        # Agregar post al inicio de la lista
        if "posts" not in community_data:
            community_data["posts"] = []
        community_data["posts"].insert(0, new_post)
        
        # Guardar datos actualizados
        if save_community_data(community_data):
            return jsonify({"success": True, "post": new_post})
        else:
            return jsonify({"error": "Error al guardar post"}), 500
            
    except Exception as e:
        print(f"Error creando post: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500


@app.route("/api/community/users")
def get_community_users():
    """API para obtener información de usuarios"""
    return jsonify(load_users_data())


@app.route("/api/community/like", methods=["POST"])
def toggle_post_like():
    """API para dar/quitar like a un post"""
    try:
        data = request.get_json()
        post_id = data.get("postId")
        action = data.get("action")  # 'like' o 'unlike'
        
        community_data = load_community_data()
        post = next((p for p in community_data.get("posts", []) if p["id"] == post_id), None)
        
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        if action == "like":
            post["likes"] = post.get("likes", 0) + 1
        elif action == "unlike":
            post["likes"] = max(0, post.get("likes", 0) - 1)
        
        save_community_data(community_data)
        return jsonify({"success": True, "likes": post["likes"]})
        
    except Exception as e:
        print(f"Error en toggle like: {e}")
        return jsonify({"error": "Error interno"}), 500


@app.route("/api/community/save", methods=["POST"])
def toggle_post_save():
    """API para guardar/desguardar un post"""
    try:
        data = request.get_json()
        post_id = data.get("postId")
        user_id = "user1"  # En implementación real vendría de la sesión
        
        community_data = load_community_data()
        post = next((p for p in community_data.get("posts", []) if p["id"] == post_id), None)
        
        if not post:
            return jsonify({"error": "Post no encontrado"}), 404
        
        saved_by = post.get("saved_by", [])
        
        if user_id in saved_by:
            saved_by.remove(user_id)
            action = "unsaved"
        else:
            saved_by.append(user_id)
            action = "saved"
        
        post["saved_by"] = saved_by
        save_community_data(community_data)
        
        return jsonify({"success": True, "action": action, "saved_count": len(saved_by)})
        
    except Exception as e:
        print(f"Error en toggle save: {e}")
        return jsonify({"error": "Error interno"}), 500


if __name__ == "__main__":
    app.run(debug=True)

# → IMPORTANTE: conectar este backend, carpeta upload_images y endpoint /upload
# con los otros módulos del proyecto (frontend, armario, try‑on, agenda, comunidad…)
