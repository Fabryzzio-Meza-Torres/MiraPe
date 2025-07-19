import json
import os

# Leer el wardrobe.json actualizado
with open('../Deteccion_de_ropa/data/wardrobe.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Directorio de imágenes
upload_dir = '../Deteccion_de_ropa/upload_images'
available_files = os.listdir(upload_dir)

print("Verificando coincidencias entre wardrobe.json y upload_images:")
print("=" * 70)

print(f"\nArchivos disponibles en upload_images:")
for file in sorted(available_files):
    print(f"  ✓ {file}")

print(f"\nVerificando archivos del wardrobe.json:")
existing_count = 0
missing_count = 0

for i, item in enumerate(data):
    img_path = item['img_path']
    filename = img_path.replace('upload_images/', '')
    full_path = os.path.join(upload_dir, filename)
    
    exists = os.path.exists(full_path)
    status = "✓" if exists else "✗"
    
    print(f"  {status} {item['tipo']} -> {filename}")
    
    if exists:
        existing_count += 1
        # Mostrar el color dominante
        color_hex = f"#{item['color_rgb'][0]:02x}{item['color_rgb'][1]:02x}{item['color_rgb'][2]:02x}"
        print(f"    Color: {item.get('color_name', 'N/A')} ({color_hex})")
    else:
        missing_count += 1

print(f"\n" + "=" * 70)
print(f"Resumen:")
print(f"  Archivos existentes: {existing_count}")
print(f"  Archivos faltantes: {missing_count}")
print(f"  Total en JSON: {len(data)}")

if missing_count == 0:
    print("\n🎉 ¡Todas las imágenes están disponibles! La aplicación debería funcionar correctamente.")
else:
    print(f"\n⚠️  Faltan {missing_count} imágenes. Necesitas actualizar las rutas o agregar las imágenes faltantes.")
