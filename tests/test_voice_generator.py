"""Tests for the voice generation service."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_engine.models.scripts import Script, ScriptStatus
from content_engine.models.videos import VideoAsset
from content_engine.services.voice.elevenlabs_client import (
    VOICE_PROFILES,
    ElevenLabsClient,
    VoiceConfig,
)
from content_engine.services.voice.voice_generator import VoiceGenerator


def make_script(
    title: str = "The Mirror Watched Back",
    body: str = (
        "I stopped looking in mirrors three days ago. Here's why. "
        "It started with a flicker. Just a shadow in the corner. "
        "I told myself it was nothing. But the next night, it moved closer. "
        "It had a shape now. Shoulders. A head. Right behind me. "
        "I spun around. Nothing. But in the mirror, it was still there. Smiling. "
        "I covered every mirror. Taped newspapers over them. "
        "But this morning, the tape was peeled back on one. "
        "And there were fingerprints on the glass. From the inside. "
        "The worst part? My reflection in my phone screen is not moving when I do."
    ),
) -> Script:
    """Create a mock Script for testing."""
    script = Script(
        id=uuid.uuid4(),
        title=title,
        body=body,
        target_duration="60s",
        hook="I stopped looking in mirrors three days ago.",
        twist="There were fingerprints on the glass. From the inside.",
        ending="My reflection in my phone screen is not moving when I do.",
        niche="creepy_horror",
        status=ScriptStatus.DRAFT.value,
        estimated_quality=8.5,
        generation_params={"tone_tags": ["dread", "paranoia"]},
    )
    return script


@pytest.fixture
def mock_tts() -> MagicMock:
    """Create a mock ElevenLabs client."""
    mock = MagicMock(spec=ElevenLabsClient)

    def fake_generate(text, output_path, config=None):
        # Create a fake file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake audio data" * 100)
        return output_path

    mock.generate_speech.side_effect = fake_generate
    return mock


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    # No existing video for the script
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = MagicMock(return_value=mock_result)
    return session


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temp directory for audio output."""
    return tmp_path / "audio"


class TestVoiceConfig:
    """Tests for voice configuration."""

    def test_default_profiles_exist(self) -> None:
        """Pre-configured voice profiles are available."""
        assert "narrator_deep" in VOICE_PROFILES
        assert "narrator_eerie" in VOICE_PROFILES
        assert "narrator_whisper" in VOICE_PROFILES

    def test_profile_has_required_fields(self) -> None:
        """Each profile has all required configuration."""
        for name, config in VOICE_PROFILES.items():
            assert config.voice_id, f"{name} missing voice_id"
            assert config.voice_name, f"{name} missing voice_name"
            assert config.model_id, f"{name} missing model_id"
            assert 0 <= config.stability <= 1
            assert 0 <= config.similarity_boost <= 1
            assert 0 <= config.style <= 1


class TestElevenLabsClient:
    """Tests for the ElevenLabs client wrapper."""

    @patch("content_engine.services.voice.elevenlabs_client.ElevenLabs")
    def test_generate_speech_writes_file(
        self, mock_elevenlabs_class: MagicMock, tmp_path: Path
    ) -> None:
        """generate_speech writes audio data to the output path."""
        # Mock the TTS response as an iterator of bytes
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter(
            [b"chunk1", b"chunk2", b"chunk3"]
        )
        mock_elevenlabs_class.return_value = mock_client

        client = ElevenLabsClient(api_key="test-key")
        output_path = tmp_path / "test_audio.mp3"

        result = client.generate_speech(
            text="Hello darkness my old friend.",
            output_path=output_path,
        )

        assert result == output_path
        assert output_path.exists()
        assert output_path.read_bytes() == b"chunk1chunk2chunk3"

    @patch("content_engine.services.voice.elevenlabs_client.ElevenLabs")
    def test_generate_speech_creates_parent_dirs(
        self, mock_elevenlabs_class: MagicMock, tmp_path: Path
    ) -> None:
        """generate_speech creates parent directories if needed."""
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([b"data"])
        mock_elevenlabs_class.return_value = mock_client

        client = ElevenLabsClient(api_key="test-key")
        output_path = tmp_path / "deep" / "nested" / "dir" / "audio.mp3"

        client.generate_speech(text="Test", output_path=output_path)

        assert output_path.exists()

    @patch("content_engine.services.voice.elevenlabs_client.ElevenLabs")
    def test_generate_speech_uses_config(
        self, mock_elevenlabs_class: MagicMock, tmp_path: Path
    ) -> None:
        """generate_speech passes voice config to the API."""
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([b"data"])
        mock_elevenlabs_class.return_value = mock_client

        client = ElevenLabsClient(api_key="test-key")
        config = VoiceConfig(
            voice_id="custom_voice_123",
            voice_name="Custom",
            model_id="eleven_multilingual_v2",
            stability=0.6,
            similarity_boost=0.8,
            style=0.4,
        )

        client.generate_speech(
            text="Test text",
            output_path=tmp_path / "test.mp3",
            config=config,
        )

        call_kwargs = mock_client.text_to_speech.convert.call_args[1]
        assert call_kwargs["voice_id"] == "custom_voice_123"
        assert call_kwargs["model_id"] == "eleven_multilingual_v2"
        assert call_kwargs["voice_settings"]["stability"] == 0.6


