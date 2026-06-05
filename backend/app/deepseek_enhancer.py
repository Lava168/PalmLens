from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

PROVIDER = "AI 增强"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_API_URL = "https://api.deepseek.com/chat/completions"
AI_SAFETY_NOTE = (
    "AI 增强内容仅改写结构化视觉指标，属于科普说明与娱乐文案，"
    "不构成医学诊断、疾病预测、治疗建议、用药建议、性格判断或人生决策建议。"
)
UNSAFE_PHRASES = (
    "诊断为",
    "确诊",
    "治疗方案",
    "用药建议",
    "处方",
    "患有",
    "必然",
    "一定是",
    "疾病预测",
    "命运预测",
    "性格判断",
)


def enhance_with_deepseek(report: dict[str, Any]) -> dict[str, Any]:
    model = os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    local = _local_enhancement(report, model=model)

    enabled = os.getenv("DEEPSEEK_ENABLED", "true").strip().lower()
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if enabled in {"0", "false", "no", "off"}:
        return {
            **local,
            "status": "disabled",
            "status_label": "AI 增强已关闭",
            "source": "local_template",
        }

    if not api_key:
        return {
            **local,
            "status": "not_configured",
            "status_label": "AI 增强未配置",
            "source": "local_template",
        }

    try:
        generated = _call_deepseek(report=report, api_key=api_key, model=model)
    except (OSError, TimeoutError, ValueError, KeyError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return {
            **local,
            "status": "error",
            "status_label": "AI 增强调用失败",
            "source": "local_template",
            "error_message": str(exc)[:180],
        }

    if _contains_unsafe_claim(generated):
        return {
            **local,
            "status": "safety_fallback",
            "status_label": "安全回退",
            "source": "local_template",
            "error_message": "AI 输出包含不适合本项目边界的表述，已使用本地安全增强文本。",
        }

    return {
        **generated,
        "provider": PROVIDER,
        "status": "generated",
        "status_label": "AI 已增强",
        "source": "ai_api",
        "model": model,
        "title": "AI 增强报告",
        "safety_note": AI_SAFETY_NOTE,
        "error_message": None,
    }


def _call_deepseek(report: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    timeout = float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "18"))
    api_url = os.getenv("DEEPSEEK_API_URL", DEFAULT_API_URL).strip() or DEFAULT_API_URL
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 PalmLens 的报告文案增强模块。你只能根据用户提供的 OpenCV/MediaPipe "
                    "结构化视觉指标生成中文报告。健康和皮肤部分只能写视觉特征分析、健康科普提示、"
                    "复拍建议、卫生提醒和咨询医生边界；禁止诊断、识别具体皮肤病/传染病、疾病预测、"
                    "治疗方案、用药建议。手相部分只能写娱乐化掌纹卡片；禁止命运预测、性格判断和现实决策建议。"
                    "必须返回 JSON，不要 Markdown，不要多余文本。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于以下 PalmLens 结构化报告生成增强文案。JSON 格式必须为："
                    "{\"summary\": string, \"health_insights\": string[], "
                    "\"palmistry_story\": string[], \"next_steps\": string[]}。"
                    "summary 不超过 90 个中文字符；health_insights 3 到 5 条；"
                    "palmistry_story 3 到 4 条；next_steps 3 到 4 条。"
                    f"\n\n输入 JSON：{json.dumps(_prompt_payload(report), ensure_ascii=False)}"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0.45,
        "max_tokens": 950,
    }

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")

    data = json.loads(raw)
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return _normalize_generated(parsed)


