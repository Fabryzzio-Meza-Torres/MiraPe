from flask import Flask, request, jsonify, render_template
import requests
from transformers import CLIPProcessor, CLIPModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import json

app = Flask(__name__)

WEATHER_API_KEY = "53c0cdba3f617d813f3043fa38c3225c"  
eventos = []

# Cargar modelo CLIP
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# Cargar prendas del armario
def load_wardrobe():
    try:
        with open("wardrobe_updated.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []

# Sugerencia de outfit según descripción usando CLIP
def sugerir_outfit(descripcion):
    wardrobe = load_wardrobe()
    if not wardrobe:
        return "No se encontraron prendas en el guardarropa"

    textos = [descripcion] + [f"{item['tipo']} en color {item['color_name']}" for item in wardrobe]
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
        "descripcion": data["descripcion"]
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
    data = request.get_json()
    descripcion = data.get("descripcion", "")
    recomendacion = sugerir_outfit(descripcion)
    return jsonify({"recomendacion": recomendacion})

# Función clima con OpenWeatherMap
def get_weather(ciudad="Lima"):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={ciudad}&appid={WEATHER_API_KEY}&units=metric"
    try:
        r = requests.get(url)
        data = r.json()
        return {
            "temp": data["main"]["temp"],
            "desc": data["weather"][0]["description"],
            "icon": data["weather"][0]["icon"]
        }
    except:
        return {"temp": "?", "desc": "No disponible", "icon": "01d"}

if __name__ == "__main__":
    app.run(debug=True)