class TestVoiceGenerator:
    """Tests for the VoiceGenerator service."""

    def test_generate_for_script_creates_asset(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """generate_for_script returns a VideoAsset with correct metadata."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        script = make_script()

        asset = generator.generate_for_script(script)

        assert isinstance(asset, VideoAsset)
        assert asset.asset_type == "voice"
        assert asset.sequence_order == 0
        assert asset.start_time_seconds == 0.0
        assert asset.end_time_seconds is not None
        assert asset.end_time_seconds > 0
        mock_tts.generate_speech.assert_called_once()

    def test_generate_for_script_estimates_duration(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Duration is estimated from word count."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        # 150 words / 2.5 words per second = 60 seconds
        body_150_words = " ".join(["word"] * 150)
        script = make_script(body=body_150_words)

        asset = generator.generate_for_script(script)

        assert asset.end_time_seconds == pytest.approx(60.0)

    def test_generate_for_script_stores_generation_params(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Asset stores voice generation metadata."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        script = make_script()

        asset = generator.generate_for_script(script)

        assert asset.generation_params is not None
        assert "voice_profile" in asset.generation_params
        assert "voice_id" in asset.generation_params
        assert "word_count" in asset.generation_params
        assert "estimated_duration_seconds" in asset.generation_params

    def test_generate_for_script_updates_script_status(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Script status changes to IN_PRODUCTION after audio generation."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        script = make_script()
        assert script.status == ScriptStatus.DRAFT.value

        generator.generate_for_script(script)

        assert script.status == ScriptStatus.IN_PRODUCTION.value

    def test_generate_batch_processes_multiple(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Batch generates audio for multiple scripts."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        scripts = [make_script(title=f"Story {i}") for i in range(3)]

        assets = generator.generate_batch(scripts)

        assert len(assets) == 3
        assert mock_tts.generate_speech.call_count == 3

    def test_generate_batch_continues_on_error(
        self, mock_session: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Batch continues if one generation fails."""
        mock_tts = MagicMock(spec=ElevenLabsClient)
        call_count = [0]

        def side_effect(text, output_path, config=None):
            call_count[0] += 1
            if call_count[0] == 2:
                raise RuntimeError("API error")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"audio data")
            return output_path

        mock_tts.generate_speech.side_effect = side_effect

        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
        )
        scripts = [make_script(title=f"Story {i}") for i in range(3)]

        assets = generator.generate_batch(scripts)

        assert len(assets) == 2  # 1 failed

    def test_voice_profile_selection(
        self, mock_session: MagicMock, mock_tts: MagicMock, tmp_output_dir: Path
    ) -> None:
        """Generator uses the specified voice profile."""
        generator = VoiceGenerator(
            session=mock_session,
            elevenlabs_client=mock_tts,
            output_dir=tmp_output_dir,
            voice_profile="narrator_eerie",
        )

        assert generator.voice_config.voice_name == "Daniel"
        assert generator.voice_config.voice_id == "onwK4e9ZLuTAKqWW03F9"
