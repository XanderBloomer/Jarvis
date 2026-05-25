"""Tests for the visual generation service."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from content_engine.models.scripts import Script, ScriptStatus
from content_engine.models.videos import Video, VideoAsset, VideoStatus
from content_engine.services.visuals.leonardo_client import (
    IMAGE_STYLES,
    GeneratedImage,
    LeonardoClient,
)
from content_engine.services.visuals.visual_generator import VisualGenerator


def make_script_with_cues() -> Script:
    """Create a mock Script with visual cues."""
    return Script(
        id=uuid.uuid4(),
        title="The Mirror Watched Back",
        body="I stopped looking in mirrors three days ago...",
        target_duration="60s",
        hook="I stopped looking in mirrors three days ago.",
        twist="Fingerprints on the glass. From the inside.",
        ending="My reflection isn't moving when I do.",
        niche="creepy_horror",
        status=ScriptStatus.IN_PRODUCTION.value,
        estimated_quality=8.5,
        generation_params={
            "tone_tags": ["dread", "paranoia"],
            "visual_cues": [
                "Dark bathroom, flickering light, mirror with shadowy figure",
                "Close-up of mirror with shape forming behind reflection",
                "Hands taping newspaper over mirrors frantically",
                "Peeled tape with fingerprints visible on glass surface",
                "Phone screen showing still reflection while hand moves",
            ],
        },
    )


def make_video(script_id: uuid.UUID) -> Video:
    """Create a mock Video record."""
    return Video(
        id=uuid.uuid4(),
        script_id=script_id,
        title="The Mirror Watched Back",
        status=VideoStatus.GENERATING_VISUALS.value,
        duration_seconds=60.0,
        resolution="1080x1920",
    )


@pytest.fixture
def mock_leonardo() -> MagicMock:
    """Create a mock Leonardo client."""
    mock = MagicMock(spec=LeonardoClient)

    def fake_generate(prompt, style=None, output_dir=None):
        gen_id = f"gen_{uuid.uuid4().hex[:8]}"
        local_path = None
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            local_path = output_dir / f"{gen_id}.jpg"
            local_path.write_bytes(b"fake image data")
        return GeneratedImage(
            generation_id=gen_id,
            image_url=f"https://cdn.leonardo.ai/{gen_id}.jpg",
            local_path=local_path,
            prompt=prompt,
            seed=12345,
        )

    mock.generate_image.side_effect = fake_generate
    return mock


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    return session


class TestImageStyles:
    """Tests for image style configuration."""

    def test_default_styles_exist(self) -> None:
        """Pre-configured styles are available."""
        assert "horror_dark" in IMAGE_STYLES
        assert "horror_surreal" in IMAGE_STYLES
        assert "horror_found_footage" in IMAGE_STYLES

    def test_styles_have_vertical_dimensions(self) -> None:
        """All styles use vertical (9:16) dimensions for Shorts."""
        for name, style in IMAGE_STYLES.items():
            assert style.height > style.width, f"{name} should be vertical"

    def test_styles_have_negative_prompts(self) -> None:
        """All styles have negative prompts to avoid bad outputs."""
        for name, style in IMAGE_STYLES.items():
            assert style.negative_prompt, f"{name} missing negative_prompt"
            assert "cartoon" in style.negative_prompt.lower()


class TestLeonardoClient:
    """Tests for the Leonardo AI client."""

    @patch("content_engine.services.visuals.leonardo_client.httpx.Client")
    def test_generate_image_calls_api(self, mock_httpx: MagicMock) -> None:
        """generate_image makes correct API calls."""
        # Mock the POST response (create generation)
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {
            "sdGenerationJob": {"generationId": "gen_123"}
        }
        mock_post_response.raise_for_status = MagicMock()

        # Mock the GET response (poll for completion)
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "generations_by_pk": {
                "status": "COMPLETE",
                "generated_images": [
                    {"url": "https://cdn.leonardo.ai/gen_123.jpg", "seed": 42}
                ],
            }
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_post_response
        mock_client_instance.get.return_value = mock_get_response
        mock_httpx.return_value = mock_client_instance

        client = LeonardoClient(api_key="test-key")
        result = client.generate_image(prompt="Dark bathroom with mirror")

        assert isinstance(result, GeneratedImage)
        assert result.generation_id == "gen_123"
        assert result.image_url == "https://cdn.leonardo.ai/gen_123.jpg"
        assert result.seed == 42
        mock_client_instance.post.assert_called_once()

    @patch("content_engine.services.visuals.leonardo_client.httpx.Client")
    def test_generate_image_includes_style_in_prompt(
        self, mock_httpx: MagicMock
    ) -> None:
        """Style prompt is appended to the scene description."""
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {
            "sdGenerationJob": {"generationId": "gen_456"}
        }
        mock_post_response.raise_for_status = MagicMock()

        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "generations_by_pk": {
                "status": "COMPLETE",
                "generated_images": [{"url": "https://example.com/img.jpg"}],
            }
        }
        mock_get_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_post_response
        mock_client_instance.get.return_value = mock_get_response
        mock_httpx.return_value = mock_client_instance

        client = LeonardoClient(api_key="test-key")
        style = IMAGE_STYLES["horror_dark"]
        client.generate_image(prompt="A dark hallway", style=style)

        # Check that the POST payload includes style in prompt
        call_kwargs = mock_client_instance.post.call_args
        payload = call_kwargs[1]["json"]
        assert "A dark hallway" in payload["prompt"]
        assert "cinematic" in payload["prompt"]
        assert payload["negative_prompt"] == style.negative_prompt


class TestVisualGenerator:
    """Tests for the VisualGenerator service."""

    def test_generate_for_script_creates_assets(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """generate_for_script creates a VideoAsset per visual cue."""
        script = make_script_with_cues()
        video = make_video(script.id)

        # Mock session to return the video
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = video
        mock_session.execute.return_value = mock_result

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        assets = generator.generate_for_script(script)

        assert len(assets) == 5  # 5 visual cues
        assert all(isinstance(a, VideoAsset) for a in assets)
        assert all(a.asset_type == "image" for a in assets)
        assert mock_leonardo.generate_image.call_count == 5

    def test_generate_for_script_sets_timing(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """Each image asset has correct start/end times."""
        script = make_script_with_cues()
        video = make_video(script.id)
        video.duration_seconds = 60.0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = video
        mock_session.execute.return_value = mock_result

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        assets = generator.generate_for_script(script)

        # 5 scenes over 60 seconds = 12 seconds each
        assert assets[0].start_time_seconds == pytest.approx(0.0)
        assert assets[0].end_time_seconds == pytest.approx(12.0)
        assert assets[1].start_time_seconds == pytest.approx(12.0)
        assert assets[1].end_time_seconds == pytest.approx(24.0)
        assert assets[4].end_time_seconds == pytest.approx(60.0)

    def test_generate_for_script_stores_generation_params(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """Each asset stores generation metadata."""
        script = make_script_with_cues()
        video = make_video(script.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = video
        mock_session.execute.return_value = mock_result

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        assets = generator.generate_for_script(script)

        for asset in assets:
            assert asset.generation_params is not None
            assert "prompt" in asset.generation_params
            assert "style" in asset.generation_params
            assert "generation_id" in asset.generation_params
            assert "image_url" in asset.generation_params

    def test_generate_for_script_handles_no_cues(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """Returns empty list if script has no visual cues."""
        script = make_script_with_cues()
        script.generation_params = {"tone_tags": ["dread"]}  # No visual_cues

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        assets = generator.generate_for_script(script)

        assert assets == []
        mock_leonardo.generate_image.assert_not_called()

    def test_generate_for_script_continues_on_error(
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Continues generating if one image fails."""
        script = make_script_with_cues()
        video = make_video(script.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = video
        mock_session.execute.return_value = mock_result

        mock_leonardo = MagicMock(spec=LeonardoClient)
        call_count = [0]

        def side_effect(prompt, style=None, output_dir=None):
            call_count[0] += 1
            if call_count[0] == 3:
                raise RuntimeError("Generation failed")
            return GeneratedImage(
                generation_id=f"gen_{call_count[0]}",
                image_url=f"https://cdn.leonardo.ai/gen_{call_count[0]}.jpg",
                prompt=prompt,
            )

        mock_leonardo.generate_image.side_effect = side_effect

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        assets = generator.generate_for_script(script)

        # 5 cues, 1 failed = 4 assets
        assert len(assets) == 4

    def test_generate_for_script_updates_video_status(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """Video status updates to ASSEMBLING after images are generated."""
        script = make_script_with_cues()
        video = make_video(script.id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = video
        mock_session.execute.return_value = mock_result

        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path / "images",
        )

        generator.generate_for_script(script)

        assert video.status == VideoStatus.ASSEMBLING.value

    def test_style_selection(
        self, mock_session: MagicMock, mock_leonardo: MagicMock, tmp_path: Path
    ) -> None:
        """Generator uses the specified style."""
        generator = VisualGenerator(
            session=mock_session,
            leonardo_client=mock_leonardo,
            output_dir=tmp_path,
            style="horror_surreal",
        )

        assert generator.image_style.name == "horror_surreal"
        assert "surreal" in generator.image_style.style_prompt
