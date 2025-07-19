import json
import os

# Leer el wardrobe.json
with open('../Deteccion_de_ropa/data/wardrobe.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Directorio de imágenes
upload_dir = '../Deteccion_de_ropa/upload_images'

print("Verificando archivos de imágenes...")
print("=" * 50)

# Listar archivos disponibles
available_files = os.listdir(upload_dir)
print(f"Archivos disponibles en {upload_dir}:")
for file in sorted(available_files):
    print(f"  ✓ {file}")

print("\n" + "=" * 50)
print("Archivos referenciados en wardrobe.json:")

missing_files = []
existing_files = []

for item in data[:10]:  # Solo revisar los primeros 10
    img_path = item['img_path']
    filename = img_path.replace('upload_images/', '')
    full_path = os.path.join(upload_dir, filename)
    
    if os.path.exists(full_path):
        existing_files.append(filename)
        print(f"  ✓ {filename} - {item['tipo']}")
    else:
        missing_files.append(filename)
        print(f"  ✗ {filename} - {item['tipo']} (NO EXISTE)")

print(f"\nResumen:")
print(f"Archivos existentes: {len(existing_files)}")
print(f"Archivos faltantes: {len(missing_files)}")

if missing_files:
    print(f"\nArchivos faltantes:")
    for file in missing_files:
        print(f"  - {file}")
