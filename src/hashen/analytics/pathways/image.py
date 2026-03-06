"""Image pathway: grayscale pixel intensity tiles → values for TSEC (Component 130a)."""

from __future__ import annotations


def image_to_values(image_bytes: bytes, tile_size: int = 64) -> list[float]:
    """
    Convert image bytes to normalized grayscale pixel values.

    For TSEC: the cascade will window these and compute tile-level H1.
    If PIL/Pillow available: decode image, convert to grayscale, normalize.
    Fallback: treat raw bytes as pixel intensities (for raw/BMP-like data).
    """
    try:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        pixels = list(img.getdata())
        return [p / 255.0 for p in pixels]
    except ImportError:
        return [b / 255.0 for b in image_bytes]
    except Exception:
        return [b / 255.0 for b in image_bytes]
