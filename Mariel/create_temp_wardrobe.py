import json
import os

print("=== GENERANDO WARDROBE TEMPORAL ===")

# Directorio de imágenes
upload_dir = '../Deteccion_de_ropa/upload_images'
available_images = sorted(os.listdir(upload_dir))

# Crear wardrobe temporal básico
temp_wardrobe = []

for img in available_images:
    # Intentar extraer tipo de la imagen del nombre
    img_lower = img.lower()
    
    if 'jacket' in img_lower:
        tipo = 'jacket'
    elif 'shirt' in img_lower or 'blouse' in img_lower:
        tipo = 'shirt'
    elif 'dress' in img_lower:
        tipo = 'dress'
    elif 'top' in img_lower or 't-shirt' in img_lower or 'sweatshirt' in img_lower:
        tipo = 'top'
    elif 'pants' in img_lower:
        tipo = 'pants'
    elif 'glasses' in img_lower:
        tipo = 'glasses'
    else:
        tipo = 'clothing'  # genérico
    
    # Crear entrada básica
    item = {
        "tipo": tipo,
        "color_rgb": [128, 128, 128],  # Gris por defecto
        "color_name": "Gris",
        "img_path": f"upload_images/{img}",
        "score": 0.8  # Score por defecto
    }
    
    temp_wardrobe.append(item)
    print(f"   ✓ {img} → {tipo}")

# Guardar wardrobe temporal
temp_path = '../Deteccion_de_ropa/data/wardrobe_temp.json'
with open(temp_path, 'w', encoding='utf-8') as f:
    json.dump(temp_wardrobe, f, indent=2, ensure_ascii=False)

print(f"\n✓ Wardrobe temporal creado: {temp_path}")
print(f"✓ Contiene {len(temp_wardrobe)} imágenes")
print(f"\nPara usarlo, actualiza app.py para leer 'wardrobe_temp.json' en lugar de 'wardrobe.json'")
