from __future__ import annotations

import base64
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import cv2
import numpy as np

DISCLAIMER = (
    "PalmLens 仅分析照片中的视觉特征并给出健康科普提示，"
    "不构成医学诊断、疾病筛查、治疗建议或用药建议。"
)
PALMISTRY_DISCLAIMER = "手相解读模块仅基于掌纹视觉特征生成娱乐化文本，不具有预测、判断性格或指导人生决策的作用。"


class AnalyzerError(ValueError):
    """Raised when an uploaded image cannot be analyzed."""


def analyze_palm_image(image_bytes: bytes) -> dict[str, Any]:
    image = _decode_image(image_bytes)
    image = _resize_for_analysis(image)

    detection = _detect_palm_region(image)
    mask = detection["mask"]

    if _mask_area_ratio(mask) < 0.015:
        raise AnalyzerError("未检测到足够清晰的手掌区域，请换一张掌心朝向镜头的照片。")

    color = _analyze_color(image, mask)
    redness = _analyze_redness(image, mask)
    lines = _analyze_lines(image, mask)
    overlay = _build_overlay(image, mask, detection.get("hand_mask"), redness["mask"], lines["edge_mask"])
    line_enhanced = _build_line_enhanced_image(image, mask, lines["enhanced_gray"], lines["edge_mask"])
    red_heatmap = _build_red_heatmap_image(image, mask, redness["strength_map"], redness["mask"])

    observations, tips, flags = _build_report(
        detection=detection,
        color=color,
        redness=redness,
        lines=lines,
        image_shape=image.shape,
    )
    health_suggestions = _generate_health_suggestions(
        color_result=_health_color_scores(color=color, redness=redness),
        texture_result=_health_texture_scores(lines=lines, palm_ratio=_mask_area_ratio(mask)),
    )
    palmistry = _build_palmistry_reading(color=color, redness=redness, lines=lines, palm_ratio=_mask_area_ratio(mask))

    return {
        "image": {
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "palm_detected": True,
            "detection_method": detection["method"],
            "confidence": round(float(detection["confidence"]), 3),
            "overlay_image": overlay,
            "line_enhanced_image": line_enhanced,
            "red_heatmap_image": red_heatmap,
        },
        "metrics": {
            "palm_area_ratio": round(_mask_area_ratio(mask), 4),
            "color": {
                "tone": color["tone"],
                "mean_hue": round(color["mean_hue"], 2),
                "mean_saturation": round(color["mean_saturation"], 2),
                "mean_brightness": round(color["mean_brightness"], 2),
                "redness_index": round(color["redness_index"], 2),
            },
            "redness": {
                "attention_level": redness["attention_level"],
                "area_ratio": round(redness["area_ratio"], 4),
                "largest_patch_ratio": round(redness["largest_patch_ratio"], 4),
                "patch_count": int(redness["patch_count"]),
            },
            "lines": {
                "clarity_level": lines["clarity_level"],
                "clarity_score": round(lines["clarity_score"], 1),
                "edge_density": round(lines["edge_density"], 4),
                "contrast_score": round(lines["contrast_score"], 1),
            },
        },
        "observations": observations,
        "tips": tips,
        "health_suggestions": health_suggestions,
        "palmistry": palmistry,
        "flags": flags,
        "disclaimer": DISCLAIMER,
    }


def _decode_image(image_bytes: bytes) -> np.ndarray:
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise AnalyzerError("无法读取图片内容，请确认文件未损坏。")
    return image


def _resize_for_analysis(image: np.ndarray, max_side: int = 1280) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_side:
        return image

    scale = max_side / float(longest)
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def _detect_palm_region(image: np.ndarray) -> dict[str, Any]:
    mediapipe_detection = _detect_with_mediapipe(image)
    if mediapipe_detection is not None:
        return mediapipe_detection
    return _detect_with_skin_segmentation(image)


def _detect_with_mediapipe(image: np.ndarray) -> dict[str, Any] | None:
    try:
        os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
        import mediapipe as mp
    except ImportError:
        return None

    height, width = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    try:
        with mp.solutions.hands.Hands(
            static_image_mode=True,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=0.45,
        ) as hands:
            result = hands.process(rgb)
    except RuntimeError:
        return None

    if not result.multi_hand_landmarks:
        return None

    landmarks = result.multi_hand_landmarks[0].landmark
    points = np.array(
        [
            [
                int(np.clip(point.x, 0, 1) * width),
                int(np.clip(point.y, 0, 1) * height),
            ]
            for point in landmarks
        ],
        dtype=np.int32,
    )

    palm_indices = [0, 1, 2, 5, 9, 13, 17]
    palm_points = points[palm_indices]

    hand_mask = np.zeros((height, width), dtype=np.uint8)
    palm_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillConvexPoly(hand_mask, cv2.convexHull(points), 255)
    cv2.fillConvexPoly(palm_mask, cv2.convexHull(palm_points), 255)

    palm_mask = _expand_mask(palm_mask, image.shape, factor=0.018)
    hand_mask = _expand_mask(hand_mask, image.shape, factor=0.012)

    confidence = 0.82
    if result.multi_handedness:
        classification = result.multi_handedness[0].classification[0]
        confidence = float(classification.score)

    return {
        "method": "MediaPipe Hands",
        "confidence": confidence,
        "mask": palm_mask,
        "hand_mask": hand_mask,
        "landmarks": points.tolist(),
    }


