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


def _mask_area_ratio(mask: np.ndarray) -> float:
    return float(np.count_nonzero(mask) / mask.size)
