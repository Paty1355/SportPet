from io import BytesIO

import pytest
from PIL import Image

from app.agents.vision import images
from app.agents.vision.agent import get_vision_agent
from app.agents.vision.images import ImagePreparationError, ImageTooLarge, prepare_image
from app.core.config import settings
from app.main import app

FORMATS = [
    ("JPEG", "jpg", "image/jpeg"),
    ("JPEG", "jpeg", "image/jpeg"),
    ("PNG", "png", "image/png"),
    ("WEBP", "webp", "image/webp"),
    ("HEIF", "heic", "image/heic"),
    ("HEIF", "heif", "image/heif"),
    ("AVIF", "avif", "image/avif"),
    ("BMP", "bmp", "image/bmp"),
    ("TIFF", "tif", "image/tiff"),
    ("TIFF", "tiff", "image/tiff"),
    ("GIF", "gif", "image/gif"),
]


def encoded(format, **options):
    output = BytesIO()
    with Image.new("RGB", (32, 24), "red") as image:
        image.save(output, format=format, **options)
    return output.getvalue()


@pytest.mark.parametrize(("format", "extension", "mime"), FORMATS)
def test_real_formats_decode_and_become_jpeg(format, extension, mime):
    prepared = prepare_image(encoded(format))
    with Image.open(BytesIO(prepared)) as image:
        image.load()
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (32, 24)
        assert image.getpixel((16, 12))[0] > 240


@pytest.mark.parametrize(("format", "extension", "mime"), FORMATS)
def test_endpoint_accepts_formats_and_passes_jpeg_to_agent(client, format, extension, mime):
    class CapturingAgent:
        calls = []

        async def run(self, image):
            self.calls.append(image)
            from fastapi import HTTPException

            raise HTTPException(409, "Reached agent")

    agent = CapturingAgent()
    app.dependency_overrides[get_vision_agent] = lambda: agent
    response = client.post(
        "/api/v1/agents/vision/analyze", files={"file": (f"machine.{extension}", encoded(format), mime)}
    )
    assert response.status_code == 409
    assert len(agent.calls) == 1
    with Image.open(BytesIO(agent.calls[0])) as image:
        assert image.format == "JPEG"
        assert image.size == (32, 24)


def test_actual_bytes_take_priority_over_filename_and_mime(client):
    class CapturingAgent:
        async def run(self, image):
            with Image.open(BytesIO(image)) as parsed:
                assert parsed.format == "JPEG"
            from fastapi import HTTPException

            raise HTTPException(409, "Reached agent")

    app.dependency_overrides[get_vision_agent] = CapturingAgent
    response = client.post(
        "/api/v1/agents/vision/analyze", files={"file": ("wrong.txt", encoded("HEIF"), "application/octet-stream")}
    )
    assert response.status_code == 409


@pytest.mark.parametrize("format", ["GIF", "TIFF", "WEBP", "AVIF"])
def test_first_frame_or_page_is_selected(format):
    output = BytesIO()
    with Image.new("RGB", (32, 24), "red") as first, Image.new("RGB", (32, 24), "blue") as second:
        first.save(output, format=format, save_all=True, append_images=[second], duration=100)
    with Image.open(BytesIO(prepare_image(output.getvalue()))) as image:
        red, green, blue = image.getpixel((16, 12))
        assert red > 240 and green < 20 and blue < 20


def test_heif_primary_image_is_selected():
    output = BytesIO()
    with Image.new("RGB", (32, 24), "red") as first, Image.new("RGB", (32, 24), "blue") as second:
        first.save(output, format="HEIF", save_all=True, append_images=[second], primary_index=1)
    with Image.open(BytesIO(prepare_image(output.getvalue()))) as image:
        red, green, blue = image.getpixel((16, 12))
        assert blue > 240 and red < 20 and green < 20


def test_exif_rotation_is_applied_and_metadata_removed():
    exif = Image.Exif()
    exif[274] = 6
    exif[315] = "test author"
    prepared = prepare_image(encoded("JPEG", exif=exif))
    with Image.open(BytesIO(prepared)) as image:
        assert image.size == (24, 32)
        assert not image.getexif()
        assert "icc_profile" not in image.info


@pytest.mark.parametrize("mode", ["RGBA", "LA", "P"])
def test_transparent_background_becomes_white(mode):
    output = BytesIO()
    with Image.new("RGBA", (8, 8), (255, 0, 0, 0)) as image:
        converted = image.convert(mode)
        converted.save(output, format="PNG")
        converted.close()
    with Image.open(BytesIO(prepare_image(output.getvalue()))) as image:
        assert image.getpixel((4, 4)) == (255, 255, 255)


def test_cmyk_jpeg_becomes_rgb():
    output = BytesIO()
    with Image.new("CMYK", (8, 8), (0, 255, 255, 0)) as image:
        image.save(output, format="JPEG")
    with Image.open(BytesIO(prepare_image(output.getvalue()))) as image:
        assert image.mode == "RGB"
        assert image.getpixel((4, 4))[0] > 240


def test_large_image_is_resized_with_proportions(monkeypatch):
    monkeypatch.setattr(images, "MAX_IMAGE_SIDE", 16)
    with Image.open(BytesIO(prepare_image(encoded("PNG")))) as image:
        assert image.size == (16, 12)


@pytest.mark.parametrize("data", [b"", b"not an image", b"\x89PNG example", b"<svg></svg>"])
def test_invalid_and_unsupported_images_are_rejected(data):
    with pytest.raises(ImagePreparationError):
        prepare_image(data)


def test_corrupted_image_is_rejected_even_with_valid_header():
    with pytest.raises(ImagePreparationError):
        prepare_image(encoded("JPEG")[:-30])


def test_pixel_limit_is_checked_before_loading(monkeypatch):
    monkeypatch.setattr(images, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(ImageTooLarge):
        prepare_image(encoded("PNG"))


@pytest.mark.parametrize(("data", "status"), [(b"", 422), (b"fake image", 422)])
def test_invalid_upload_never_reaches_agent(client, data, status):
    class UnusedAgent:
        async def run(self, image):
            pytest.fail("Invalid upload reached agent")

    app.dependency_overrides[get_vision_agent] = UnusedAgent
    response = client.post("/api/v1/agents/vision/analyze", files={"file": ("machine.jpg", data, "image/jpeg")})
    assert response.status_code == status


def test_oversized_upload_never_reaches_agent(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)

    class UnusedAgent:
        async def run(self, image):
            pytest.fail("Oversized upload reached agent")

    app.dependency_overrides[get_vision_agent] = UnusedAgent
    response = client.post(
        "/api/v1/agents/vision/analyze", files={"file": ("machine.jpg", b"x" * (1024 * 1024 + 1), "image/jpeg")}
    )
    assert response.status_code == 413


def test_oversized_dimensions_return_413(client, monkeypatch):
    monkeypatch.setattr(images, "MAX_IMAGE_PIXELS", 100)

    class UnusedAgent:
        async def run(self, image):
            pytest.fail("Oversized dimensions reached agent")

    app.dependency_overrides[get_vision_agent] = UnusedAgent
    response = client.post(
        "/api/v1/agents/vision/analyze", files={"file": ("machine.png", encoded("PNG"), "image/png")}
    )
    assert response.status_code == 413
