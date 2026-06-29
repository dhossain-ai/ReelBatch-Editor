from __future__ import annotations

import unittest

from core.export_worker import BatchExportSummary, format_export_summary


class ExportReportingTests(unittest.TestCase):
    def test_format_export_summary_includes_fallback_count_and_log_path(self):
        summary = BatchExportSummary(
            total_videos=5,
            success_count=4,
            failure_count=1,
            fallback_count=2,
            output_directory="C:/exports",
            log_file_path="C:/logs/export.log",
            successes=(("ok.mp4", "C:/exports/ok.mp4"),),
            failures=(("bad.mp4", "FFmpeg exited with code 1."),),
        )

        message = format_export_summary(summary)

        self.assertIn("Total files: 5", message)
        self.assertIn("Successful files: 4", message)
        self.assertIn("Failed files: 1", message)
        self.assertIn("CPU fallback used: 2", message)
        self.assertIn("Log file: C:/logs/export.log", message)
        self.assertIn("- bad.mp4: FFmpeg exited with code 1.", message)


if __name__ == "__main__":
    unittest.main()
