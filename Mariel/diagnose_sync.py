import json
import os

print("=== DIAGNÓSTICO COMPLETO ===")

# 1. Verificar imágenes disponibles
upload_dir = '../Deteccion_de_ropa/upload_images'
available_images = sorted(os.listdir(upload_dir))

print(f"\n1. IMÁGENES DISPONIBLES ({len(available_images)}):")
for img in available_images:
    print(f"   ✓ {img}")

# 2. Verificar wardrobe.json
wardrobe_path = '../Deteccion_de_ropa/data/wardrobe.json'
with open(wardrobe_path, 'r', encoding='utf-8') as f:
    wardrobe_data = json.load(f)

print(f"\n2. IMÁGENES EN WARDROBE.JSON ({len(wardrobe_data)}):")
missing_count = 0
existing_count = 0

for i, item in enumerate(wardrobe_data[:15]):  # Solo primeros 15
    img_path = item['img_path']
    filename = img_path.replace('upload_images/', '')
    full_path = os.path.join(upload_dir, filename)
    
    if os.path.exists(full_path):
        print(f"   ✓ {filename} - {item['tipo']}")
        existing_count += 1
    else:
        print(f"   ✗ {filename} - {item['tipo']} (FALTANTE)")
        missing_count += 1

print(f"\n3. RESUMEN:")
print(f"   Imágenes físicas disponibles: {len(available_images)}")
print(f"   Referencias en wardrobe.json: {len(wardrobe_data)}")
print(f"   Referencias que existen: {existing_count}")
print(f"   Referencias faltantes: {missing_count}")

if missing_count > 0:
    print(f"\n4. SOLUCIÓN NECESARIA:")
    print(f"   - Tu compañero actualizó las imágenes pero no el wardrobe.json")
    print(f"   - Necesitas que genere un nuevo wardrobe.json con las imágenes actuales")
    print(f"   - O necesitas las imágenes que coincidan con el wardrobe.json actual")
