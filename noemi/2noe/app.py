from flask import Flask, request, jsonify, render_template
import requests
from transformers import CLIPProcessor, CLIPModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import json
import random
import numpy as np

app = Flask(__name__)

WEATHER_API_KEY = "53c0cdba3f617d813f3043fa38c3225c"
eventos = []

# Cargar modelo CLIP
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")


# Cargar prendas del armario
def load_wardrobe():
    try:
        # Intentar cargar el archivo actualizado primero
        print("DEBUG: Intentando cargar wardrobe_updated.json")
        with open(
            "C:\\Users\\ASUS\\OneDrive\\Documentos\\MiraPe-\\Deteccion_de_ropa\\data\\wardrobe_updated.json",
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
            print(f"DEBUG: Cargado wardrobe_updated.json con {len(data)} prendas")
            return data
    except FileNotFoundError:
        try:
            # Si no existe, usar el original
            print("DEBUG: wardrobe_updated.json no encontrado, usando wardrobe.json")
            with open(
                "C:\\Users\\ASUS\\OneDrive\\Documentos\\MiraPe-\\Deteccion_de_ropa\\data\\wardrobe.json",
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
                print(f"DEBUG: Cargado wardrobe.json con {len(data)} prendas")
                return data
        except Exception as e:
            print(f"DEBUG: Error cargando wardrobe.json: {e}")
            return []
    except Exception as e:
        print(f"DEBUG: Error cargando archivo de armario: {e}")
        return []


# Sugerencia de outfit según descripción usando CLIP
def sugerir_outfit(descripcion):
    print(f"DEBUG: Recibida descripción: '{descripcion}'")

    wardrobe = load_wardrobe()
    if not wardrobe:
        print("DEBUG: No se encontraron prendas en el armario")
        return "No se encontraron prendas en el guardarropa"

    print(f"DEBUG: Se encontraron {len(wardrobe)} prendas en el armario")

    # Separar por tipos de prenda para mejores combinaciones
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

    print(
        f"DEBUG: Tops: {len(tops)}, Bottoms: {len(bottoms)}, Dresses: {len(dresses)}, Outerwear: {len(outerwear)}, Accessories: {len(accessories)}"
    )

    # Análisis de contexto para mejores recomendaciones
    descripcion_lower = descripcion.lower()

    # Palabras clave para diferentes ocasiones
    formal_keywords = [
        "trabajo",
        "oficina",
        "reunión",
        "presentación",
        "formal",
        "elegante",
        "profesional",
    ]
    casual_keywords = [
        "casual",
        "relajado",
        "cómodo",
        "paseo",
        "universidad",
        "estudiar",
    ]
    party_keywords = [
        "fiesta",
        "celebración",
        "noche",
        "salir",
        "cena",
        "romántico",
        "especial",
    ]
    sport_keywords = ["ejercicio", "gym", "deporte", "correr", "entrenar"]
    weather_keywords = ["frío", "calor", "lluvia", "sol", "invierno", "verano"]

    occasion_type = "casual"  # default

    if any(keyword in descripcion_lower for keyword in formal_keywords):
        occasion_type = "formal"
    elif any(keyword in descripcion_lower for keyword in party_keywords):
        occasion_type = "party"
    elif any(keyword in descripcion_lower for keyword in sport_keywords):
        occasion_type = "sport"

    print(f"DEBUG: Tipo de ocasión detectado: {occasion_type}")

    try:
        # Estrategia de selección más diversa
        selected_items = []
        outfit_parts = []

        # Decidir si usar vestido o combinación top+bottom (50% probabilidad)
        use_dress = len(dresses) > 0 and random.random() < 0.5

        if use_dress and occasion_type in ["party", "formal", "casual"]:
            # Seleccionar vestido aleatoriamente
            dress_item = random.choice(dresses)
            outfit_parts.append(f"{dress_item['tipo']} {dress_item['color_name']}")
            selected_items.append(dress_item)
            print(
                f"DEBUG: Seleccionado vestido: {dress_item['tipo']} {dress_item['color_name']}"
            )

            # Agregar accesorios o chaqueta si corresponde
            if len(outerwear) > 0 and (
                occasion_type == "formal" or "frío" in descripcion_lower
            ):
                jacket_item = random.choice(outerwear)
                outfit_parts.append(
                    f"{jacket_item['tipo']} {jacket_item['color_name']}"
                )
                selected_items.append(jacket_item)

            if (
                len(accessories) > 0 and random.random() < 0.7
            ):  # 70% probabilidad de agregar accesorio
                acc_item = random.choice(accessories)
                outfit_parts.append(f"{acc_item['tipo']} {acc_item['color_name']}")

        else:
            # Estrategia tradicional: top + bottom con mayor diversidad

            # Usar CLIP para encontrar prendas relevantes pero con diversidad
            available_items = []

            # Filtrar según ocasión pero mantener diversidad
            if occasion_type == "formal":
                available_items = [
                    item
                    for item in wardrobe
                    if any(
                        tipo in item["tipo"].lower()
                        for tipo in ["shirt", "blouse", "blazer", "jacket", "pants"]
                    )
                ]
            elif occasion_type == "party":
                available_items = [
                    item
                    for item in wardrobe
                    if any(
                        tipo in item["tipo"].lower()
                        for tipo in [
                            "blouse",
                            "shirt",
                            "top",
                            "jacket",
                            "skirt",
                            "pants",
                        ]
                    )
                ]
            else:
                available_items = [
                    item for item in wardrobe if "dress" not in item["tipo"].lower()
                ]  # Excluir vestidos para combinaciones

            if len(available_items) < 4:
                available_items = wardrobe  # Usar todo si hay pocas opciones

            # Selección con CLIP pero con aleatorización
            query_text = f"outfit for {descripcion}"
            contextos = [query_text] + [
                f"{item['tipo']} {item['color_name']}" for item in available_items
            ]

            inputs = clip_processor(text=contextos, return_tensors="pt", padding=True)
            with torch.no_grad():
                embeddings = clip_model.get_text_features(**inputs)

            query_vec = embeddings[0].unsqueeze(0)
            item_vecs = embeddings[1:]
            similarities = cosine_similarity(query_vec.numpy(), item_vecs.numpy())[0]

            # En lugar de tomar solo los top, usar probabilidades ponderadas
            # Normalizar similitudes para usarlas como probabilidades
            similarities_positive = np.maximum(
                similarities, 0.1
            )  # Evitar valores negativos
            probabilities = similarities_positive / np.sum(similarities_positive)

            # Seleccionar top con probabilidad ponderada
            available_tops = [
                item
                for item in available_items
                if any(
                    tipo in item["tipo"].lower()
                    for tipo in ["shirt", "blouse", "top", "t-shirt", "sweatshirt"]
                )
            ]
            if available_tops:
                # Encontrar índices de tops en available_items
                top_indices = [
                    i
                    for i, item in enumerate(available_items)
                    if item in available_tops
                ]
                if top_indices:
                    # Usar probabilidades para seleccionar
                    top_probs = [probabilities[i] for i in top_indices]
                    top_probs = np.array(top_probs) / np.sum(top_probs)  # Re-normalizar

                    selected_top_idx = np.random.choice(len(top_indices), p=top_probs)
                    top_item = available_tops[selected_top_idx]
                    outfit_parts.append(f"{top_item['tipo']} {top_item['color_name']}")
                    selected_items.append(top_item)

            # Seleccionar bottom
            available_bottoms = [
                item
                for item in available_items
                if any(
                    tipo in item["tipo"].lower() for tipo in ["pants", "jeans", "skirt"]
                )
                and item not in selected_items
            ]
            if available_bottoms:
                bottom_item = random.choice(
                    available_bottoms
                )  # Selección aleatoria para mayor diversidad
                outfit_parts.append(
                    f"{bottom_item['tipo']} {bottom_item['color_name']}"
                )
                selected_items.append(bottom_item)

            # Agregar outerwear si es apropiado
            if len(outerwear) > 0 and (
                occasion_type == "formal"
                or "frío" in descripcion_lower
                or random.random() < 0.3
            ):
                available_outer = [
                    item for item in outerwear if item not in selected_items
                ]
                if available_outer:
                    outer_item = random.choice(available_outer)
                    outfit_parts.append(
                        f"{outer_item['tipo']} {outer_item['color_name']}"
                    )

            # Agregar accesorio ocasionalmente
            if len(accessories) > 0 and random.random() < 0.4:  # 40% probabilidad
                available_acc = [
                    item for item in accessories if item not in selected_items
                ]
                if available_acc:
                    acc_item = random.choice(available_acc)
                    outfit_parts.append(f"{acc_item['tipo']} {acc_item['color_name']}")

        # Generar respuesta final
        if len(outfit_parts) >= 2:
            # Agregar variedad en el texto de respuesta
            respuestas_inicio = [
                f"Para '{descripcion}', te recomiendo",
                f"Para tu evento '{descripcion}', sugiero",
                f"Perfecto para '{descripcion}', prueba con",
                f"Una excelente opción para '{descripcion}' sería",
                f"Para '{descripcion}', combina",
            ]
            inicio = random.choice(respuestas_inicio)
            response = f"{inicio}: " + ", ".join(outfit_parts)
        elif len(outfit_parts) == 1:
            response = f"Para '{descripcion}', te sugiero: {outfit_parts[0]}"
        else:
            # Fallback con selección completamente aleatoria
            if len(wardrobe) >= 2:
                random_items = random.sample(wardrobe, 2)
                response = f"Te sugiero combinar {random_items[0]['tipo']} {random_items[0]['color_name']} con {random_items[1]['tipo']} {random_items[1]['color_name']}"
            else:
                response = (
                    "No hay suficientes prendas para crear una recomendación completa"
                )

        print(f"DEBUG: Respuesta generada: {response}")
        return response

    except Exception as e:
        print(f"DEBUG: Error en sugerir_outfit: {str(e)}")
        import traceback

        traceback.print_exc()
        return f"Error al generar recomendación: {str(e)}"


# Ruta principal
@app.route("/")
def index():
    return render_template("index.html")


# Guardar eventos
@app.route("/agregar_evento", methods=["POST"])
def agregar_evento():
    data = request.get_json()
    evento = {
        "titulo": data["titulo"],
        "fecha": data["fecha"],
        "descripcion": data["descripcion"],
    }
    eventos.append(evento)
    return jsonify({"status": "ok", "evento": evento})


# Listar eventos
@app.route("/eventos")
def obtener_eventos():
    return jsonify(eventos)


# Obtener clima
@app.route("/clima")
def clima():
    ciudad = request.args.get("ciudad", "Lima")
    return jsonify(get_weather(ciudad))


# Obtener sugerencia de outfit
@app.route("/recomendar", methods=["POST"])
def recomendar():
    try:
        data = request.get_json()
        print(f"DEBUG: Datos recibidos en /recomendar: {data}")

        if not data:
            return jsonify({"error": "No se recibieron datos"}), 400

        descripcion = data.get("descripcion", "").strip()
        print(f"DEBUG: Descripción extraída: '{descripcion}'")

        if not descripcion:
            return jsonify(
                {
                    "recomendacion": "Por favor, describe el tipo de evento para obtener una mejor recomendación."
                }
            )

        recomendacion = sugerir_outfit(descripcion)
        print(f"DEBUG: Recomendación generada: {recomendacion}")

        return jsonify({"recomendacion": recomendacion})

    except Exception as e:
        print(f"ERROR en /recomendar: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


# Ruta de prueba para verificar el armario
@app.route("/test-wardrobe")
def test_wardrobe():
    try:
        wardrobe = load_wardrobe()
        return jsonify(
            {
                "total_items": len(wardrobe),
                "first_5_items": wardrobe[:5] if wardrobe else [],
                "types_available": list(
                    set([item.get("tipo", "unknown") for item in wardrobe])
                ),
                "colors_available": list(
                    set([item.get("color_name", "unknown") for item in wardrobe])
                ),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)})


# Función clima con OpenWeatherMap
def get_weather(ciudad="Lima"):
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


if __name__ == "__main__":
    app.run(debug=True)
