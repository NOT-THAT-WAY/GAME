import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.backend.tutorial_pipeline import prepare_tutorial, scan_tutorials


class TutorialPipelineTest(unittest.TestCase):
    def test_video_evidence_and_transcript_are_prepared(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "knowledge" / "tutorials" / "camera-basics-test"
            folder.mkdir(parents=True)
            source = folder / "source.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                "testsrc2=size=320x180:rate=12:duration=2", "-f", "lavfi", "-i",
                "sine=frequency=440:duration=2", "-shortest", "-pix_fmt", "yuv420p", str(source),
            ], check=True)
            (folder / "transcript-source.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,500\nCréer une caméra.\n", encoding="utf-8"
            )
            (folder / "manifest.json").write_text(json.dumps({
                "schema_version": 1,
                "id": "tutorial-test",
                "title": "Camera basics",
                "status": "queued",
                "source_name": source.name,
                "created": "2026-07-19T00:00:00+02:00",
                "updated": "2026-07-19T00:00:00+02:00",
                "analysis_status": "not_started",
            }), encoding="utf-8")

            result = prepare_tutorial(root, folder, frame_interval=1, scene_threshold=0.3)
            self.assertEqual(result["status"], "ready_for_ai")
            self.assertTrue((folder / "audio.wav").exists())
            self.assertTrue((folder / "contact-sheet.jpg").exists())
            self.assertTrue((folder / "transcript.json").exists())
            self.assertTrue((folder / "ANALYSIS_BRIEF.md").exists())
            self.assertGreater(result["technical"]["regular_frame_count"], 0)
            indexed = scan_tutorials(root)
            self.assertEqual(indexed[0]["id"], "tutorial-test")
            self.assertIn("Créer une caméra", indexed[0]["transcript_excerpt"])


if __name__ == "__main__":
    unittest.main()
