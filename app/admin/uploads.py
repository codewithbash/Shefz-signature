import os
import uuid
from flask import current_app
from PIL import Image

ALLOWED = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def save_product_image(file_storage):
    """Validate the real image content, resize, save with a safe random name.
    Returns the path under static/ or raises ValueError with a friendly message."""
    try:
        img = Image.open(file_storage.stream)
        img.verify()                       # is it really an image?
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        fmt = img.format
    except Exception:
        raise ValueError(f"{file_storage.filename}: this is not a valid image.")
    if fmt not in ALLOWED:
        raise ValueError(f"{file_storage.filename}: use JPG, PNG or WEBP photos.")
    img.thumbnail((1600, 1600))
    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    folder = os.path.join(current_app.root_path, "static", "uploads", "products")
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ALLOWED[fmt]}"
    img.save(os.path.join(folder, name), format=fmt, quality=88)
    return f"uploads/products/{name}"


def delete_image_file(relative_path):
    full = os.path.join(current_app.root_path, "static", relative_path)
    if os.path.isfile(full):
        os.remove(full)
