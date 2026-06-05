export type ReportItem = {
  title: string;
  value?: string;
  detail: string;
};

export type PalmLensReport = {
  image: {
    width: number;
    height: number;
    processed_at: string;
    palm_detected: boolean;
    detection_method: string;
    confidence: number;
    overlay_image: string;
    line_enhanced_image: string;
    red_heatmap_image: string;
  };
  metrics: {
    palm_area_ratio: number;
    color: {
      tone: string;
      mean_hue: number;
      mean_saturation: number;
      mean_brightness: number;
      redness_index: number;
    };
    redness: {
      attention_level: string;
      area_ratio: number;
      largest_patch_ratio: number;
      patch_count: number;
    };
    lines: {
      clarity_level: string;
      clarity_score: number;
      edge_density: number;
      contrast_score: number;
    };
  };
  observations: ReportItem[];
  tips: ReportItem[];
  health_suggestions: {
    risk_level: "low" | "medium" | "high" | "uncertain";
    risk_label: string;
    scores: {
      redness: number;
      yellow: number;
      pale: number;
      lighting_quality: number;
    };
    summary: string;
    quality_notes: string[];
    color_explanation: Array<{
      title: string;
      level: string;
      detail: string;
    }>;
    redness_explanation: {
      level: string;
      detail: string;
    };
    texture_explanation: {
      level: string;
      detail: string;
    };
    possible_health_directions: Array<{
      title: string;
      possible_related_issues: string[];
      note: string;
    }>;
    lifestyle_advice: string[];
    recheck_plan: string[];
    consult_doctor_if: string[];
    medical_advice: string;
    disclaimer: string;
  };
  palmistry: {
    title: string;
    summary: string;
    archetype: string;
    keywords: string[];
    confidence_label: string;
    confidence_score: number;
    disclaimer: string;
    lines: Array<{
      name: string;
      score: number;
      theme: string;
      detail: string;
      visual_basis: string;
      entertainment_advice: string[];
    }>;
    overall_advice: string[];
    relationship_advice: string[];
    work_rhythm_advice: string[];
    daily_rhythm_advice: string[];
    photo_tips: string[];
    share_copy: string;
    lifestyle_notes: string[];
  };
  skin_screening: {
    title: string;
    attention_level: string;
    summary: string;
    scores: {
      inflammation: number;
      distribution: number;
      texture: number;
      infection_attention: number;
    };
    visible_findings: Array<{
      title: string;
      level: string;
      detail: string;
    }>;
    possible_visual_patterns: Array<{
      name: string;
      basis: string;
      non_diagnostic_note: string;
    }>;
    hygiene_guidance: string[];
    seek_care_if: string[];
    photo_limitations: string[];
    disclaimer: string;
  };
  ai_enhancement: {
    provider: string;
    status: "generated" | "not_configured" | "disabled" | "error" | "safety_fallback";
    status_label: string;
    source: "ai_api" | "local_template";
    model: string;
    title: string;
    summary: string;
    health_insights: string[];
    palmistry_story: string[];
    next_steps: string[];
    safety_note: string;
    error_message?: string | null;
  };
  flags: string[];
  disclaimer: string;
};
