"""
Utility functions for downloading and storing persona images.
"""
import aiohttp
import aiofiles
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Directory to store persona images
IMAGES_DIR = Path("/app/static/images/personas")
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


async def download_and_save_image(image_url: str, persona_id: int) -> Optional[str]:
    """
    Download an image from a URL and save it locally.
    
    Args:
        image_url: URL of the image to download
        persona_id: ID of the persona (used for filename)
    
    Returns:
        Relative path to the saved image, or None if download failed
    """
    try:
        # Create images directory if it doesn't exist
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"persona_{persona_id}.png"
        filepath = IMAGES_DIR / filename
        
        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    async with aiofiles.open(filepath, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    # Return relative path for serving
                    return f"/static/images/personas/{filename}"
                else:
                    logger.error(f"Failed to download image from {image_url}: HTTP {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error downloading image from {image_url}: {e}", exc_info=True)
        return None


def get_image_path(persona_id: int) -> Path:
    """Get the file path for a persona image."""
    filename = f"persona_{persona_id}.png"
    return IMAGES_DIR / filename


def image_exists(persona_id: int) -> bool:
    """Check if an image exists for a persona."""
    return get_image_path(persona_id).exists()

