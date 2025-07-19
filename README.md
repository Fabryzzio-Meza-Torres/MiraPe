# Proyecto: Sistema de Detección de Ropa y Red Social de Outfits

Este proyecto es una aplicación web desarrollada en Flask que simula un **espejo inteligente** con reconocimiento de prendas y colores mediante visión por computadora. Además, permite a los usuarios construir un **armario virtual** y una **red social de outfits**, donde pueden compartir looks, ver publicaciones, y matchear con otras personas en base al estilo y color de ropa que usan.

---

## Objetivos Generales

- Permitir a los usuarios detectar ropa y color dominante a través de una cámara o archivo.
- Construir un armario virtual con las prendas detectadas.
- Publicar y visualizar outfits en una red social tipo TikTok o Tinder.
- Ofrecer una experiencia de interacción entre usuarios basada en estilo visual.

---

## Tecnologías Utilizadas

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Procesamiento de Imagen:** OpenCV, NumPy, scikit-learn
- **Modelo de Detección:** `valentinafeve/yolos-fashionpedia` (HuggingFace Transformers)
- **Base de datos:** JSON (`wardrobe.json`, `posts.json`) o SQLite
- **Framework de estilo:** Bootstrap o TailwindCSS (según módulo)

---

## Estructura del Proyecto



## Funcionalidades clave

### Detección de ropa y armado del armario

- Detección de ropa usando webcam o archivo cargado.
- Procesamiento con OpenCV (sin uso de PIL).
- Uso del modelo `valentinafeve/yolos-fashionpedia` con Transformers.
- Extracción de color dominante con K-means (`sklearn.cluster`).
- Recorte automático de prendas detectadas y guardado.
- Almacenamiento en `wardrobe.json`.
- Confirmaciones de acción: cámara encendida, foto tomada, resultados generados.

### Armario virtual + prueba de ropa

- Vista de galería con todas las prendas detectadas (desde JSON).
- Visualización del usuario con imagen subida.
- Superposición de prendas sobre el cuerpo del usuario usando `<canvas>`.
- Funcionalidad interactiva sin recarga de página.
- Servidor sirve imágenes desde `upload_images`.

### Integrante 4 (Brigitte): Red social tipo TikTok y Tinder

- Perfil de usuario con galería de outfits publicados.
- Feed tipo TikTok con scroll vertical de publicaciones de todos los usuarios.
- Publicación de posts con imagen + descripción (formulario simple).
- Funcionalidad de likes y comentarios (simulados con JS).
- Módulo tipo Tinder donde se comparan colores de ropa para hacer match entre personas.

---

## Endpoints principales

### app.py
- `POST /upload`: Carga y procesamiento de imagen desde webcam (base64) o archivo (`multipart/form-data`).
- `GET /upload_images/<filename>`: Servir imágenes guardadas.
- Procesamiento robusto con OpenCV y detección de ropa.

### red_social/routes.py
- `/perfil`: Vista del perfil de usuario.
- `/feed`: Vista general de publicaciones.
- `/match`: Vista tipo Tinder.

### virtual_tryon/index.html
- Carga dinámica de prendas desde `/data`.
- Superposición de ropa sobre imagen subida por usuario.

---

## Seguridad y buenas prácticas

- Subida de archivos con nombres seguros (`secure_filename`).
- Rutas de guardado claras y controladas (`upload_images/`).
- Separación de responsabilidades por módulo.
- Asegurar rutas antes de desplegar.

---

## Conexiones entre módulos

- Los recortes generados por `app.py` son usados por:
  - El armario virtual para visualización.
  - El módulo de red social para publicaciones.
  - El módulo de match para comparar estilos.
- Las imágenes se centralizan en la carpeta `upload_images/`.
- Los datos persistentes están en formato `.json` accesible para todos los módulos.

---

## Notas

- No se han incluido archivos de instrucciones adicionales ni scripts externos.
- Todo el código debe mantenerse limpio, sin comentarios, sin emojis y sin archivos de configuración bash.



