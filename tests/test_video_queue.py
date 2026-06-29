from __future__ import annotations

import unittest

from app.video_queue import format_queue_item_label
from core.video_probe import VideoInfo


class VideoQueueLabelTests(unittest.TestCase):
    def test_queue_label_includes_filename_metadata_and_status(self):
        video_info = VideoInfo(
            file_path="C:/clips/demo.mp4",
            file_name="demo.mp4",
            width=1080,
            height=1920,
            fps=30.0,
            frame_count=300,
            duration_seconds=10.0,
        )

        label = format_queue_item_label(video_info, "Done")

        self.assertIn("demo.mp4", label)
        self.assertIn("1080x1920", label)
        self.assertIn("0:10", label)
        self.assertIn("Done", label)


if __name__ == "__main__":
    unittest.main()
