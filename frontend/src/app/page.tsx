"use client";

import { ChangeEvent, DragEvent, KeyboardEvent, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  ImagePlus,
  Loader2,
  Microscope,
  RotateCcw,
  UploadCloud
} from "lucide-react";
import { ReportView } from "@/components/ReportView";
import type { PalmLensReport } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [report, setReport] = useState<PalmLensReport | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const canAnalyze = Boolean(file) && !isLoading;
  const fileMeta = useMemo(() => {
    if (!file) return null;
    return `${(file.size / 1024 / 1024).toFixed(2)} MB · ${file.type.replace("image/", "").toUpperCase()}`;
  }, [file]);

  function selectFile(nextFile: File | undefined) {
    if (!nextFile) return;

    if (!nextFile.type.startsWith("image/")) {
      setError("请选择图片文件。");
      return;
    }

    setFile(nextFile);
    setReport(null);
    setError(null);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return URL.createObjectURL(nextFile);
    });
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    selectFile(event.dataTransfer.files?.[0]);
  }

  function openFilePicker() {
    inputRef.current?.click();
  }

  function handlePickerKey(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openFilePicker();
    }
  }

  async function analyze() {
    if (!file) return;

    setIsLoading(true);
    setError(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 45_000);
      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: form,
        signal: controller.signal
      });
      window.clearTimeout(timeout);

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "分析失败，请稍后再试。");
      }

      setReport(payload as PalmLensReport);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") {
        setError("分析超时，请换一张更小的图片。");
      } else if (reason instanceof Error) {
        setError(reason.message);
      } else {
        setError("分析失败，请检查后端服务是否已启动。");
      }
    } finally {
      setIsLoading(false);
    }
  }

  function reset() {
    setFile(null);
    setReport(null);
    setError(null);
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <main className="min-h-screen px-4 py-5 md:px-8 md:py-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-4 rounded-[8px] border border-white/55 bg-white/56 px-5 py-4 shadow-lens backdrop-blur-xl md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="grid size-12 place-items-center rounded-[8px] bg-ink text-white">
              <Microscope className="size-6" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-ink md:text-3xl">PalmLens</h1>
              <p className="text-sm font-medium text-mineral">基于手掌图像的健康科普提示网站</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-[8px] border border-sage/45 bg-white/70 px-3 py-1.5 text-sm font-semibold text-mineral">
              视觉观察
            </span>
            <span className="rounded-[8px] border border-coral/30 bg-white/70 px-3 py-1.5 text-sm font-semibold text-clay">
              非诊断
            </span>
          </div>
        </header>

        <div className="grid gap-5 lg:grid-cols-[0.78fr_1.22fr]">
          <section className="glass-panel rounded-[8px] p-5 md:p-6">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase text-clay">Capture</p>
                <h2 className="mt-1 text-2xl font-semibold text-ink">掌心图像</h2>
              </div>
              {file ? (
                <button
                  className="focus-ring inline-grid size-10 place-items-center rounded-[8px] border border-sage/40 bg-white/72 text-mineral transition hover:border-coral/45 hover:text-clay"
                  onClick={reset}
                  title="重置"
                  type="button"
                >
                  <RotateCcw className="size-4" aria-hidden="true" />
                </button>
              ) : null}
            </div>

            <input
              ref={inputRef}
              className="sr-only"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFileInput}
            />

            <div
              role="button"
              aria-label="上传手掌照片"
              className={[
                "focus-ring group flex min-h-[360px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-[8px] border border-dashed p-4 text-center transition",
                isDragging
                  ? "border-coral bg-coral/10"
                  : "border-sage/55 bg-white/50 hover:border-coral/55 hover:bg-white/68"
              ].join(" ")}
              onClick={openFilePicker}
              onKeyDown={handlePickerKey}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              tabIndex={0}
            >
              {previewUrl ? (
                <figure className="flex w-full flex-col gap-3">
                  <div className="flex items-center justify-between gap-3">
                    <figcaption className="text-sm font-semibold text-ink">原图预览</figcaption>
                    <span className="rounded-[6px] bg-white/70 px-2.5 py-1 text-xs font-semibold text-mineral">
                      本地预览
                    </span>
                  </div>
                  <img
                    src={previewUrl}
                    alt="Uploaded palm preview"
                    className="h-[330px] w-full rounded-[6px] object-contain"
                  />
                </figure>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="grid size-16 place-items-center rounded-[8px] bg-ink text-white transition group-hover:bg-clay">
                    <ImagePlus className="size-7" aria-hidden="true" />
                  </div>
                  <div className="mt-5 max-w-xs">
                    <p className="text-lg font-semibold text-ink">上传手掌照片</p>
                    <p className="mt-2 text-sm leading-6 text-mineral">JPG、PNG、WebP · 8MB 以内</p>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-5 flex flex-col gap-3">
              {file ? (
                <div className="rounded-[8px] border border-sage/25 bg-white/58 px-4 py-3">
                  <p className="truncate text-sm font-semibold text-ink">{file.name}</p>
                  <p className="mt-1 text-xs font-medium text-mineral">{fileMeta}</p>
                </div>
              ) : null}

              <button
                className="focus-ring inline-flex h-12 items-center justify-center gap-2 rounded-[8px] bg-ink px-5 text-sm font-semibold text-white transition hover:bg-clay disabled:cursor-not-allowed disabled:bg-mineral/40"
                disabled={!canAnalyze}
                onClick={analyze}
                type="button"
              >
                {isLoading ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Activity className="size-4" aria-hidden="true" />
                )}
                {isLoading ? "分析中" : "生成视觉报告"}
              </button>

              <button
                className="focus-ring inline-flex h-11 items-center justify-center gap-2 rounded-[8px] border border-sage/40 bg-white/70 px-5 text-sm font-semibold text-mineral transition hover:border-coral/45 hover:text-clay"
                onClick={openFilePicker}
                type="button"
              >
                <UploadCloud className="size-4" aria-hidden="true" />
                选择图片
              </button>
            </div>

            {error ? (
              <div className="mt-5 flex gap-3 rounded-[8px] border border-coral/30 bg-coral/10 p-4 text-sm leading-6 text-clay">
                <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            ) : null}

            <div className="mt-5 rounded-[8px] border border-pollen/45 bg-white/58 p-4 text-sm leading-6 text-mineral">
              建议使用自然光、掌心平展、背景干净的照片；报告只描述图像视觉特征。
            </div>
          </section>

          <ReportView report={report} />
        </div>
      </div>
    </main>
  );
}