def _prompt_payload(report: dict[str, Any]) -> dict[str, Any]:
    health = report["health_suggestions"]
    palmistry = report["palmistry"]
    skin = report["skin_screening"]
    return {
        "metrics": report["metrics"],
        "health": {
            "risk_level": health["risk_level"],
            "risk_label": health["risk_label"],
            "summary": health["summary"],
            "scores": health["scores"],
            "quality_notes": health["quality_notes"],
            "redness_explanation": health["redness_explanation"],
            "texture_explanation": health["texture_explanation"],
            "possible_direction_titles": [item["title"] for item in health["possible_health_directions"]],
            "medical_boundary": health["disclaimer"],
        },
        "palmistry": {
            "summary": palmistry["summary"],
            "archetype": palmistry["archetype"],
            "keywords": palmistry["keywords"],
            "lines": [
                {
                    "name": item["name"],
                    "score": item["score"],
                    "theme": item["theme"],
                    "detail": item["detail"],
                    "visual_basis": item["visual_basis"],
                }
                for item in palmistry["lines"]
            ],
            "disclaimer": palmistry["disclaimer"],
        },
        "skin_screening": {
            "attention_level": skin["attention_level"],
            "summary": skin["summary"],
            "scores": skin["scores"],
            "visible_findings": skin["visible_findings"],
            "possible_visual_patterns": [
                {"name": item["name"], "basis": item["basis"]} for item in skin["possible_visual_patterns"]
            ],
            "disclaimer": skin["disclaimer"],
        },
    }


def _normalize_generated(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": _short_text(parsed.get("summary"), "AI 已根据视觉指标生成增强说明。", max_len=140),
        "health_insights": _string_list(parsed.get("health_insights"), min_items=3, max_items=5),
        "palmistry_story": _string_list(parsed.get("palmistry_story"), min_items=3, max_items=4),
        "next_steps": _string_list(parsed.get("next_steps"), min_items=3, max_items=4),
    }


def _local_enhancement(report: dict[str, Any], model: str) -> dict[str, Any]:
    health = report["health_suggestions"]
    palmistry = report["palmistry"]
    skin = report["skin_screening"]
    scores = health["scores"]
    line_names = "、".join(item["name"] for item in palmistry["lines"])
    return {
        "provider": PROVIDER,
        "status": "not_configured",
        "status_label": "AI 增强未配置",
        "source": "local_template",
        "model": model,
        "title": "AI 增强报告",
        "summary": (
            f"本地增强预览：当前为{health['risk_label']}，掌纹娱乐设定为"
            f"「{palmistry['archetype']}」。配置后端 AI Key 后会生成更自然的个性化文案。"
        ),
        "health_insights": [
            f"掌色分数：偏红 {scores['redness']:.0f}、偏黄 {scores['yellow']:.0f}、偏淡 {scores['pale']:.0f}，仅代表照片中的颜色倾向。",
            health["redness_explanation"]["detail"],
            skin["summary"],
            health["texture_explanation"]["detail"],
            "如果现实中持续不适，应以专业医生意见为准，而不是依据照片或 AI 文案判断。",
        ],
        "palmistry_story": [
            f"趣味手相关键词：{' / '.join(palmistry['keywords'][:4])}。",
            f"本次四条线卡片包含 {line_names}，只用于互动娱乐展示。",
            palmistry["share_copy"],
        ],
        "next_steps": [
            "在自然光下复拍一张掌心平展照片，对比两次视觉特征是否稳定。",
            "优先参考掌纹增强图和红色热力图，它们比纯文字更容易解释分数来源。",
            "若要启用实时 AI 增强，请在后端环境变量配置 AI API Key。",
        ],
        "safety_note": AI_SAFETY_NOTE,
        "error_message": None,
    }


def _string_list(value: Any, min_items: int, max_items: int) -> list[str]:
    if not isinstance(value, list):
        value = []
    items = [_short_text(item, "", max_len=180) for item in value if isinstance(item, str)]
    items = [item for item in items if item]
    while len(items) < min_items:
        items.append("本条为视觉报告增强说明，不用于医学诊断或现实决策。")
    return items[:max_items]


def _short_text(value: Any, fallback: str, max_len: int) -> str:
    if not isinstance(value, str):
        return fallback
    text = " ".join(value.split())
    return text[:max_len] if text else fallback


def _contains_unsafe_claim(generated: dict[str, Any]) -> bool:
    text = json.dumps(generated, ensure_ascii=False)
    return any(phrase in text for phrase in UNSAFE_PHRASES)
