import json
import os

print("=== VERIFICANDO Y ACTUALIZANDO WARDROBE ===")

# Leer wardrobe.json original
wardrobe_path = '../Deteccion_de_ropa/data/wardrobe.json'
with open(wardrobe_path, 'r', encoding='utf-8') as f:
    original_data = json.load(f)

# Directorio de imágenes
upload_dir = '../Deteccion_de_ropa/upload_images'
available_images = set(os.listdir(upload_dir))

print(f"📁 Imágenes disponibles: {len(available_images)}")
print(f"📋 Entradas en wardrobe.json: {len(original_data)}")
print("\n" + "="*60)

# Filtrar solo las entradas que tienen imágenes disponibles
valid_entries = []
missing_count = 0

for i, item in enumerate(original_data):
    img_path = item['img_path']
    filename = img_path.replace('upload_images/', '')
    
    if filename in available_images:
        valid_entries.append(item)
        color_hex = "#{:02x}{:02x}{:02x}".format(item['color_rgb'][0], item['color_rgb'][1], item['color_rgb'][2])
        print(f"✅ {filename}")
        print(f"   Tipo: {item['tipo']} | Color: {item['color_name']} {color_hex}")
    else:
        missing_count += 1
        if missing_count <= 5:  # Solo mostrar primeros 5
            print(f"❌ {filename} - {item['tipo']} (FALTANTE)")

if missing_count > 5:
    print(f"❌ ... y {missing_count - 5} imágenes más faltantes")

print("\n" + "="*60)
print(f"📊 RESUMEN:")
print(f"✅ Entradas válidas: {len(valid_entries)}")
print(f"❌ Entradas con imágenes faltantes: {missing_count}")

# Guardar wardrobe filtrado
if valid_entries:
    updated_path = '../Deteccion_de_ropa/data/wardrobe_updated.json'
    with open(updated_path, 'w', encoding='utf-8') as f:
        json.dump(valid_entries, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Wardrobe filtrado guardado: wardrobe_updated.json")
    print(f"📦 Contiene {len(valid_entries)} prendas con imágenes válidas")
    
    # Mostrar estadísticas por tipo
    tipo_count = {}
    for item in valid_entries:
        tipo = item['tipo']
        tipo_count[tipo] = tipo_count.get(tipo, 0) + 1
    
    print(f"\n📈 Distribución por tipo:")
    for tipo, count in sorted(tipo_count.items()):
        print(f"   {tipo}: {count} prendas")

else:
    print("\n⚠️  No se encontraron entradas válidas")

print(f"\n🔧 Para usar el wardrobe actualizado:")
print(f"   Modifica app.py para leer 'wardrobe_updated.json'")
