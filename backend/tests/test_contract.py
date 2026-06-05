import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analyzer import DISCLAIMER, analyze_palm_image
from app.deepseek_enhancer import enhance_with_deepseek


class ContractTest(unittest.TestCase):
    def test_disclaimer_is_non_diagnostic(self) -> None:
        self.assertIn("不构成医学诊断", DISCLAIMER)
        self.assertIn("治疗建议", DISCLAIMER)

    def test_report_contains_required_visual_outputs(self) -> None:
        sample_image = Path(__file__).resolve().parents[2] / "frontend" / "public" / "palm-lens-art.png"

        original_enabled = os.environ.get("DEEPSEEK_ENABLED")
        os.environ["DEEPSEEK_ENABLED"] = "false"
        try:
            report = analyze_palm_image(sample_image.read_bytes())
        finally:
            if original_enabled is None:
                os.environ.pop("DEEPSEEK_ENABLED", None)
            else:
                os.environ["DEEPSEEK_ENABLED"] = original_enabled

        self.assertIn("metrics", report)
        self.assertIn("tips", report)
        self.assertTrue(report["image"]["overlay_image"].startswith("data:image/png;base64,"))
        self.assertTrue(report["image"]["line_enhanced_image"].startswith("data:image/png;base64,"))
        self.assertTrue(report["image"]["red_heatmap_image"].startswith("data:image/png;base64,"))
        self.assertIn("health_suggestions", report)
        self.assertIn(report["health_suggestions"]["risk_level"], {"low", "medium", "high", "uncertain"})
        self.assertGreaterEqual(len(report["health_suggestions"]["possible_health_directions"]), 1)
        self.assertGreaterEqual(len(report["health_suggestions"]["lifestyle_advice"]), 1)
        self.assertGreaterEqual(len(report["health_suggestions"]["quality_notes"]), 1)
        self.assertEqual(len(report["health_suggestions"]["color_explanation"]), 3)
        self.assertIn("summary", report["health_suggestions"])
        self.assertIn("redness_explanation", report["health_suggestions"])
        self.assertIn("texture_explanation", report["health_suggestions"])
        self.assertGreaterEqual(len(report["health_suggestions"]["recheck_plan"]), 1)
        self.assertGreaterEqual(len(report["health_suggestions"]["consult_doctor_if"]), 1)
        self.assertIn("不构成医学诊断", report["health_suggestions"]["disclaimer"])
        self.assertIn("palmistry", report)
        self.assertEqual(len(report["palmistry"]["lines"]), 4)
        self.assertIn("archetype", report["palmistry"])
        self.assertGreaterEqual(len(report["palmistry"]["keywords"]), 1)
        self.assertGreaterEqual(len(report["palmistry"]["overall_advice"]), 1)
        self.assertGreaterEqual(len(report["palmistry"]["relationship_advice"]), 1)
        self.assertGreaterEqual(len(report["palmistry"]["work_rhythm_advice"]), 1)
        self.assertGreaterEqual(len(report["palmistry"]["daily_rhythm_advice"]), 1)
        self.assertGreaterEqual(len(report["palmistry"]["photo_tips"]), 1)
        self.assertIn("仅供娱乐", report["palmistry"]["share_copy"])
        for line in report["palmistry"]["lines"]:
            self.assertIn("visual_basis", line)
            self.assertGreaterEqual(len(line["entertainment_advice"]), 1)
        self.assertIn("仅", report["palmistry"]["disclaimer"])
        self.assertIn("娱乐", report["palmistry"]["disclaimer"])
        self.assertIn("skin_screening", report)
        self.assertIn(report["skin_screening"]["attention_level"], {"低关注", "轻度关注", "需要关注"})
        self.assertGreaterEqual(len(report["skin_screening"]["visible_findings"]), 3)
        self.assertGreaterEqual(len(report["skin_screening"]["possible_visual_patterns"]), 3)
        self.assertGreaterEqual(len(report["skin_screening"]["hygiene_guidance"]), 3)
        self.assertGreaterEqual(len(report["skin_screening"]["seek_care_if"]), 3)
        self.assertGreaterEqual(len(report["skin_screening"]["photo_limitations"]), 1)
        self.assertIn("不能识别", report["skin_screening"]["disclaimer"])
        self.assertIn("传染病", report["skin_screening"]["disclaimer"])
        self.assertIn("ai_enhancement", report)
        self.assertIn(report["ai_enhancement"]["status"], {"generated", "not_configured", "disabled", "error", "safety_fallback"})
        self.assertIn(report["ai_enhancement"]["source"], {"ai_api", "local_template"})
        self.assertGreaterEqual(len(report["ai_enhancement"]["health_insights"]), 3)
        self.assertGreaterEqual(len(report["ai_enhancement"]["palmistry_story"]), 3)
        self.assertGreaterEqual(len(report["ai_enhancement"]["next_steps"]), 3)
        self.assertIn("不构成医学诊断", report["ai_enhancement"]["safety_note"])

    def test_deepseek_safety_fallback_blocks_diagnostic_claims(self) -> None:
        sample_image = Path(__file__).resolve().parents[2] / "frontend" / "public" / "palm-lens-art.png"
        original_enabled = os.environ.get("DEEPSEEK_ENABLED")
        os.environ["DEEPSEEK_ENABLED"] = "false"
        try:
            report = analyze_palm_image(sample_image.read_bytes())
        finally:
            if original_enabled is None:
                os.environ.pop("DEEPSEEK_ENABLED", None)
            else:
                os.environ["DEEPSEEK_ENABLED"] = original_enabled

        original_call = enhance_with_deepseek.__globals__["_call_deepseek"]
        original_key = os.environ.get("DEEPSEEK_API_KEY")
        original_enabled = os.environ.get("DEEPSEEK_ENABLED")

        def unsafe_call(*_args, **_kwargs):
            return {
                "summary": "诊断为某种疾病",
                "health_insights": ["确诊，需要治疗方案。"],
                "palmistry_story": ["仅供娱乐。"],
                "next_steps": ["咨询医生。"],
            }

        try:
            enhance_with_deepseek.__globals__["_call_deepseek"] = unsafe_call
            os.environ["DEEPSEEK_API_KEY"] = "test-key"
            os.environ["DEEPSEEK_ENABLED"] = "true"
            result = enhance_with_deepseek(report)
        finally:
            enhance_with_deepseek.__globals__["_call_deepseek"] = original_call
            if original_key is None:
                os.environ.pop("DEEPSEEK_API_KEY", None)
            else:
                os.environ["DEEPSEEK_API_KEY"] = original_key
            if original_enabled is None:
                os.environ.pop("DEEPSEEK_ENABLED", None)
            else:
                os.environ["DEEPSEEK_ENABLED"] = original_enabled

        self.assertEqual(result["status"], "safety_fallback")
        self.assertEqual(result["source"], "local_template")
        self.assertNotIn("诊断为", result["summary"])


if __name__ == "__main__":
    unittest.main()
