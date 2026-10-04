from pathlib import Path
from urllib.parse import quote

# Decorative meal photos, not matched to the dish: any image file in the directory can be used.
IMAGE_DIR = Path(__file__).resolve().parent / "images"
IMAGE_URL_PREFIX = "/static/meals"


def meal_image_urls() -> list[str]:
    """Read on every call, so a newly added image is available right away."""
    return [
        f"{IMAGE_URL_PREFIX}/{quote(p.name)}"
        for p in sorted(IMAGE_DIR.iterdir())
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]
