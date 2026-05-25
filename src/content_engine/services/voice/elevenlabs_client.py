"""ElevenLabs API client wrapper for text-to-speech generation."""

import logging
from dataclasses import dataclass
from pathlib import Path

from elevenlabs import ElevenLabs
from elevenlabs.types import Voice

from content_engine.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class VoiceConfig:
    """Configuration for voice generation."""

    # Voice selection
    voice_id: str = "pNInz6obpgDQGcFmaJgB"  # "Adam" — deep, narration-quality male voice
    voice_name: str = "Adam"

    # Generation settings
    model_id: str = "eleven_multilingual_v2"  # Best quality model
    stability: float = 0.5  # 0=more variable, 1=more stable
    similarity_boost: float = 0.75  # How closely to match the voice
    style: float = 0.3  # Style exaggeration (0=none, 1=max)
    use_speaker_boost: bool = True

    # Output settings
    output_format: str = "mp3_44100_128"  # mp3 at 44.1kHz 128kbps


# Pre-configured voice profiles for horror content
VOICE_PROFILES: dict[str, VoiceConfig] = {
    "narrator_deep": VoiceConfig(
        voice_id="pNInz6obpgDQGcFmaJgB",
        voice_name="Adam",
        stability=0.4,
        similarity_boost=0.75,
        style=0.2,
    ),
    "narrator_eerie": VoiceConfig(
        voice_id="onwK4e9ZLuTAKqWW03F9",
        voice_name="Daniel",
        stability=0.3,
        similarity_boost=0.8,
        style=0.4,
    ),
    "narrator_whisper": VoiceConfig(
        voice_id="EXAVITQu4vr4xnSDxMaL",
        voice_name="Bella",
        stability=0.35,
        similarity_boost=0.7,
        style=0.5,
    ),
}


class ElevenLabsClient:
    """Wrapper around ElevenLabs API for text-to-speech generation."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self._api_key = api_key or settings.elevenlabs_api_key
        self._client: ElevenLabs | None = None

    @property
    def client(self) -> ElevenLabs:
        """Lazy-initialize ElevenLabs client."""
        if self._client is None:
            self._client = ElevenLabs(api_key=self._api_key)
        return self._client

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        config: VoiceConfig | None = None,
    ) -> Path:
        """Generate speech audio from text.

        Args:
            text: The text to convert to speech
            output_path: Where to save the audio file
            config: Voice configuration (uses default narrator if None)

        Returns:
            Path to the generated audio file
        """
        config = config or VOICE_PROFILES["narrator_deep"]

        logger.info(
            f"Generating speech: {len(text)} chars, voice={config.voice_name}, "
            f"model={config.model_id}"
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate audio
        audio_iterator = self.client.text_to_speech.convert(
            voice_id=config.voice_id,
            text=text,
            model_id=config.model_id,
            output_format=config.output_format,
            voice_settings={
                "stability": config.stability,
                "similarity_boost": config.similarity_boost,
                "style": config.style,
                "use_speaker_boost": config.use_speaker_boost,
            },
        )

        # Write audio to file
        with open(output_path, "wb") as f:
            for chunk in audio_iterator:
                f.write(chunk)

        file_size = output_path.stat().st_size
        logger.info(f"Audio saved: {output_path} ({file_size / 1024:.1f} KB)")

        return output_path

    def list_voices(self) -> list[Voice]:
        """List available voices from the API."""
        response = self.client.voices.get_all()
        return response.voices

    def get_voice_info(self, voice_id: str) -> Voice:
        """Get info about a specific voice."""
        return self.client.voices.get(voice_id)
