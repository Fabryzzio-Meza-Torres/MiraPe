import json
import os

# Leer el wardrobe.json actual
with open('../Deteccion_de_ropa/data/wardrobe.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Directorio de imágenes
upload_dir = '../Deteccion_de_ropa/upload_images'
available_files = os.listdir(upload_dir)

# Crear mapeo de tipos de prenda a archivos disponibles
clothing_map = {}
for file in available_files:
    if 'glasses' in file:
        if 'glasses' not in clothing_map:
            clothing_map['glasses'] = []
        clothing_map['glasses'].append(file)
    elif 'hood' in file:
        if 'hood' not in clothing_map:
            clothing_map['hood'] = []
        clothing_map['hood'].append(file)
    elif 'jacket' in file:
        if 'jacket' not in clothing_map:
            clothing_map['jacket'] = []
        clothing_map['jacket'].append(file)
    elif 'shirt' in file or 'blouse' in file:
        if 'shirt, blouse' not in clothing_map:
            clothing_map['shirt, blouse'] = []
        clothing_map['shirt, blouse'].append(file)
    elif 'top' in file or 't-shirt' in file or 'sweatshirt' in file:
        if 'top, t-shirt, sweatshirt' not in clothing_map:
            clothing_map['top, t-shirt, sweatshirt'] = []
        clothing_map['top, t-shirt, sweatshirt'].append(file)

print("Mapeo de prendas encontradas:")
for tipo, files in clothing_map.items():
    print(f"{tipo}: {files}")

# Crear nuevos datos con archivos existentes
new_data = []
used_files = set()

for item in data:
    tipo = item['tipo']
    
    # Buscar archivo disponible para este tipo
    available_file = None
    
    if tipo in clothing_map and clothing_map[tipo]:
        # Usar el primer archivo disponible que no hayamos usado
        for file in clothing_map[tipo]:
            if file not in used_files:
                available_file = file
                used_files.add(file)
                break
    
    if available_file:
        # Crear nuevo item con archivo existente
        new_item = item.copy()
        new_item['img_path'] = f"upload_images/{available_file}"
        new_data.append(new_item)
        print(f"✓ {tipo} -> {available_file}")
    else:
        print(f"✗ No hay archivo disponible para {tipo}")

print(f"\nItems creados: {len(new_data)}")

# Guardar archivo actualizado
with open('../Deteccion_de_ropa/data/wardrobe_updated.json', 'w', encoding='utf-8') as f:
    json.dump(new_data, f, indent=2, ensure_ascii=False)

print("Archivo wardrobe_updated.json creado con éxito")
