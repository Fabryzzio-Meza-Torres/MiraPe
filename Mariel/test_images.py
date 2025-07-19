import json
import os

# Leer el wardrobe_updated.json
with open('../Deteccion_de_ropa/data/wardrobe_updated.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Verificando imágenes en wardrobe_updated.json:")
print("=" * 60)

for i, item in enumerate(data):
    img_path = item['img_path']
    filename = img_path.replace('upload_images/', '')
    full_path = os.path.join('..', 'Deteccion_de_ropa', 'upload_images', filename)
    
    print(f"\n{i+1}. {item['tipo']}")
    print(f"   Archivo: {filename}")
    print(f"   Color RGB: {item['color_rgb']}")
    print(f"   Color HEX: #{item['color_rgb'][0]:02x}{item['color_rgb'][1]:02x}{item['color_rgb'][2]:02x}")
    print(f"   Existe: {'✓' if os.path.exists(full_path) else '✗'}")
    print(f"   Ruta completa: {full_path}")

print(f"\n" + "=" * 60)
print(f"Total de imágenes verificadas: {len(data)}")
