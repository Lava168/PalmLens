import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analyzer import DISCLAIMER, analyze_palm_image


class ContractTest(unittest.TestCase):
    def test_disclaimer_is_non_diagnostic(self) -> None:
        self.assertIn("不构成医学诊断", DISCLAIMER)
        self.assertIn("治疗建议", DISCLAIMER)

    def test_report_contains_required_visual_outputs(self) -> None:
        sample_image = Path(__file__).resolve().parents[2] / "frontend" / "public" / "palm-lens-art.png"

        report = analyze_palm_image(sample_image.read_bytes())

        self.assertIn("metrics", report)
        self.assertIn("tips", report)
        self.assertTrue(report["image"]["overlay_image"].startswith("data:image/png;base64,"))
        self.assertTrue(report["image"]["line_enhanced_image"].startswith("data:image/png;base64,"))
        self.assertTrue(report["image"]["red_heatmap_image"].startswith("data:image/png;base64,"))
        self.assertIn("health_suggestions", report)
        self.assertIn(report["health_suggestions"]["risk_level"], {"low", "medium", "high", "uncertain"})
        self.assertGreaterEqual(len(report["health_suggestions"]["possible_health_directions"]), 1)
        self.assertGreaterEqual(len(report["health_suggestions"]["lifestyle_advice"]), 1)
        self.assertIn("不构成医学诊断", report["health_suggestions"]["disclaimer"])
        self.assertIn("palmistry", report)
        self.assertEqual(len(report["palmistry"]["lines"]), 4)
        self.assertIn("仅", report["palmistry"]["disclaimer"])
        self.assertIn("娱乐", report["palmistry"]["disclaimer"])


if __name__ == "__main__":
    unittest.main()
