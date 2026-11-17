"""
Utility functions for downloading and storing persona images.
Uses configurable PERSONA_IMAGES_DIR (e.g. volume path) and can return base64 for DB backup.
"""
import aiohttp
import aiofiles
import base64
from pathlib import Path
from typing import Optional, Tuple
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_images_dir() -> Path:
    """Directory for persona images (configurable so it can be a volume path)."""
    return Path(settings.PERSONA_IMAGES_DIR)


async def save_base64_image(image_b64: str, persona_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Decode base64 image data and save under PERSONA_IMAGES_DIR.

    Returns:
        (relative_url_path, base64_data) for serving and DB backup; (None, None) if failed
    """
    images_dir = get_images_dir()
    try:
        # Strip data-URI prefix if present
        raw = image_b64
        if "," in raw and raw.strip().lower().startswith("data:"):
            raw = raw.split(",", 1)[1]
        data = base64.b64decode(raw)

        images_dir.mkdir(parents=True, exist_ok=True)
        filename = f"persona_{persona_id}.png"
        filepath = images_dir / filename

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(data)

        url_path = f"/static/images/personas/{filename}"
        return url_path, base64.b64encode(data).decode("utf-8")
    except Exception as e:
        logger.error(f"Error saving base64 image for persona {persona_id}: {e}", exc_info=True)
        return None, None


async def download_and_save_image(image_url: str, persona_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    Download an image from a URL and save it locally under PERSONA_IMAGES_DIR.

    Args:
        image_url: URL of the image to download
        persona_id: ID of the persona (used for filename)

    Returns:
        (relative_url_path, base64_data) for serving and DB backup; (None, None) if failed
    """
    # GPT Image returns base64; if a caller passes b64 by mistake, save directly
    if image_url and not image_url.startswith(("http://", "https://")):
        return await save_base64_image(image_url, persona_id)

    images_dir = get_images_dir()
    try:
        images_dir.mkdir(parents=True, exist_ok=True)
        filename = f"persona_{persona_id}.png"
        filepath = images_dir / filename

        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download image from {image_url}: HTTP {response.status}")
                    return None, None
                chunks = []
                async for chunk in response.content.iter_chunked(8192):
                    chunks.append(chunk)
                data = b"".join(chunks)

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(data)

        url_path = f"/static/images/personas/{filename}"
        b64 = base64.b64encode(data).decode("utf-8")
        return url_path, b64
    except Exception as e:
        logger.error(f"Error downloading image from {image_url}: {e}", exc_info=True)
        return None, None


def get_image_path(persona_id: int) -> Path:
    """Get the file path for a persona image."""
    return get_images_dir() / f"persona_{persona_id}.png"


def image_exists(persona_id: int) -> bool:
    """Check if an image file exists for a persona."""
    return get_image_path(persona_id).exists()

