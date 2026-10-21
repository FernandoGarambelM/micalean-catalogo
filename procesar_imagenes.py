import os, time, sys, gc
from rembg import remove, new_session
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
from scipy import ndimage

os.makedirs('imagenes_tienda', exist_ok=True)

print("Iniciando procesador de imágenes de catálogo...")
sys.stdout.flush()

# Sesión ONNX reutilizable
session = new_session('bria-rmbg')

def process_flyer(input_path, output_name, shadow_width_ratio=0.85):
    out_path = os.path.join('imagenes_tienda', output_name)
    if os.path.exists(out_path):
        print(f"-> Ya existe {output_name}, omitiendo...")
        sys.stdout.flush()
        return

    t0 = time.time()
    inp = Image.open(input_path)
    # Limitar resolución de entrada para optimizar RAM
    if max(inp.size) > 1400:
        inp.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    
    cutout = remove(inp, session=session)
    
    alpha = np.array(cutout.split()[3])
    labeled, num_features = ndimage.label(alpha > 50)
    if num_features > 0:
        sizes = ndimage.sum(alpha > 50, labeled, range(num_features + 1))
        max_label = np.argmax(sizes[1:]) + 1
        clean_mask = (labeled == max_label).astype(np.uint8) * 255
        cutout.putalpha(Image.fromarray(clean_mask))
    
    bbox = cutout.getbbox()
    if bbox:
        cropped = cutout.crop(bbox)
    else:
        cropped = cutout

    target_w, target_h = 1200, 1200
    canvas = Image.new('RGB', (target_w, target_h), (255, 255, 255))
    
    scale = min(target_w * 0.82 / cropped.width, target_h * 0.75 / cropped.height)
    new_size = (int(cropped.width * scale), int(cropped.height * scale))
    resized = cropped.resize(new_size, Image.Resampling.LANCZOS)
    
    pos_x = (target_w - new_size[0]) // 2
    pos_y = (target_h - new_size[1]) // 2 + 25
    
    # Sombra de piso
    shadow_layer = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)
    ground_y = pos_y + new_size[1] - 8
    sw = int(new_size[0] * shadow_width_ratio)
    sx1 = (target_w - sw) // 2
    sx2 = sx1 + sw
    draw.ellipse([sx1, ground_y - 18, sx2, ground_y + 22], fill=(185, 185, 190, 105))
    shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(16))
    
    canvas_rgba = canvas.convert('RGBA')
    canvas_rgba.alpha_composite(shadow_blurred)
    canvas_rgba.paste(resized, (pos_x, pos_y), resized)
    
    canvas_rgba.convert('RGB').save(out_path, quality=95)
    print(f"[OK] {output_name} procesado en {time.time()-t0:.1f}s")
    sys.stdout.flush()
    
    # Liberar memoria explícitamente
    del inp, cutout, alpha, labeled, clean_mask, canvas, canvas_rgba, shadow_layer
    gc.collect()

# Lista de afiches para recortar y limpiar
flyers = [
    ('productos/WhatsApp Image 2026-10-14 at 10.30.29 AM.jpeg', 'twiscar-morado.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.29 AM (1).jpeg', 'twiscar-rojo.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.29 AM (2).jpeg', 'twiscar-azul-rojo.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.30 AM.jpeg', 'twiscar-azul-blanco.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.30 AM (1).jpeg', 'twiscar-rosado.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.36 AM (3).jpeg', 'andador-mono-ck803b.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.32 AM (2).jpeg', 'buguie-con-sombrilla.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.32 AM (1).jpeg', 'buguie-correpasillo.jpg')
]

for src, dst in flyers:
    process_flyer(src, dst)

# Fotos de Andador Perrito (ya limpias sobre tela blanca de estudio)
perritos = [
    ('productos/WhatsApp Image 2026-10-14 at 10.30.33 AM.jpeg', 'andador-perrito-celeste.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.33 AM (1).jpeg', 'andador-perrito-azul.jpg'),
    ('productos/WhatsApp Image 2026-10-14 at 10.30.33 AM (2).jpeg', 'andador-perrito-rosado.jpg')
]

for src, dst in perritos:
    out_path = os.path.join('imagenes_tienda', dst)
    if not os.path.exists(out_path):
        im = Image.open(src)
        scale = min(1200 / im.width, 1200 / im.height)
        new_w, new_h = int(im.width * scale), int(im.height * scale)
        resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (1200, 1200), (255, 255, 255))
        canvas.paste(resized, ((1200 - new_w) // 2, (1200 - new_h) // 2))
        canvas.save(out_path, quality=95)
        print(f"[OK] Encuadrado {dst} en 1200x1200px")
        sys.stdout.flush()

print("\n¡PROCESO COMPLETADO! Todas las imágenes listas en 'imagenes_tienda/'.")
