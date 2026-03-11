"""图文与长音频相关单元测试。"""

from pathlib import Path
from unittest.mock import patch
from unittest import TestCase

from src.models import DouyinAweme
from src.server import _download_output_dir, _merge_segment_transcripts, _should_chunk_audio


class MediaFeatureTest(TestCase):
    def test_aweme_extracts_images_from_image_post_info(self):
        aweme = DouyinAweme.from_dict({
            "aweme_id": "123",
            "desc": "图文作品",
            "author": {"nickname": "作者"},
            "statistics": {},
            "image_post_info": {
                "images": [
                    {"display_image": {"url_list": ["https://img.example.com/1.jpg"]}},
                    {"display_image": {"url_list": ["https://img.example.com/2.jpg"]}},
                ]
            },
        })

        self.assertEqual(aweme.image_count, 2)
        self.assertEqual(
            aweme.image_urls,
            [
                "https://img.example.com/1.jpg",
                "https://img.example.com/2.jpg",
            ],
        )
        self.assertEqual(aweme.cover_url, "https://img.example.com/1.jpg")

    def test_should_chunk_audio_when_duration_or_size_exceeds_threshold(self):
        self.assertTrue(_should_chunk_audio(601, 10))
        self.assertTrue(_should_chunk_audio(120, 46))
        self.assertFalse(_should_chunk_audio(300, 12))

    def test_merge_segment_transcripts_keeps_single_segment_plain(self):
        merged = _merge_segment_transcripts([
            {"start_seconds": 0, "text": "单段文本"},
        ])
        self.assertEqual(merged, "单段文本")

    def test_merge_segment_transcripts_adds_timestamps_for_multiple_segments(self):
        merged = _merge_segment_transcripts([
            {"start_seconds": 0, "text": "第一段"},
            {"start_seconds": 75, "text": "第二段"},
        ])
        self.assertIn("[00:00:00] 第一段", merged)
        self.assertIn("[00:01:15] 第二段", merged)

    def test_download_output_dir_prefers_explicit_then_env_default(self):
        with patch("src.server.DOWNLOAD_DIR", "/tmp/from-env"):
            explicit = _download_output_dir("/tmp/custom-save")
            defaulted = _download_output_dir("")

        self.assertEqual(explicit, Path("/tmp/custom-save"))
        self.assertEqual(defaulted, Path("/tmp/from-env"))
