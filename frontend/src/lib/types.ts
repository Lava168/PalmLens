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
    possible_health_directions: Array<{
      title: string;
      possible_related_issues: string[];
      note: string;
    }>;
    lifestyle_advice: string[];
    medical_advice: string;
    disclaimer: string;
  };
  palmistry: {
    title: string;
    summary: string;
    confidence_label: string;
    confidence_score: number;
    disclaimer: string;
    lines: Array<{
      name: string;
      score: number;
      theme: string;
      detail: string;
    }>;
    lifestyle_notes: string[];
  };
  flags: string[];
  disclaimer: string;
};
