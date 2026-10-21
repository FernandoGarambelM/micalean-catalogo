import os, sys, time
import onnxruntime as ort

# Limitar hilos para que no sature la CPU ni congele la laptop
ort.set_default_logger_severity(3)
opts = ort.SessionOptions()
opts.intra_op_num_threads = 2
opts.inter_op_num_threads = 1

from rembg import remove, new_session
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
from scipy import ndimage

os.makedirs('imagenes_tienda', exist_ok=True)

if len(sys.argv) < 3:
    print("Uso: python procesar_uno.py <input_path> <output_filename>")
    sys.exit(1)

src_path = sys.argv[1]
dst_name = sys.argv[2]
out_path = os.path.join('imagenes_tienda', dst_name)

if os.path.exists(out_path):
    print(f"-> {dst_name} ya existe. Omitiendo.")
    sys.exit(0)

print(f"--> Procesando {dst_name} desde {src_path}...")
sys.stdout.flush()
t0 = time.time()

session = new_session('bria-rmbg', session_options=opts)

inp = Image.open(src_path)
if max(inp.size) > 1200:
    inp.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

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

shadow_layer = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
draw = ImageDraw.Draw(shadow_layer)
ground_y = pos_y + new_size[1] - 8
sw = int(new_size[0] * 0.85)
sx1 = (target_w - sw) // 2
sx2 = sx1 + sw
draw.ellipse([sx1, ground_y - 18, sx2, ground_y + 22], fill=(185, 185, 190, 105))
shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(16))

canvas_rgba = canvas.convert('RGBA')
canvas_rgba.alpha_composite(shadow_blurred)
canvas_rgba.paste(resized, (pos_x, pos_y), resized)

canvas_rgba.convert('RGB').save(out_path, quality=95)
print(f"[EXITO] {dst_name} completado en {time.time()-t0:.1f}s")
