import json
import os

def update_app_for_nobg():
    """Actualiza la aplicación para usar imágenes sin fondo"""
    
    print("=== Actualizador de App para Imágenes sin Fondo ===")
    
    # Verificar que existe el directorio con imágenes sin fondo
    nobg_dir = "../Deteccion_de_ropa/upload_images_nobg"
    if not os.path.exists(nobg_dir):
        print(f"Error: No se encuentra el directorio {nobg_dir}")
        print("Primero ejecuta el script para remover fondos")
        return
    
    # Listar imágenes sin fondo disponibles
    nobg_files = [f for f in os.listdir(nobg_dir) if f.lower().endswith('.png')]
    
    if not nobg_files:
        print("No se encontraron imágenes sin fondo")
        return
    
    print(f"Encontradas {len(nobg_files)} imágenes sin fondo")
    
    # Leer wardrobe.json original
    wardrobe_path = "../Deteccion_de_ropa/data/wardrobe.json"
    try:
        with open(wardrobe_path, 'r', encoding='utf-8') as f:
            wardrobe_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró {wardrobe_path}")
        return
    
    # Crear nuevo wardrobe con imágenes sin fondo
    updated_wardrobe = []
    
    for item in wardrobe_data:
        original_path = item['img_path']
        filename = original_path.replace('upload_images/', '')
        name, ext = os.path.splitext(filename)
        nobg_filename = f"{name}_nobg.png"
        
        # Verificar si existe la imagen sin fondo
        if nobg_filename in nobg_files:
            updated_item = item.copy()
            updated_item['img_path'] = f"upload_images_nobg/{nobg_filename}"
            updated_item['original_img_path'] = original_path
            updated_wardrobe.append(updated_item)
            print(f"✓ {item['tipo']}: {nobg_filename}")
        else:
            # Mantener imagen original si no hay versión sin fondo
            updated_wardrobe.append(item)
            print(f"- {item['tipo']}: manteniendo original")
    
    # Guardar nuevo wardrobe
    nobg_wardrobe_path = "../Deteccion_de_ropa/data/wardrobe_nobg.json"
    with open(nobg_wardrobe_path, 'w', encoding='utf-8') as f:
        json.dump(updated_wardrobe, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Creado: {nobg_wardrobe_path}")
    
    # Mostrar código para actualizar app.py
    print("\n=== Para completar la actualización ===")
    print("Copia y pega este código en tu app.py:")
    print()
    print("# Agregar nuevo endpoint para imágenes sin fondo")
    print("@app.route('/upload_images_nobg/<path:filename>')")
    print("def nobg_uploaded_file(filename):")
    print("    try:")
    print("        upload_dir = os.path.join('..', 'Deteccion_de_ropa', 'upload_images_nobg')")
    print("        return send_from_directory(upload_dir, filename)")
    print("    except Exception as e:")
    print("        print(f'Error al servir imagen sin fondo: {e}')")
    print("        return 'Error al cargar imagen', 500")
    print()
    print("# Y cambia la ruta del wardrobe.json por:")
    print("with open('../Deteccion_de_ropa/data/wardrobe_nobg.json', 'r', encoding='utf-8') as f:")

if __name__ == "__main__":
    update_app_for_nobg()
