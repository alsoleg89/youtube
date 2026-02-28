import pytest

from app.services.validator import ValidatorService


class TestBananaFormatValidation:
    def test_valid_banana_prompt(self):
        data = {
            "style_summary": "кинематографичный, мрачный",
            "scenes": [
                {
                    "scene_number": 1,
                    "visual_prompt": "A dark room with a single light source",
                    "voiceover_text": "В тёмной комнате раздаётся звук",
                },
                {
                    "scene_number": 2,
                    "visual_prompt": "Wide aerial shot of a city at sunset",
                    "voiceover_text": "Город засыпает",
                },
            ],
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is True

    def test_missing_style_summary(self):
        data = {
            "scenes": [
                {
                    "scene_number": 1,
                    "visual_prompt": "shot",
                    "voiceover_text": "text",
                }
            ],
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is False
        assert "style_summary" in result["details"]

    def test_empty_scenes(self):
        data = {
            "style_summary": "cinematic",
            "scenes": [],
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is False
        assert "scenes" in result["details"]

    def test_missing_scenes_key(self):
        data = {
            "style_summary": "cinematic",
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is False

    def test_scene_missing_keys(self):
        data = {
            "style_summary": "cinematic",
            "scenes": [
                {"scene_number": 1, "visual_prompt": "shot"},
            ],
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is False
        assert "voiceover_text" in result["details"]

    def test_numeric_style_summary_fails(self):
        data = {
            "style_summary": 123,
            "scenes": [
                {
                    "scene_number": 1,
                    "visual_prompt": "shot",
                    "voiceover_text": "text",
                }
            ],
        }
        result = ValidatorService._validate_banana_format(data)
        assert result["passed"] is False
