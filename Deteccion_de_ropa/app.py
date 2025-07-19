from flask import Flask, request, jsonify, send_from_directory, render_template
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


def rgb_to_color_name(rgb):
    """
    Convierte valores RGB a nombres de colores descriptivos en español
    """
    r, g, b = rgb

    # Calcular brillo y saturación
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    brightness = (max_val + min_val) / 2

    # Colores grises/neutros
    if max_val - min_val < 30:  # Muy poca diferencia entre canales
        if brightness < 60:
            return "Negro"
        elif brightness < 120:
            return "Gris oscuro"
        elif brightness < 180:
            return "Gris"
        elif brightness < 220:
            return "Gris claro"
        else:
            return "Blanco"

    # Colores dominantes
    if r > g and r > b:  # Rojizo
        if r > 200 and g < 100 and b < 100:
            return "Rojo"
        elif r > 150 and g > 100:
            if b < 100:
                return "Naranja"
            else:
                return "Rosa"
        elif r > 100 and g > 80 and b < 80:
            return "Marrón"
        else:
            return "Rojizo"

    elif g > r and g > b:  # Verdoso
        if g > 200 and r < 100 and b < 100:
            return "Verde"
        elif r > 100:
            return "Verde oliva"
        else:
            return "Verde"

    elif b > r and b > g:  # Azulado
        if b > 200 and r < 100 and g < 100:
            return "Azul"
        elif g > 100:
            return "Azul verdoso"
        elif r > 100:
            return "Morado"
        else:
            return "Azul"

    # Combinaciones especiales
    elif r > 150 and g > 150 and b < 100:  # Amarillo
        return "Amarillo"
    elif r > 100 and g < 100 and b > 100:  # Morado
        return "Morado"
    elif r > 150 and g > 100 and b > 150:  # Rosa/magenta
        return "Rosa"

    # Por defecto, usar el canal dominante
    if max(rgb) == r:
        return "Rojizo"
    elif max(rgb) == g:
        return "Verdoso"
    else:
        return "Azulado"


def enhance_color_by_garment_type(color_rgb, item_type):
    """
    Ajusta el color extraído basado en el tipo de prenda para mayor precisión
    """
    try:
        # Convertir RGB a HSV para manipular mejor el color
        rgb_normalized = np.array(color_rgb) / 255.0
        hsv = colorsys.rgb_to_hsv(
            rgb_normalized[0], rgb_normalized[1], rgb_normalized[2]
        )

        # Ajustes específicos por tipo de prenda
        h, s, v = hsv

        # Para camisas y polos, aumentar ligeramente la saturación si es muy baja
        if item_type in ["shirt", "polo", "blouse", "top"]:
            if s < 0.15:  # Color muy desaturado
                s = min(s * 1.3, 0.4)  # Aumentar saturación moderadamente

        # Para jeans, ajustar hacia tonos azules si está en el rango
        elif item_type in ["jeans", "pants"]:
            # Si el color está en el rango azul pero muy desaturado
            if 0.55 <= h <= 0.7 and s < 0.3:
                s = min(s * 1.5, 0.6)

        # Para prendas oscuras como chaquetas, evitar que se vean muy oscuras
        elif item_type in ["jacket", "coat", "blazer"]:
            if v < 0.2:  # Muy oscuro
                v = min(v * 1.2, 0.4)

        # Convertir de vuelta a RGB
        enhanced_rgb = colorsys.hsv_to_rgb(h, s, v)
        enhanced_color = [
            int(enhanced_rgb[0] * 255),
            int(enhanced_rgb[1] * 255),
            int(enhanced_rgb[2] * 255),
        ]

        return enhanced_color

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


@app.route("/upload", methods=["POST"])
def upload():
    try:
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


@app.route("/upload_images/<filename>")
def uploaded_file(filename):
    return send_from_directory("upload_images", filename)


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
