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


if __name__ == "__main__":
    app.run(debug=True)

# → IMPORTANTE: conectar este backend, carpeta upload_images y endpoint /upload
# con los otros módulos del proyecto (frontend, armario, try‑on, agenda, comunidad…)
