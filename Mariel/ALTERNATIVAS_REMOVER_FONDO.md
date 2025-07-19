# ALTERNATIVA MANUAL PARA REMOVER FONDOS

Si tienes problemas con rembg, puedes usar herramientas online:

## Opción A: remove.bg (Online)
1. Ve a https://www.remove.bg/
2. Sube cada imagen de tu armario virtual una por una
3. Descarga las imágenes sin fondo
4. Guárdalas en: ../Deteccion_de_ropa/upload_images_nobg/
5. Renómbralas agregando "_nobg" al final del nombre

## Opción B: GIMP (Software gratuito)
1. Descarga GIMP: https://www.gimp.org/
2. Abre cada imagen
3. Usa la herramienta "Selección por color" 
4. Selecciona el fondo
5. Presiona Delete para borrarlo
6. Exporta como PNG con transparencia

## Opción C: Photopea (Online gratuito)
1. Ve a https://www.photopea.com/
2. Abre tu imagen
3. Usa la "Magic Wand Tool" para seleccionar el fondo
4. Presiona Delete
5. Exporta como PNG

## Estructura esperada:
../Deteccion_de_ropa/upload_images_nobg/
├── 1752959699_glasses_6_nobg.png
├── 1752959699_glasses_8_nobg.png
├── 1752959699_jacket_7_nobg.png
├── 1752959699_shirt_blouse_9_nobg.png
├── 1752959782_jacket_3_nobg.png
├── 1752959800_tie_2_nobg.png
├── 1752959800_tie_3_nobg.png
├── 1752959800_jacket_5_nobg.png
└── 1752959843_top_t-shirt_sweatshirt_0_nobg.png

Después ejecuta: python update_app_for_nobg.py