def _detect_with_skin_segmentation(image: np.ndarray) -> dict[str, Any]:
    height, width = image.shape[:2]
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    skin_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 180, 135]))
    skin_hsv = cv2.inRange(hsv, np.array([0, 18, 45]), np.array([35, 210, 255]))
    mask = cv2.bitwise_or(skin_ycrcb, skin_hsv)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise AnalyzerError("未检测到明显的手掌区域，请使用自然光下的掌心照片。")

    largest = max(contours, key=cv2.contourArea)
    contour_area = cv2.contourArea(largest)
    image_area = height * width
    if contour_area / image_area < 0.015:
        raise AnalyzerError("手掌区域过小，请让手掌占据画面更多空间。")

    hand_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(hand_mask, [largest], -1, 255, thickness=cv2.FILLED)

    x, y, w, h = cv2.boundingRect(largest)
    center_mask = np.zeros_like(hand_mask)
    center_rect = (
        max(0, x + int(w * 0.16)),
        max(0, y + int(h * 0.18)),
        min(width, x + int(w * 0.84)),
        min(height, y + int(h * 0.82)),
    )
    cv2.rectangle(
        center_mask,
        (center_rect[0], center_rect[1]),
        (center_rect[2], center_rect[3]),
        255,
        thickness=cv2.FILLED,
    )
    palm_mask = cv2.bitwise_and(hand_mask, center_mask)
    palm_mask = _expand_mask(palm_mask, image.shape, factor=0.006)

    hull_area = cv2.contourArea(cv2.convexHull(largest))
    solidity = contour_area / hull_area if hull_area else 0
    confidence = float(np.clip(0.34 + _mask_area_ratio(hand_mask) * 2.2 + solidity * 0.22, 0.34, 0.72))

    return {
        "method": "OpenCV skin segmentation",
        "confidence": confidence,
        "mask": palm_mask,
        "hand_mask": hand_mask,
        "landmarks": [],
    }


def _expand_mask(mask: np.ndarray, image_shape: tuple[int, ...], factor: float) -> np.ndarray:
    kernel_size = max(3, int(max(image_shape[:2]) * factor))
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)


def _analyze_color(image: np.ndarray, mask: np.ndarray) -> dict[str, float | str]:
    mask_bool = mask > 0
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    palm_hsv = hsv[mask_bool]
    palm_rgb = rgb[mask_bool].astype(np.float32)

    if palm_hsv.size == 0:
        raise AnalyzerError("手掌区域像素不足，无法完成分析。")

    mean_hue = float(np.mean(palm_hsv[:, 0]) * 2)
    mean_saturation = float(np.mean(palm_hsv[:, 1]) / 255)
    mean_brightness = float(np.mean(palm_hsv[:, 2]) / 255)

    red_channel = palm_rgb[:, 0]
    green_channel = palm_rgb[:, 1]
    blue_channel = palm_rgb[:, 2]
    red_dominance = red_channel - ((green_channel + blue_channel) * 0.5)
    redness_index = float(np.clip(np.mean(np.maximum(red_dominance, 0)) / 72, 0, 1))

    tone = "相对均衡"
    if mean_brightness < 0.34:
        tone = "光线偏暗"
    elif redness_index > 0.3 and mean_saturation > 0.22:
        tone = "偏红"
    elif mean_saturation < 0.18 and mean_brightness > 0.68:
        tone = "偏淡"
    elif np.mean(red_channel) > np.mean(blue_channel) + 26 and np.mean(green_channel) > np.mean(blue_channel) + 8:
        tone = "偏暖黄"

    return {
        "tone": tone,
        "mean_hue": mean_hue,
        "mean_saturation": mean_saturation,
        "mean_brightness": mean_brightness,
        "redness_index": redness_index,
    }


