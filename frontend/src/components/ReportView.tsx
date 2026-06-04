import { useState } from "react";
import {
  AlertTriangle,
  BadgeInfo,
  Eye,
  Fingerprint,
  HeartPulse,
  ScanLine,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import { MetricBar } from "@/components/MetricBar";
import type { PalmLensReport } from "@/lib/types";

type ReportViewProps = {
  report: PalmLensReport | null;
};

export function ReportView({ report }: ReportViewProps) {
  const [mode, setMode] = useState<"health" | "palmistry">("health");

  if (!report) {
    return (
      <section className="glass-panel flex min-h-[560px] flex-col justify-between rounded-[8px] p-6 md:p-8">
        <div className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-[8px] bg-ink text-white">
            <ScanLine className="size-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase text-clay">Visual report</p>
            <h2 className="text-2xl font-semibold text-ink">等待分析</h2>
          </div>
        </div>

        <div className="overflow-hidden rounded-[8px] border border-white/60 bg-celadon/45">
          <img
            src="/palm-lens-art.png"
            alt=""
            className="h-[330px] w-full object-cover mix-blend-multiply"
          />
        </div>

        <div className="rounded-[8px] border border-coral/20 bg-white/60 p-4 text-sm leading-6 text-mineral">
          PalmLens 输出图像视觉观察、健康科普提示和娱乐性质手相解读；不输出疾病名称、诊断结论或治疗建议。
        </div>
      </section>
    );
  }

  const rednessPercent = report.metrics.redness.area_ratio * 100;
  const confidencePercent = report.image.confidence * 100;
  const palmAreaPercent = report.metrics.palm_area_ratio * 100;
  const brightnessPercent = report.metrics.color.mean_brightness * 100;
  const rednessIndexPercent = report.metrics.color.redness_index * 100;
  const healthTone = {
    low: "sage",
    medium: "pollen",
    high: "coral",
    uncertain: "pollen"
  }[report.health_suggestions.risk_level] as "sage" | "pollen" | "coral";
  const visualizations = [
    {
      title: "综合叠加图",
      detail: "掌心区域、掌纹边缘与发红区域的综合视觉标记。",
      src: report.image.overlay_image,
      alt: "PalmLens palm region overlay"
    },
    {
      title: "掌纹增强图",
      detail: "增强局部对比后突出掌纹边缘，用于观察照片中的纹理清晰度。",
      src: report.image.line_enhanced_image,
      alt: "PalmLens enhanced palm line visualization"
    },
    {
      title: "红色热力图",
      detail: "以热力图显示红色高饱和像素分布，只代表照片中的颜色特征。",
      src: report.image.red_heatmap_image,
      alt: "PalmLens red color heatmap"
    }
  ];

  return (
    <section className="glass-panel rounded-[8px] p-6 md:p-8">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-[8px] bg-ink text-white">
            <Eye className="size-5" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase text-clay">Visual report</p>
            <h2 className="text-2xl font-semibold text-ink">
              {mode === "health" ? "非诊断型健康提示" : "趣味手相解读"}
            </h2>
          </div>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-[8px] border border-sage/50 bg-white/65 px-3 py-1.5 text-sm font-medium text-mineral">
          <ShieldCheck className="size-4 text-sage" aria-hidden="true" />
          {report.image.detection_method}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-4">
          <div className="grid gap-4">
            {visualizations.map((item) => (
              <figure
                key={item.title}
                className="overflow-hidden rounded-[8px] border border-white/70 bg-ink"
              >
                <img
                  src={item.src}
                  alt={item.alt}
                  className="aspect-[4/3] w-full object-contain"
                />
                <figcaption className="border-t border-white/10 bg-white/90 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    {item.title === "红色热力图" ? (
                      <span className="h-2 w-20 rounded-full bg-gradient-to-r from-sage via-pollen to-coral" />
                    ) : null}
                  </div>
                  <p className="mt-1 text-xs leading-5 text-mineral">{item.detail}</p>
                </figcaption>
              </figure>
            ))}
          </div>
          <div className="rounded-[8px] border border-sage/25 bg-white/58 p-4">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
              <ScanLine className="size-4 text-sage" aria-hidden="true" />
              分析分数
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <MetricBar label="检测参考" value={`${confidencePercent.toFixed(0)}%`} percent={confidencePercent} />
              <MetricBar
                label="掌心占比"
                value={`${palmAreaPercent.toFixed(1)}%`}
                percent={Math.min(100, palmAreaPercent * 2.4)}
                tone="sage"
              />
              <MetricBar
                label="画面亮度"
                value={`${brightnessPercent.toFixed(0)}%`}
                percent={brightnessPercent}
                tone="pollen"
              />
              <MetricBar
                label="发红指数"
                value={`${rednessIndexPercent.toFixed(0)}`}
                percent={rednessIndexPercent}
                tone={rednessIndexPercent >= 30 ? "coral" : "pollen"}
              />
              <MetricBar
                label="发红占比"
                value={`${rednessPercent.toFixed(1)}%`}
                percent={Math.min(100, rednessPercent * 5)}
                tone={report.metrics.redness.attention_level === "明显" ? "coral" : "pollen"}
              />
              <MetricBar
                label="掌纹评分"
                value={`${report.metrics.lines.clarity_score.toFixed(0)}`}
                percent={report.metrics.lines.clarity_score}
                tone="sage"
              />
            </div>
          </div>
        </div>

        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-2 rounded-[8px] border border-sage/25 bg-white/58 p-1.5">
            <button
              className={[
                "focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-[6px] text-sm font-semibold transition",
                mode === "health" ? "bg-ink text-white" : "text-mineral hover:bg-white/70 hover:text-ink"
              ].join(" ")}
              onClick={() => setMode("health")}
              type="button"
            >
              <HeartPulse className="size-4" aria-hidden="true" />
              健康分析
            </button>
            <button
              className={[
                "focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-[6px] text-sm font-semibold transition",
                mode === "palmistry" ? "bg-ink text-white" : "text-mineral hover:bg-white/70 hover:text-ink"
              ].join(" ")}
              onClick={() => setMode("palmistry")}
              type="button"
            >
              <Fingerprint className="size-4" aria-hidden="true" />
              趣味手相
            </button>
          </div>

          {mode === "health" ? (
            <>
              <div className="rounded-[8px] border border-sage/25 bg-white/58 p-4">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <HeartPulse className="size-4 text-coral" aria-hidden="true" />
                  视觉关注等级
                </div>
                <MetricBar
                  label={report.health_suggestions.risk_label}
                  value={report.health_suggestions.risk_level.toUpperCase()}
                  percent={
                    report.health_suggestions.risk_level === "high"
                      ? 92
                      : report.health_suggestions.risk_level === "medium"
                        ? 64
                        : report.health_suggestions.risk_level === "uncertain"
                          ? 42
                          : 28
                  }
                  tone={healthTone}
                />
                <p className="mt-3 text-sm leading-6 text-mineral">{report.health_suggestions.medical_advice}</p>
              </div>

              <div className="rounded-[8px] border border-sage/25 bg-white/58 p-4">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <ScanLine className="size-4 text-sage" aria-hidden="true" />
                  色彩关注分数
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <MetricBar
                    label="偏红"
                    value={`${report.health_suggestions.scores.redness.toFixed(0)}`}
                    percent={report.health_suggestions.scores.redness}
                    tone={report.health_suggestions.scores.redness > 65 ? "coral" : "pollen"}
                  />
                  <MetricBar
                    label="偏黄"
                    value={`${report.health_suggestions.scores.yellow.toFixed(0)}`}
                    percent={report.health_suggestions.scores.yellow}
                    tone="pollen"
                  />
                  <MetricBar
                    label="偏淡"
                    value={`${report.health_suggestions.scores.pale.toFixed(0)}`}
                    percent={report.health_suggestions.scores.pale}
                    tone="sage"
                  />
                  <MetricBar
                    label="图片质量"
                    value={`${report.health_suggestions.scores.lighting_quality.toFixed(0)}`}
                    percent={report.health_suggestions.scores.lighting_quality}
                    tone="sage"
                  />
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <Sparkles className="size-4 text-coral" aria-hidden="true" />
                  Possible directions
                </div>
                <div className="space-y-3">
                  {report.health_suggestions.possible_health_directions.map((item) => (
                    <div key={item.title} className="rounded-[8px] border border-sage/25 bg-white/58 p-4">
                      <div className="flex items-center justify-between gap-4">
                        <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                        <span className="rounded-[6px] bg-celadon/70 px-2.5 py-1 text-xs font-semibold text-mineral">
                          科普方向
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-mineral">{item.note}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.possible_related_issues.map((issue) => (
                          <span
                            key={issue}
                            className="rounded-[6px] border border-sage/25 bg-white/65 px-2.5 py-1 text-xs font-semibold text-mineral"
                          >
                            {issue}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <BadgeInfo className="size-4 text-sage" aria-hidden="true" />
                  Lifestyle notes
                </div>
                <div className="space-y-3">
                  {report.health_suggestions.lifestyle_advice.map((item) => (
                    <div key={item} className="rounded-[8px] border border-white/70 bg-white/58 p-4">
                      <p className="text-sm leading-6 text-mineral">{item}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <Sparkles className="size-4 text-coral" aria-hidden="true" />
                  Observations
                </div>
                <div className="divide-y divide-sage/20 rounded-[8px] border border-sage/25 bg-white/55">
                  {report.observations.map((item) => (
                    <div key={item.title} className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                        {item.value ? <span className="text-sm font-semibold text-clay">{item.value}</span> : null}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-mineral">{item.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                  <HeartPulse className="size-4 text-coral" aria-hidden="true" />
                  Health notes
                </div>
                <div className="space-y-3">
                  {report.tips.map((item) => (
                    <div key={item.title} className="rounded-[8px] border border-white/70 bg-white/58 p-4">
                      <div className="flex items-center gap-2">
                        {item.title === "边界声明" ? (
                          <AlertTriangle className="size-4 text-coral" aria-hidden="true" />
                        ) : (
                          <BadgeInfo className="size-4 text-sage" aria-hidden="true" />
                        )}
                        <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-mineral">{item.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[8px] border border-coral/25 bg-coral/10 p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-4 text-coral" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-ink">边界声明</h3>
                </div>
                <p className="mt-2 text-sm leading-6 text-mineral">{report.health_suggestions.disclaimer}</p>
              </div>
            </>
          ) : (
            <div className="space-y-5">
              <div className="rounded-[8px] border border-sage/25 bg-white/58 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2 text-sm font-semibold uppercase text-mineral">
                    <Fingerprint className="size-4 text-sage" aria-hidden="true" />
                    Palm reading
                  </div>
                  <span className="rounded-[6px] bg-celadon/70 px-2.5 py-1 text-xs font-semibold text-mineral">
                    {report.palmistry.confidence_label}
                  </span>
                </div>
                <h3 className="mt-3 text-lg font-semibold text-ink">{report.palmistry.title}</h3>
                <p className="mt-2 text-sm leading-6 text-mineral">{report.palmistry.summary}</p>
                <div className="mt-4">
                  <MetricBar
                    label="娱乐可读性"
                    value={`${report.palmistry.confidence_score.toFixed(0)}`}
                    percent={report.palmistry.confidence_score}
                    tone="pollen"
                  />
                </div>
              </div>

              <div className="grid gap-3">
                {report.palmistry.lines.map((item) => (
                  <div key={item.name} className="rounded-[8px] border border-white/70 bg-white/58 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-sm font-semibold text-ink">{item.name}</h3>
                        <p className="mt-1 text-xs font-semibold text-clay">{item.theme}</p>
                      </div>
                      <span className="shrink-0 rounded-[6px] bg-ink px-2.5 py-1 text-xs font-semibold text-white">
                        {item.score.toFixed(0)}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-mineral">{item.detail}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-3">
                {report.palmistry.lifestyle_notes.map((item) => (
                  <div key={item} className="rounded-[8px] border border-pollen/45 bg-white/58 p-4">
                    <div className="flex items-center gap-2">
                      <BadgeInfo className="size-4 text-sage" aria-hidden="true" />
                      <p className="text-sm leading-6 text-mineral">{item}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-[8px] border border-coral/25 bg-coral/10 p-4">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="size-4 text-coral" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-ink">娱乐声明</h3>
                </div>
                <p className="mt-2 text-sm leading-6 text-mineral">{report.palmistry.disclaimer}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
