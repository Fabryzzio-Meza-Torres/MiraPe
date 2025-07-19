
from flask import Flask, request, jsonify, render_template
import requests
import openai
import os

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("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")
WEATHER_API_KEY = os.getenv("bb8fdda40331256aee2056cfa2659d96")

eventos = []

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

def sugerir_outfit(descripcion):
    if OPENAI_API_KEY:
        try:
            openai.api_key = OPENAI_API_KEY
            prompt = f"Tengo este evento: '{descripcion}'. Recomiéndame un outfit adecuado. Solo una frase corta."
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response["choices"][0]["message"]["content"]
        except:
            return "No se pudo generar recomendación"
    descripcion = descripcion.lower()
    if "playa" in descripcion:
        return "Usa camisa blanca y short beige con sandalias."
    if "boda" in descripcion:
        return "Usa blazer claro y pantalón de lino."
    if "trabajo" in descripcion:
        return "Camisa celeste y pantalón oscuro."
    return "Outfit cómodo: jeans y polo básico."

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/agregar_evento', methods=['POST'])
def agregar_evento():
    data = request.get_json()
    evento = {
        "titulo": data["titulo"],
        "fecha": data["fecha"],
        "descripcion": data["descripcion"]
    }
    eventos.append(evento)
    return jsonify({"status": "ok", "evento": evento})

@app.route('/eventos')
def obtener_eventos():
    return jsonify(eventos)

@app.route('/clima')
def clima():
    ciudad = request.args.get("ciudad", "Lima")
    return jsonify(get_weather(ciudad))

@app.route('/recomendar', methods=['POST'])
def recomendar():
    data = request.get_json()
    descripcion = data.get("descripcion", "")
    recomendacion = sugerir_outfit(descripcion)
    return jsonify({"recomendacion": recomendacion})

if __name__ == '__main__':
    app.run(debug=True)