def _analyze_redness(image: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
    mask_bool = mask > 0

    hue = hsv[:, :, 0]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    red_dominance = rgb[:, :, 0] - ((rgb[:, :, 1] + rgb[:, :, 2]) * 0.5)

    hue_red = ((hue <= 18) | (hue >= 165)).astype(np.float32)
    redness_strength = np.clip((red_dominance - 10) / 58, 0, 1)
    saturation_strength = np.clip((saturation.astype(np.float32) - 42) / 150, 0, 1)
    strength_map = (redness_strength * saturation_strength * hue_red * mask_bool * 255).astype(np.uint8)
    strength_map = cv2.GaussianBlur(
        strength_map,
        (0, 0),
        sigmaX=max(3, min(image.shape[:2]) * 0.01),
    )
    strength_map = cv2.bitwise_and(strength_map, mask)

    red_pixels = (
        mask_bool
        & ((hue <= 12) | (hue >= 170))
        & (saturation > 55)
        & (value > 55)
        & (red_dominance > 18)
    )

    red_mask = red_pixels.astype(np.uint8) * 255
    red_mask = cv2.morphologyEx(
        red_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
        iterations=1,
    )

    palm_area = max(1, int(np.count_nonzero(mask)))
    red_area = int(np.count_nonzero(red_mask))
    area_ratio = red_area / palm_area

    components = cv2.connectedComponentsWithStats(red_mask, connectivity=8)
    patch_count = 0
    largest_patch = 0
    min_patch_area = max(24, int(palm_area * 0.004))
    for area in components[2][1:, cv2.CC_STAT_AREA]:
        if int(area) >= min_patch_area:
            patch_count += 1
            largest_patch = max(largest_patch, int(area))

    largest_patch_ratio = largest_patch / palm_area

    if area_ratio >= 0.12 or largest_patch_ratio >= 0.065:
        attention_level = "明显"
    elif area_ratio >= 0.045 or largest_patch_ratio >= 0.025:
        attention_level = "轻度"
    else:
        attention_level = "低"

    return {
        "mask": red_mask,
        "strength_map": strength_map,
        "area_ratio": area_ratio,
        "largest_patch_ratio": largest_patch_ratio,
        "patch_count": patch_count,
        "attention_level": attention_level,
    }


def _analyze_lines(image: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    eroded_mask = cv2.erode(
        mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
        iterations=1,
    )
    if np.count_nonzero(eroded_mask) < 200:
        eroded_mask = mask

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    edges = cv2.Canny(blurred, 42, 118)
    edges = cv2.bitwise_and(edges, eroded_mask)

    palm_area = max(1, int(np.count_nonzero(eroded_mask)))
    edge_density = float(np.count_nonzero(edges) / palm_area)
    local_pixels = enhanced[eroded_mask > 0]
    contrast_score = float(np.clip(np.std(local_pixels) / 56 * 100, 0, 100))

    density_score = float(np.clip(edge_density / 0.095 * 100, 0, 100))
    clarity_score = float(np.clip(density_score * 0.58 + contrast_score * 0.42, 0, 100))

    if clarity_score >= 66:
        clarity_level = "清晰"
    elif clarity_score >= 40:
        clarity_level = "中等"
    else:
        clarity_level = "较弱"

    return {
        "enhanced_gray": enhanced,
        "edge_mask": edges,
        "edge_density": edge_density,
        "contrast_score": contrast_score,
        "clarity_score": clarity_score,
        "clarity_level": clarity_level,
    }


def _build_overlay(
    image: np.ndarray,
    palm_mask: np.ndarray,
    hand_mask: np.ndarray | None,
    red_mask: np.ndarray,
    edge_mask: np.ndarray,
) -> str:
    overlay = image.copy()
    layer = np.zeros_like(image)

    layer[palm_mask > 0] = (80, 185, 160)
    layer[edge_mask > 0] = (255, 232, 112)
    layer[red_mask > 0] = (54, 78, 255)

    overlay = cv2.addWeighted(overlay, 0.78, layer, 0.34, 0)

    contour_source = hand_mask if hand_mask is not None and np.count_nonzero(hand_mask) else palm_mask
    contours, _ = cv2.findContours(contour_source, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (66, 214, 180), 3, lineType=cv2.LINE_AA)

    palm_contours, _ = cv2.findContours(palm_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, palm_contours, -1, (248, 224, 102), 2, lineType=cv2.LINE_AA)

    return _encode_png_data_url(overlay, "无法生成可视化叠加图。")


def _build_line_enhanced_image(
    image: np.ndarray,
    palm_mask: np.ndarray,
    enhanced_gray: np.ndarray,
    edge_mask: np.ndarray,
) -> str:
    enhanced_bgr = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)
    outside = cv2.GaussianBlur(image, (0, 0), sigmaX=7)
    palm_visual = cv2.addWeighted(image, 0.2, enhanced_bgr, 0.8, 0)

    visual = outside.copy()
    visual[palm_mask > 0] = palm_visual[palm_mask > 0]

    line_layer = np.zeros_like(image)
    line_layer[edge_mask > 0] = (74, 214, 246)
    visual = cv2.addWeighted(visual, 0.86, line_layer, 0.62, 0)

    palm_contours, _ = cv2.findContours(palm_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(visual, palm_contours, -1, (92, 184, 152), 2, lineType=cv2.LINE_AA)

    return _encode_png_data_url(visual, "无法生成掌纹增强图。")


def _build_red_heatmap_image(
    image: np.ndarray,
    palm_mask: np.ndarray,
    strength_map: np.ndarray,
    red_mask: np.ndarray,
) -> str:
    gray_bgr = cv2.cvtColor(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    visual = cv2.addWeighted(image, 0.38, gray_bgr, 0.62, 0)

    heat_input = cv2.GaussianBlur(
        strength_map,
        (0, 0),
        sigmaX=max(4, min(image.shape[:2]) * 0.014),
    )
    heat_input = cv2.bitwise_and(heat_input, palm_mask)

    if int(np.max(heat_input)) > 0:
        normalized = cv2.normalize(heat_input, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    else:
        normalized = np.zeros_like(heat_input, dtype=np.uint8)

    color_map = getattr(cv2, "COLORMAP_TURBO", cv2.COLORMAP_JET)
    heat_color = cv2.applyColorMap(normalized, color_map)
    alpha = (normalized.astype(np.float32) / 255 * 0.78)
    alpha[red_mask > 0] = np.maximum(alpha[red_mask > 0], 0.55)
    alpha[palm_mask == 0] = 0
    alpha_3 = np.dstack([alpha, alpha, alpha])
    visual = (visual.astype(np.float32) * (1 - alpha_3) + heat_color.astype(np.float32) * alpha_3).astype(np.uint8)

    palm_contours, _ = cv2.findContours(palm_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(visual, palm_contours, -1, (118, 198, 166), 2, lineType=cv2.LINE_AA)

    red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(visual, red_contours, -1, (54, 78, 255), 2, lineType=cv2.LINE_AA)

    return _encode_png_data_url(visual, "无法生成红色热力图。")


def _encode_png_data_url(image: np.ndarray, error_message: str) -> str:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise AnalyzerError(error_message)

    data = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _build_report(
    detection: dict[str, Any],
    color: dict[str, Any],
    redness: dict[str, Any],
    lines: dict[str, Any],
    image_shape: tuple[int, ...],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    height, width = image_shape[:2]
    palm_ratio = _mask_area_ratio(detection["mask"])
    flags: list[str] = []

    observations = [
        {
            "title": "手掌区域",
            "value": f"{palm_ratio * 100:.1f}% 画面占比",
            "detail": f"使用 {detection['method']} 定位掌心区域，置信参考值 {detection['confidence']:.2f}。",
        },
        {
            "title": "掌心色彩",
            "value": str(color["tone"]),
            "detail": f"平均亮度 {color['mean_brightness']:.2f}，平均饱和度 {color['mean_saturation']:.2f}。",
        },
        {
            "title": "局部发红",
            "value": str(redness["attention_level"]),
            "detail": f"红色高饱和区域约占掌心 {redness['area_ratio'] * 100:.1f}%，可见斑块 {redness['patch_count']} 处。",
        },
        {
            "title": "掌纹清晰度",
            "value": str(lines["clarity_level"]),
            "detail": f"边缘密度 {lines['edge_density']:.3f}，局部对比评分 {lines['contrast_score']:.0f}/100。",
        },
        {
            "title": "图像质量",
            "value": f"{width} x {height}",
            "detail": "结果会受到光照、白平衡、皮肤表面水分、按压和相机锐化影响。",
        },
    ]

    tips = [
        {
            "title": "掌纹说明",
            "detail": "掌纹清晰度主要反映照片锐度、皮肤纹理与光照对比，不用于判断疾病。",
        },
        {
            "title": "颜色说明",
            "detail": "掌心颜色会受环境光、手部温度、按压、运动后状态和相机白平衡影响。",
        },
    ]

    if redness["attention_level"] in {"轻度", "明显"}:
        flags.append("redness_attention")
        tips.append(
            {
                "title": "发红关注",
                "detail": "若现实中同一区域持续明显发红，并伴随疼痛、发热、瘙痒或肿胀，建议咨询专业医生。",
            }
        )

    if lines["clarity_level"] == "较弱":
        flags.append("low_line_clarity")
        tips.append(
            {
                "title": "重拍建议",
                "detail": "掌纹较弱时，可在自然光下重拍，保持掌心平展并避免过曝或运动模糊。",
            }
        )

    if color["tone"] == "光线偏暗":
        flags.append("low_light")
        tips.append(
            {
                "title": "光线提示",
                "detail": "当前画面偏暗，颜色类指标的可信度会下降，建议补充柔和正面光。",
            }
        )

    tips.append(
        {
            "title": "边界声明",
            "detail": DISCLAIMER,
        }
    )

    return observations, tips, flags


def _health_color_scores(color: dict[str, Any], redness: dict[str, Any]) -> dict[str, float]:
    brightness = float(color["mean_brightness"])
    saturation = float(color["mean_saturation"])
    hue = float(color["mean_hue"])
    redness_index = float(color["redness_index"])
    redness_area = float(redness["area_ratio"])

    redness_score = float(np.clip(max(redness_index * 100, redness_area * 420), 0, 100))
    pale_score = float(np.clip((brightness - 0.58) * 130 + (0.24 - saturation) * 170, 0, 100))
    yellow_hue_score = 100 if 28 <= hue <= 58 else max(0, 100 - min(abs(hue - 36), abs(hue - 52)) * 7)
    yellow_score = float(np.clip(yellow_hue_score * 0.48 + saturation * 44 + (1 if color["tone"] == "偏暖黄" else 0) * 32, 0, 100))
    lighting_quality = float(np.clip((1 - abs(brightness - 0.62) / 0.62) * 72 + min(saturation / 0.22, 1) * 28, 0, 100))

    return {
        "redness": redness_score,
        "yellow": yellow_score,
        "pale": pale_score,
        "lighting_quality": lighting_quality,
    }


def _health_texture_scores(lines: dict[str, Any], palm_ratio: float) -> dict[str, float]:
    clarity = float(lines["clarity_score"])
    palm_framing = float(np.clip(palm_ratio / 0.18 * 100, 0, 100))
    image_quality = float(np.clip(clarity * 0.62 + palm_framing * 0.38, 0, 100))

    return {
        "clarity": clarity,
        "palm_framing": palm_framing,
        "image_quality": image_quality,
    }


def _generate_health_suggestions(color_result: dict[str, float], texture_result: dict[str, float]) -> dict[str, Any]:
    redness = color_result.get("redness", 0)
    yellow = color_result.get("yellow", 0)
    pale = color_result.get("pale", 0)
    lighting = min(color_result.get("lighting_quality", 100), texture_result.get("image_quality", 100))

    possible_health_directions: list[dict[str, Any]] = []
    lifestyle_advice: list[str] = []

    if lighting < 40:
        return {
            "risk_level": "uncertain",
            "risk_label": "图片质量不足",
            "summary": "当前照片的光照、清晰度或手掌取景可能影响视觉分析，建议先复拍再参考报告。",
            "scores": {
                "redness": round(float(redness), 1),
                "yellow": round(float(yellow), 1),
                "pale": round(float(pale), 1),
                "lighting_quality": round(float(lighting), 1),
            },
            "quality_notes": _quality_notes(lighting, texture_result),
            "color_explanation": _color_explanation(redness, yellow, pale),
            "redness_explanation": _redness_explanation(redness),
            "texture_explanation": _texture_explanation(texture_result),
            "possible_health_directions": [
                {
                    "title": "图片质量不足",
                    "possible_related_issues": [
                        "光照不足",
                        "过曝",
                        "手掌区域不完整",
                        "图片模糊",
                    ],
                    "note": "当前图片质量可能影响视觉分析结果，建议重新拍摄后再参考报告。",
                }
            ],
            "lifestyle_advice": [
                "请在白天自然光下重新拍摄。",
                "保持手掌完全展开，掌心正对镜头。",
                "避免使用美颜、滤镜或强暖光。",
                "拍摄前避免刚运动、洗热水澡或饮酒。",
            ],
            "recheck_plan": [
                "间隔 10 到 15 分钟后，在自然光下重新拍摄一张。",
                "如果复拍后结果变化很大，优先参考画质更稳定的一张。",
            ],
            "consult_doctor_if": [
                "现实中有持续不适或症状，而不是仅仅照片看起来异常。",
                "同一区域持续发红、发热、疼痛、瘙痒或肿胀。",
            ],
            "medical_advice": "当前图片质量不足，暂不建议根据本次结果做健康判断。",
            "disclaimer": DISCLAIMER,
        }

    if redness > 65:
        possible_health_directions.append(
            {
                "title": "掌心偏红",
                "possible_related_issues": [
                    "运动后充血",
                    "皮肤刺激",
                    "饮酒或热水刺激",
                    "掌红斑相关表现",
                    "肝脏代谢相关问题需排除",
                    "甲状腺功能相关问题需排除",
                    "风湿免疫相关问题需排除",
                ],
                "note": "掌心偏红可能由环境、运动、饮酒、皮肤状态等多种因素造成；如果长期持续，建议咨询医生。",
            }
        )

        lifestyle_advice.extend(
            [
                "避免刚运动、洗热水澡、饮酒后立即拍照或判断掌色。",
                "在自然光下重新拍摄，观察掌心发红是否仍然明显。",
                "观察是否双手对称发红，是否伴随掌心发热或皮肤不适。",
                "近期减少饮酒，保持规律睡眠。",
                "如果伴随乏力、眼白发黄、腹胀、关节疼痛或心悸，建议咨询医生。",
            ]
        )

    if pale > 65:
        possible_health_directions.append(
            {
                "title": "掌色偏淡",
                "possible_related_issues": [
                    "光照过强",
                    "低温导致局部血流减少",
                    "疲劳状态",
                    "贫血相关表现需排除",
                    "循环状态变化",
                ],
                "note": "掌色偏淡不能直接说明贫血；如果长期明显偏白并伴随乏力、头晕等情况，建议做进一步检查。",
            }
        )

        lifestyle_advice.extend(
            [
                "换到自然光环境重新拍摄，避免过曝。",
                "注意近期是否有乏力、头晕、心慌、气短等情况。",
                "饮食上注意摄入瘦肉、蛋类、豆类、深绿色蔬菜等含铁食物。",
                "不要自行大量补铁，必要时先咨询医生或进行血常规检查。",
            ]
        )

    if yellow > 65:
        possible_health_directions.append(
            {
                "title": "掌色偏黄",
                "possible_related_issues": [
                    "暖光或相机白平衡影响",
                    "胡萝卜素摄入较多",
                    "皮肤色素变化",
                    "肝胆相关问题需排除",
                ],
                "note": "掌色偏黄可能只是光线或饮食影响；如果同时出现眼白发黄、尿色加深等情况，需要提高关注。",
            }
        )

        lifestyle_advice.extend(
            [
                "在白天自然光下重新拍摄，避免暖黄色灯光。",
                "回想近期是否大量食用胡萝卜、南瓜、橘子、红薯等食物。",
                "观察眼白是否也发黄，尿色是否明显加深。",
                "减少熬夜和饮酒，保持规律作息。",
                "如果眼白发黄、尿色加深、皮肤瘙痒或右上腹不适，建议尽快就医。",
            ]
        )

    if not possible_health_directions:
        possible_health_directions.append(
            {
                "title": "未发现明显异常视觉特征",
                "possible_related_issues": [
                    "当前图像下掌色和掌纹表现相对平稳",
                ],
                "note": "未发现明显异常不代表没有健康问题，如有身体不适仍应咨询医生。",
            }
        )

        lifestyle_advice.extend(
            [
                "保持规律作息和均衡饮食。",
                "避免长期熬夜、过量饮酒和久坐。",
                "定期体检，关注血常规、肝功能、血糖等基础指标。",
                "如果出现持续乏力、心悸、皮肤或眼白发黄、关节疼痛等症状，应及时就医。",
            ]
        )

    max_abnormal = max(redness, yellow, pale)

    if max_abnormal >= 80:
        risk_level = "high"
        risk_label = "较高视觉关注"
        medical_advice = "当前图像存在较明显视觉特征。建议在自然光下复拍确认；如果持续存在或伴随身体不适，建议咨询医生。"
    elif max_abnormal >= 60:
        risk_level = "medium"
        risk_label = "中等视觉关注"
        medical_advice = "当前图像存在一定视觉特征。建议持续观察，并结合自身症状判断是否需要咨询医生。"
    else:
        risk_level = "low"
        risk_label = "低视觉关注"
        medical_advice = "当前图像未显示明显需要高度关注的视觉特征。若有身体不适，仍建议咨询医生。"

    return {
        "risk_level": risk_level,
        "risk_label": risk_label,
        "summary": _health_summary(risk_label, redness, yellow, pale, lighting),
        "scores": {
            "redness": round(float(redness), 1),
            "yellow": round(float(yellow), 1),
            "pale": round(float(pale), 1),
            "lighting_quality": round(float(lighting), 1),
        },
        "quality_notes": _quality_notes(lighting, texture_result),
        "color_explanation": _color_explanation(redness, yellow, pale),
        "redness_explanation": _redness_explanation(redness),
        "texture_explanation": _texture_explanation(texture_result),
        "possible_health_directions": possible_health_directions,
        "lifestyle_advice": list(dict.fromkeys(lifestyle_advice)),
        "recheck_plan": _recheck_plan(redness, yellow, pale, lighting),
        "consult_doctor_if": _consult_doctor_if(redness, yellow, pale),
        "medical_advice": medical_advice,
        "disclaimer": DISCLAIMER,
    }


def _health_summary(risk_label: str, redness: float, yellow: float, pale: float, lighting: float) -> str:
    dominant = max(
        [("偏红", redness), ("偏黄", yellow), ("偏淡", pale)],
        key=lambda item: item[1],
    )
    if dominant[1] < 45:
        feature = "未见特别突出的掌色倾向"
    else:
        feature = f"{dominant[0]}分数相对更高"

    quality = "图片质量较稳定" if lighting >= 65 else "图片质量中等，建议结合复拍结果观察"
    return f"本次报告为{risk_label}：{feature}，{quality}。这些结果只描述照片中的视觉特征，不代表医学结论。"


def _quality_notes(lighting: float, texture_result: dict[str, float]) -> list[str]:
    notes: list[str] = []
    clarity = texture_result.get("clarity", 0)
    palm_framing = texture_result.get("palm_framing", 0)

    if lighting < 45:
        notes.append("光照或整体画质偏弱，颜色类分数容易受环境影响。")
    elif lighting < 70:
        notes.append("图片质量可用于初步观察，但仍建议用自然光复拍做对照。")
    else:
        notes.append("图片质量较稳定，适合做本次视觉特征参考。")

    if clarity < 40:
        notes.append("掌纹清晰度偏弱，纹理相关判断可能受到模糊、过曝或皮肤反光影响。")
    elif clarity < 66:
        notes.append("掌纹清晰度中等，能看到部分纹理，但细节仍可能被压缩或锐化影响。")
    else:
        notes.append("掌纹清晰度较好，纹理观察的参考价值相对更高。")

    if palm_framing < 55:
        notes.append("手掌在画面中的占比偏小，建议让掌心更靠近镜头。")
    else:
        notes.append("手掌取景较完整，ROI 提取结果可作为本次分析参考。")

    return notes


def _color_explanation(redness: float, yellow: float, pale: float) -> list[dict[str, str]]:
    return [
        {
            "title": "偏红分数",
            "level": _score_level(redness),
            "detail": "由红色优势、红色区域占比和饱和度估算，容易受到运动、热水、饮酒、按压和环境光影响。",
        },
        {
            "title": "偏黄分数",
            "level": _score_level(yellow),
            "detail": "由掌心色相、饱和度和暖色倾向估算，暖光、白平衡和近期饮食都可能让分数升高。",
        },
        {
            "title": "偏淡分数",
            "level": _score_level(pale),
            "detail": "由亮度偏高、饱和度偏低等特征估算，过曝、低温和拍摄角度都可能影响结果。",
        },
    ]


def _redness_explanation(redness: float) -> dict[str, str]:
    if redness >= 80:
        level = "明显"
        detail = "照片中红色视觉特征较突出，建议在自然光下复拍，并观察是否双手对称、是否持续存在。"
    elif redness >= 60:
        level = "中等"
        detail = "照片中存在一定红色视觉特征，可结合运动、饮酒、洗热水澡、皮肤刺激等近期因素理解。"
    else:
        level = "较低"
        detail = "照片中红色视觉特征不突出，但单张照片不能代表真实皮肤状态。"
    return {"level": level, "detail": detail}


def _texture_explanation(texture_result: dict[str, float]) -> dict[str, str]:
    clarity = texture_result.get("clarity", 0)
    if clarity >= 66:
        return {
            "level": "清晰",
            "detail": "掌纹边缘和局部对比度较好，说明照片锐度和纹理可见度较稳定。",
        }
    if clarity >= 40:
        return {
            "level": "中等",
            "detail": "能看到部分掌纹纹理，但细节可能受到压缩、反光或轻微模糊影响。",
        }
    return {
        "level": "较弱",
        "detail": "掌纹纹理偏弱，建议补充柔和正面光、保持掌心平展后复拍。",
    }


def _recheck_plan(redness: float, yellow: float, pale: float, lighting: float) -> list[str]:
    plan = [
        "用白天自然光复拍一张，避免美颜、滤镜、强暖光和过曝。",
        "拍摄前让手掌放松 5 到 10 分钟，避免刚运动、洗热水澡、饮酒或用力按压。",
    ]
    if max(redness, yellow, pale) >= 60:
        plan.append("间隔一天在相似光线下再次拍摄，比较掌色倾向是否仍然存在。")
    if lighting < 65:
        plan.append("如果图片质量分数不高，优先改善光照和对焦后再参考健康提示。")
    return plan


def _consult_doctor_if(redness: float, yellow: float, pale: float) -> list[str]:
    items = [
        "视觉特征持续多天存在，并且不是由光线、运动、饮酒、热水或滤镜造成。",
        "伴随明显疼痛、发热、瘙痒、肿胀、乏力、心悸或头晕。",
    ]
    if redness >= 60:
        items.append("掌心持续明显发红，或双手对称发红并伴随身体不适。")
    if yellow >= 60:
        items.append("掌色偏黄同时伴随眼白发黄、尿色加深、皮肤瘙痒或右上腹不适。")
    if pale >= 60:
        items.append("掌色长期明显偏淡，同时伴随乏力、头晕、心慌或气短。")
    return list(dict.fromkeys(items))


def _score_level(score: float) -> str:
    if score >= 80:
        return "明显"
    if score >= 60:
        return "中等"
    if score >= 40:
        return "轻度"
    return "较低"


def _build_palmistry_reading(
    color: dict[str, Any],
    redness: dict[str, Any],
    lines: dict[str, Any],
    palm_ratio: float,
) -> dict[str, Any]:
    clarity = float(lines["clarity_score"])
    edge_density = float(lines["edge_density"])
    brightness = float(color["mean_brightness"])
    redness_index = float(color["redness_index"])

    if clarity >= 66:
        line_style = "线条清晰、层次感较强"
        energy_word = "稳定"
    elif clarity >= 40:
        line_style = "线条有一定可见度"
        energy_word = "均衡"
    else:
        line_style = "线条偏柔和"
        energy_word = "松弛"

    if brightness >= 0.72:
        color_mood = "画面明亮，整体氛围显得轻快"
    elif brightness >= 0.46:
        color_mood = "画面亮度适中，视觉氛围比较平衡"
    else:
        color_mood = "画面偏暗，解读会更偏向保守"

    if redness["attention_level"] == "明显":
        color_note = "红色区域更醒目，娱乐解读里会被视作行动感较强的视觉符号"
    elif redness["attention_level"] == "轻度":
        color_note = "局部暖色略有存在，娱乐解读里会被视作表达欲或热情的点缀"
    else:
        color_note = "红色区域不突出，娱乐解读里会被视作节奏较稳的视觉符号"

    confidence = float(np.clip(clarity * 0.55 + min(edge_density / 0.08, 1) * 24 + min(palm_ratio / 0.22, 1) * 21, 0, 100))
    archetype = _palmistry_archetype(clarity, brightness, redness["attention_level"])
    keywords = _palmistry_keywords(clarity, brightness, redness["attention_level"], color["tone"])
    life_score = round(float(np.clip(clarity * 0.5 + brightness * 30 + palm_ratio * 90, 0, 100)), 1)
    head_score = round(float(np.clip(clarity * 0.62 + min(edge_density / 0.08, 1) * 38, 0, 100)), 1)
    heart_score = round(float(np.clip(clarity * 0.45 + redness_index * 34 + brightness * 21, 0, 100)), 1)
    career_score = round(
        float(np.clip(clarity * 0.54 + min(edge_density / 0.1, 1) * 26 + (1 - abs(brightness - 0.62)) * 20, 0, 100)),
        1,
    )

    return {
        "title": "趣味手相解读",
        "summary": f"这张手掌照片中，掌纹呈现{line_style}，{color_mood}；{color_note}。整体娱乐设定可写成「{archetype}」。",
        "archetype": archetype,
        "keywords": keywords,
        "confidence_label": _palmistry_confidence_label(confidence),
        "confidence_score": round(confidence, 1),
        "disclaimer": PALMISTRY_DISCLAIMER,
        "lines": [
            {
                "name": "生命线",
                "score": life_score,
                "theme": f"{energy_word}感",
                "detail": _palmistry_life_line(clarity, brightness, palm_ratio),
                "visual_basis": _palmistry_life_basis(clarity, brightness, palm_ratio),
                "entertainment_advice": _palmistry_life_advice(clarity, brightness, palm_ratio),
            },
            {
                "name": "智慧线",
                "score": head_score,
                "theme": "思考节奏",
                "detail": _palmistry_head_line(clarity, edge_density),
                "visual_basis": _palmistry_head_basis(clarity, edge_density),
                "entertainment_advice": _palmistry_head_advice(clarity, edge_density),
            },
            {
                "name": "感情线",
                "score": heart_score,
                "theme": "表达温度",
                "detail": _palmistry_heart_line(redness["attention_level"], redness_index, brightness),
                "visual_basis": _palmistry_heart_basis(redness["attention_level"], redness_index, brightness),
                "entertainment_advice": _palmistry_heart_advice(redness["attention_level"], brightness),
            },
            {
                "name": "事业线",
                "score": career_score,
                "theme": "推进方式",
                "detail": _palmistry_career_line(clarity, edge_density, color["tone"]),
                "visual_basis": _palmistry_career_basis(clarity, edge_density, color["tone"]),
                "entertainment_advice": _palmistry_career_advice(clarity, edge_density, color["tone"]),
            },
        ],
        "overall_advice": _palmistry_overall_advice(clarity, brightness, redness["attention_level"], archetype),
        "relationship_advice": _palmistry_relationship_advice(redness["attention_level"], brightness),
        "work_rhythm_advice": _palmistry_work_rhythm_advice(clarity, edge_density, color["tone"]),
        "daily_rhythm_advice": _palmistry_daily_rhythm_advice(clarity, brightness),
        "photo_tips": _palmistry_photo_tips(confidence, brightness, palm_ratio),
        "share_copy": f"PalmLens 趣味手相：{archetype}｜关键词：{' / '.join(keywords[:3])}。仅供娱乐，不用于现实判断。",
        "lifestyle_notes": [
            "把这部分当成互动娱乐卡片，适合截图分享，不用于做现实判断。",
            "若想得到更清晰的手相卡片，可在自然光下平展掌心并避免强反光。",
        ],
    }


def _palmistry_confidence_label(score: float) -> str:
    if score >= 72:
        return "图像可读性较高"
    if score >= 48:
        return "图像可读性中等"
    return "图像可读性偏弱"


def _palmistry_archetype(clarity: float, brightness: float, attention_level: str) -> str:
    if clarity >= 66 and attention_level == "明显":
        return "行动外放型"
    if clarity >= 66:
        return "稳步推进型"
    if attention_level in {"轻度", "明显"} and brightness >= 0.5:
        return "热感表达型"
    if clarity < 40 and brightness < 0.46:
        return "慢热留白型"
    if clarity < 40:
        return "直觉感受型"
    return "平衡观察型"


def _palmistry_keywords(clarity: float, brightness: float, attention_level: str, tone: str) -> list[str]:
    keywords: list[str] = []
    if clarity >= 66:
        keywords.extend(["清晰目标", "稳定推进"])
    elif clarity >= 40:
        keywords.extend(["平衡节奏", "慢慢成形"])
    else:
        keywords.extend(["直觉留白", "轻盈调整"])

    if attention_level == "明显":
        keywords.extend(["行动感", "表达力"])
    elif attention_level == "轻度":
        keywords.append("温度感")
    else:
        keywords.append("沉稳感")

    if brightness >= 0.72:
        keywords.append("明亮感")
    elif brightness < 0.46:
        keywords.append("低调感")

    if tone == "偏暖黄":
        keywords.append("暖调氛围")
    elif tone == "偏淡":
        keywords.append("轻柔氛围")

    return list(dict.fromkeys(keywords))[:5]


def _palmistry_life_line(clarity: float, brightness: float, palm_ratio: float) -> str:
    if clarity >= 66 and palm_ratio >= 0.12:
        return "娱乐解读中，生命线呈现清楚而有支撑的观感，像是偏稳定、能量续航感不错的设定。"
    if brightness < 0.42:
        return "画面偏暗，生命线细节不够充分，娱乐解读更适合描述为慢热、需要留白的节奏。"
    return "生命线细节呈现中等，娱乐解读里可理解为节奏平稳，适合持续积累型的状态。"


def _palmistry_life_basis(clarity: float, brightness: float, palm_ratio: float) -> str:
    return (
        f"参考掌纹清晰度 {clarity:.0f}/100、画面亮度 {brightness * 100:.0f}%、掌心画面占比 "
        f"{palm_ratio * 100:.1f}%。这些数值只用于生成娱乐卡片的视觉描述。"
    )


def _palmistry_life_advice(clarity: float, brightness: float, palm_ratio: float) -> list[str]:
    advice = [
        "可以把生命线写成“个人节奏感”的娱乐符号，用来表达今天适合稳住步调。",
        "适合搭配一条轻松的状态文案，例如先把重要的小事完成，再给自己留一点缓冲。"
    ]
    if clarity >= 66 and palm_ratio >= 0.12:
        advice.append("掌纹更清楚时，分享卡片可以强调持续感和耐心积累的氛围。")
    elif brightness < 0.42:
        advice.append("画面偏暗时，建议把解读写得更温和，避免使用绝对化判断。")
    else:
        advice.append("当前适合走平稳叙事，少用夸张词，把重点放在节奏和陪伴感上。")
    return advice


def _palmistry_head_line(clarity: float, edge_density: float) -> str:
    if clarity >= 60 and edge_density >= 0.045:
        return "智慧线的纹理感较丰富，娱乐解读里像是思路活跃、善于拆解问题的设定。"
    if clarity < 38:
        return "智慧线在照片中偏柔和，娱乐解读更接近直觉派、先感受再整理的风格。"
    return "智慧线可见度适中，娱乐解读里适合描述为理性与直觉之间比较平衡。"


def _palmistry_head_basis(clarity: float, edge_density: float) -> str:
    return f"参考掌纹清晰度 {clarity:.0f}/100 与边缘密度 {edge_density:.3f}，用于估计照片中纹理层次是否丰富。"


def _palmistry_head_advice(clarity: float, edge_density: float) -> list[str]:
    if clarity >= 60 and edge_density >= 0.045:
        return [
            "娱乐设定里可以把智慧线写成“拆解型思路”，适合配合清单、步骤、复盘这类关键词。",
            "分享文案可以偏简洁利落，突出把复杂问题拆小的画面感。"
        ]
    if clarity < 38:
        return [
            "娱乐设定里可以把智慧线写成“直觉先行”，适合搭配灵感、感受、慢慢整理这类关键词。",
            "如果想让这条线更有表现力，重拍时可让掌心更靠近镜头并减少阴影。"
        ]
    return [
        "娱乐设定里可以把智慧线写成“理性与直觉并行”，适合表达先观察再行动的节奏。",
        "这类卡片适合做温和建议，不适合写成确定性的判断。"
    ]


def _palmistry_heart_line(attention_level: str, redness_index: float, brightness: float) -> str:
    if attention_level == "明显" or redness_index >= 0.34:
        return "感情线区域的暖色存在感较强，娱乐解读里像是表达直接、情绪能量比较外放。"
    if brightness >= 0.72:
        return "画面明亮，感情线在娱乐解读里显得轻快、开放，适合温和但不沉闷的表达。"
    return "感情线呈现克制的视觉氛围，娱乐解读里可理解为慢热、重视安全感。"


def _palmistry_heart_basis(attention_level: str, redness_index: float, brightness: float) -> str:
    return (
        f"参考局部红色关注等级「{attention_level}」、发红指数 {redness_index * 100:.0f}、"
        f"画面亮度 {brightness * 100:.0f}%。这里只把暖色当作娱乐表达符号。"
    )


def _palmistry_heart_advice(attention_level: str, brightness: float) -> list[str]:
    if attention_level == "明显":
        return [
            "娱乐设定里可以把感情线写成“表达更直接”，适合配合热情、坦率、现场感这类词。",
            "文案里建议保留边界感，避免写成对关系走向的判断。"
        ]
    if brightness >= 0.72:
        return [
            "画面明亮时，感情线卡片可以偏轻快，适合写成舒服、开放、愿意沟通的氛围。",
            "适合用作社交分享里的互动标签，而不是现实关系建议。"
        ]
    return [
        "娱乐设定里可以把感情线写成慢热和重视安全感的氛围。",
        "如果想让感情线更清楚，可换到柔和自然光下拍摄，减少掌心阴影。"
    ]


def _palmistry_career_line(clarity: float, edge_density: float, tone: str) -> str:
    if clarity >= 62 and edge_density >= 0.042:
        return "事业线相关纹理更有方向感，娱乐解读里像是目标感较明确、推进力较强。"
    if tone == "光线偏暗":
        return "当前光线让事业线不够突出，娱乐解读更适合描述为低调积累、先观察再行动。"
    return "事业线呈现中性观感，娱乐解读里适合写成稳步推进、靠长期习惯建立优势。"


def _palmistry_career_basis(clarity: float, edge_density: float, tone: str) -> str:
    return f"参考掌纹清晰度 {clarity:.0f}/100、边缘密度 {edge_density:.3f} 和掌色氛围「{tone}」，生成推进方式类娱乐文本。"


def _palmistry_career_advice(clarity: float, edge_density: float, tone: str) -> list[str]:
    if clarity >= 62 and edge_density >= 0.042:
        return [
            "娱乐设定里可以把事业线写成“目标路线更明确”，适合配合项目、计划、推进这类关键词。",
            "建议文案聚焦可执行的小目标，不写成事业成败或未来结果。"
        ]
    if tone == "光线偏暗":
        return [
            "画面偏暗时，事业线适合写成低调积累和观察期，整体语气更含蓄。",
            "重拍后若纹理更清晰，娱乐卡片的方向感也会更强。"
        ]
    return [
        "娱乐设定里可以把事业线写成稳步推进，强调长期习惯带来的秩序感。",
        "适合给出轻量行动提示，例如今天先完成一个最重要的小步骤。"
    ]


def _palmistry_overall_advice(clarity: float, brightness: float, attention_level: str, archetype: str) -> list[str]:
    advice = [
        f"整体卡片可以围绕「{archetype}」展开，把掌纹清晰度、暖色氛围和掌心占比转化为视觉故事。",
        "所有文案建议使用“娱乐设定”“视觉氛围”“可以理解为”等表达，避免写成确定结论。"
    ]
    if clarity >= 66:
        advice.append("掌纹较清楚时，适合突出目标感、持续感和有条理的推进节奏。")
    elif clarity < 40:
        advice.append("掌纹偏柔和时，适合突出慢热、留白、灵感和自我调整的氛围。")
    else:
        advice.append("掌纹可见度中等时，适合写成平衡型叙事，既有计划感也保留弹性。")

    if attention_level in {"轻度", "明显"}:
        advice.append("暖色区域较明显时，娱乐文案可以增加行动感和表达感，但不把它解释为现实情绪或健康结论。")
    elif brightness < 0.46:
        advice.append("画面偏暗时，建议把整体解读写得更保守，并提示重新拍摄可提升可读性。")
    return advice


def _palmistry_relationship_advice(attention_level: str, brightness: float) -> list[str]:
    if attention_level == "明显":
        return [
            "关系表达卡片可写成“热度在线，适合把话说清楚一点”，只作为轻松互动文案。",
            "避免把掌纹写成感情走向预测，建议用温和、开放、边界清楚的表达。"
        ]
    if brightness >= 0.72:
        return [
            "明亮画面适合生成轻快社交文案，例如更适合自然表达、减少拐弯。",
            "可以把它当作聊天开场素材，而不是对关系状态的判断。"
        ]
    return [
        "关系表达卡片可写成“慢热但重视安全感”，语气适合柔和一点。",
        "适合提醒用户把手相内容当作话题，不把它当作真实关系依据。"
    ]


def _palmistry_work_rhythm_advice(clarity: float, edge_density: float, tone: str) -> list[str]:
    if clarity >= 62 and edge_density >= 0.042:
        return [
            "工作节奏卡片可写成“先定方向，再拆步骤”，突出清晰纹理带来的秩序感。",
            "适合给出今日小目标式文案，例如先推进一件最关键的事。"
        ]
    if tone == "光线偏暗" or clarity < 40:
        return [
            "工作节奏卡片可写成“先观察、再推进”，适合低调积累的叙事。",
            "如果要分享，建议把重点放在调整节奏，而不是给出结果承诺。"
        ]
    return [
        "工作节奏卡片可写成“稳中带弹性”，适合把任务拆成几个可完成的小块。",
        "建议文案强调过程感，不写成事业预测。"
    ]


def _palmistry_daily_rhythm_advice(clarity: float, brightness: float) -> list[str]:
    advice = [
        "日常状态卡片可以把掌纹当作视觉日记，记录今天的节奏感和画面氛围。",
        "建议把解读当作轻松自我观察，不把它当作健康、性格或运势依据。"
    ]
    if clarity >= 66:
        advice.append("掌纹清楚时，可以设置一个更明确的小主题，例如整理、完成、推进。")
    elif brightness < 0.46:
        advice.append("画面偏暗时，可以把主题写得更安静，例如休整、慢下来、留白。")
    else:
        advice.append("整体中等时，可以把主题写成保持节奏、给自己一点弹性。")
    return advice


def _palmistry_photo_tips(confidence: float, brightness: float, palm_ratio: float) -> list[str]:
    tips = [
        "掌心自然展开，手指轻轻分开，让掌心纹理占据画面中心。",
        "使用白天自然光或柔和侧前方光线，避免滤镜、强暖光和明显反光。"
    ]
    if confidence < 55:
        tips.append("当前娱乐可读性偏低，可让手掌更靠近镜头并保持对焦后重新拍摄。")
    if brightness < 0.46:
        tips.append("画面偏暗时，增加柔和正面光会让掌纹增强图更清晰。")
    if palm_ratio < 0.1:
        tips.append("手掌占比偏小时，靠近一点拍摄会让生命线、智慧线等卡片更完整。")
    return list(dict.fromkeys(tips))


def _mask_area_ratio(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask) / mask.size)
