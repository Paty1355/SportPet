"""Decode supported uploads and send a single normalised JPEG to the vision model."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener(thumbnails=False)

SUPPORTED_FORMATS = ("JPEG", "PNG", "WEBP", "HEIF", "AVIF", "BMP", "TIFF", "GIF")
MAX_IMAGE_PIXELS = 60_000_000
MAX_IMAGE_SIDE = 2048


class ImagePreparationError(ValueError):
    pass


class ImageTooLarge(ImagePreparationError):
    pass


def prepare_image(data: bytes) -> bytes:
    """Use decoded content, not the filename/MIME; preserve orientation and flatten transparency."""
    if not data:
        raise ImagePreparationError("Provide a non-empty image")
    try:
        with Image.open(BytesIO(data), formats=SUPPORTED_FORMATS) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise ImageTooLarge("Image exceeds the 60 megapixel limit")
            # Pillow opens GIF/TIFF at their first frame/page and HEIF at its primary image.
            source.load()
            oriented = ImageOps.exif_transpose(source)
            try:
                oriented.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
                if "A" in oriented.getbands() or "transparency" in oriented.info:
                    with oriented.convert("RGBA") as rgba:
                        rgb = Image.new("RGB", rgba.size, "white")
                        with rgba.getchannel("A") as alpha:
                            rgb.paste(rgba, mask=alpha)
                else:
                    rgb = oriented.convert("RGB")
                try:
                    rgb.info.clear()
                    output = BytesIO()
                    rgb.save(output, format="JPEG", quality=90, exif=b"", icc_profile=None)
                    return output.getvalue()
                finally:
                    rgb.close()
            finally:
                oriented.close()
    except ImagePreparationError:
        raise
    except Image.DecompressionBombError as exc:
        raise ImageTooLarge("Image exceeds the 60 megapixel limit") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        raise ImagePreparationError(
            "Cannot decode image. Use a valid JPEG, PNG, WebP, HEIC/HEIF, AVIF, BMP, TIFF or GIF file."
        ) from exc
