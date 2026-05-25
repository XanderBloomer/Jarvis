"""Leonardo AI API client for image generation."""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from content_engine.config.settings import get_settings

logger = logging.getLogger(__name__)

LEONARDO_API_BASE = "https://cloud.leonardo.ai/api/rest/v1"


@dataclass
class ImageStyle:
    """Style configuration for image generation."""

    # Style preset
    name: str = "horror_dark"

    # Core prompt additions for consistent horror aesthetic
    style_prompt: str = (
        "cinematic lighting, dark atmosphere, moody, high contrast, "
        "photorealistic, 8k quality, dramatic shadows, horror aesthetic"
    )

    # Negative prompt to avoid unwanted elements
    negative_prompt: str = (
        "cartoon, anime, bright colors, cheerful, happy, low quality, "
        "blurry, text, watermark, logo, deformed, ugly, disfigured, "
        "extra limbs, extra fingers, poorly drawn"
    )

    # Generation parameters
    width: int = 768  # 9:16 vertical ratio for Shorts
    height: int = 1360
    num_inference_steps: int = 30
    guidance_scale: float = 7.0

    # Model
    model_id: str = "b75b27a3-8c22-4ef4-b59f-ec59010d4fea"  # Leonardo Phoenix


# Pre-configured styles
IMAGE_STYLES: dict[str, ImageStyle] = {
    "horror_dark": ImageStyle(
        name="horror_dark",
        style_prompt=(
            "cinematic lighting, dark atmosphere, moody, high contrast, "
            "photorealistic, 8k quality, dramatic shadows, horror aesthetic, "
            "desaturated colors, eerie fog"
        ),
    ),
    "horror_surreal": ImageStyle(
        name="horror_surreal",
        style_prompt=(
            "surreal horror, dreamlike, uncanny valley, liminal space, "
            "photorealistic, 8k quality, unsettling atmosphere, "
            "distorted perspective, psychological horror"
        ),
    ),
    "horror_found_footage": ImageStyle(
        name="horror_found_footage",
        style_prompt=(
            "found footage aesthetic, grainy, security camera, night vision, "
            "VHS static, low light, realistic, unsettling, surveillance footage"
        ),
        guidance_scale=6.0,
    ),
}


@dataclass
class GeneratedImage:
    """Result of an image generation request."""

    generation_id: str
    image_url: str
    local_path: Path | None = None
    prompt: str = ""
    seed: int | None = None


class LeonardoClient:
    """Client for Leonardo AI image generation API."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self._api_key = api_key or settings.leonardo_api_key
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=LEONARDO_API_BASE,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def generate_image(
        self,
        prompt: str,
        style: ImageStyle | None = None,
        output_dir: Path | None = None,
    ) -> GeneratedImage:
        """Generate an image from a text prompt.

        Args:
            prompt: The scene description to generate
            style: Visual style configuration
            output_dir: Where to download the image (optional)

        Returns:
            GeneratedImage with URL and optional local path
        """
        style = style or IMAGE_STYLES["horror_dark"]

        # Combine scene prompt with style
        full_prompt = f"{prompt}, {style.style_prompt}"

        logger.info(f"Generating image: {prompt[:60]}...")

        # Step 1: Create generation
        payload = {
            "prompt": full_prompt,
            "negative_prompt": style.negative_prompt,
            "modelId": style.model_id,
            "width": style.width,
            "height": style.height,
            "num_images": 1,
            "guidance_scale": style.guidance_scale,
            "num_inference_steps": style.num_inference_steps,
        }

        response = self.client.post("/generations", json=payload)
        response.raise_for_status()
        data = response.json()

        generation_id = data["sdGenerationJob"]["generationId"]
        logger.debug(f"Generation started: {generation_id}")

        # Step 2: Poll for completion
        image_data = self._poll_generation(generation_id)

        result = GeneratedImage(
            generation_id=generation_id,
            image_url=image_data["url"],
            prompt=prompt,
            seed=image_data.get("seed"),
        )

        # Step 3: Download if output_dir specified
        if output_dir:
            result.local_path = self._download_image(
                url=result.image_url,
                output_dir=output_dir,
                filename=f"{generation_id}.jpg",
            )

        logger.info(f"Image generated: {generation_id}")
        return result

    def _poll_generation(
        self,
        generation_id: str,
        max_attempts: int = 30,
        poll_interval: float = 2.0,
    ) -> dict:
        """Poll until generation is complete.

        Args:
            generation_id: The generation job ID
            max_attempts: Maximum polling attempts
            poll_interval: Seconds between polls

        Returns:
            Image data dict with 'url' key

        Raises:
            TimeoutError: If generation doesn't complete in time
            RuntimeError: If generation fails
        """
        for attempt in range(max_attempts):
            response = self.client.get(f"/generations/{generation_id}")
            response.raise_for_status()
            data = response.json()

            status = data["generations_by_pk"]["status"]

            if status == "COMPLETE":
                images = data["generations_by_pk"]["generated_images"]
                if images:
                    return images[0]
                raise RuntimeError(f"Generation {generation_id} completed but no images returned")

            if status == "FAILED":
                raise RuntimeError(f"Generation {generation_id} failed")

            logger.debug(f"Polling generation {generation_id}: {status} (attempt {attempt + 1})")
            time.sleep(poll_interval)

        raise TimeoutError(
            f"Generation {generation_id} did not complete after {max_attempts} attempts"
        )

    def _download_image(self, url: str, output_dir: Path, filename: str) -> Path:
        """Download an image from URL to local filesystem."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()

        output_path.write_bytes(response.content)
        logger.debug(f"Downloaded image: {output_path} ({len(response.content) / 1024:.1f} KB)")

        return output_path
