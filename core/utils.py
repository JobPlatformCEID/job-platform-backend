from PIL import Image as PilImage
from io import BytesIO
from django.core.files.base import ContentFile

# Compress an image at the desired resolution and quality
def compress_image(image_file, max_size=(1920, 1080), quality=85):
    try:
        img = PilImage.open(image_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail(max_size, PilImage.LANCZOS)
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        compressed_bytes = output.read()
        # Check if the compressed file is actually smaller beacause in photos
        # like screenshots, PNGs may be smaller than JPEGs even with compression
        if len(compressed_bytes) < image_file.size:
            return ContentFile(
                compressed_bytes,
                name=image_file.name.rsplit('.', 1)[0] + '.jpg'
            )
        image_file.seek(0)
        return None
    except Exception:
        return None
