"""Validate decoded images and store small metadata-free previews in the database."""
import base64
import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError


def read_image(upload, max_bytes=10 * 1024 * 1024):
    if not upload or not hasattr(upload, 'size'):
        raise ValidationError({'image': 'Choose a JPEG, PNG or WebP image.'})
    if upload.size > max_bytes:
        raise ValidationError({'image': f'Image must be smaller than {max_bytes // (1024 * 1024)} MB.'})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as source:
                if source.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValidationError({'image': 'Supported formats: JPEG, PNG and WebP.'})
                if min(source.size) < 64 or source.width * source.height > 12_000_000:
                    raise ValidationError({'image': 'Use an image at least 64 pixels wide and tall, up to 12 megapixels.'})
                source.load()
                return ImageOps.exif_transpose(source).convert('RGB')
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError({'image': 'This image is unreadable. Choose a different JPEG, PNG or WebP file.'})
    finally:
        if hasattr(upload, 'seek'):
            upload.seek(0)


def preview_data_uri(image, size=640):
    thumbnail = image.copy()
    thumbnail.thumbnail((size, size))
    output = BytesIO()
    thumbnail.save(output, format='JPEG', quality=78, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode('ascii')
