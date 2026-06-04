# PalmLens

**[English](#english)** · **[中文](#中文)**

---

<a id="english"></a>

## English

PalmLens is an interactive AI web app for palm photos: upload a palm image, preview it in the browser, and receive a visual analysis report from a FastAPI backend using OpenCV, NumPy, and MediaPipe Hands (with an OpenCV skin-segmentation fallback).

**Important:** PalmLens only describes visual features and general wellness education. It does **not** provide medical diagnosis, disease screening, treatment, or medication advice, and cannot replace a doctor. Palm-reading content is for entertainment only—not for predictions, personality judgment, or life decisions.

### Features

- Upload JPG, PNG, or WebP palm images (max 8 MB).
- In-browser preview of the uploaded photo.
- `POST /analyze` returns a structured JSON report.
- Scores: detection confidence, palm area ratio, brightness, redness index, redness area ratio, palm-line clarity.
- Three visualization images: overlay, enhanced palm lines, red heatmap.
- Non-diagnostic health tips, lifestyle notes, and clear medical boundaries.
- Visual attention level and possible wellness directions (educational only).
- Health mode: overview, image quality, color/redness/texture explanations, recheck plan, when to see a doctor.
- Dual modes: **health analysis** and **entertainment palm reading**.
- Backend prefers MediaPipe Hands; falls back to OpenCV skin segmentation when needed.

### Highlights

- Automatic palm ROI detection.
- Quantified palm color metrics.
- Palm-line enhancement visualization.
- Red-region heatmap.
- Educational wellness direction hints.
- Lifestyle suggestions based on image quality.
- Scores for redness, yellowness, paleness, and lighting quality.
- Health + palmistry dual UI.

### Tech stack

```text
frontend/  Next.js + React + Tailwind CSS
backend/   Python FastAPI + OpenCV + NumPy + MediaPipe
scripts/   Visual asset generation
```

### Run the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Analyze example:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@../frontend/public/palm-lens-art.png"
```

### Run the frontend

```bash
cd frontend
pnpm install   # or: npm install
pnpm dev       # or: npm run dev
```

Default API URL: `http://127.0.0.1:8000`. Override in `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Open `http://127.0.0.1:3000`.

On macOS, if native Next.js SWC fails, use the wasm fallback:

```bash
cd frontend
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run build
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run dev
```

### Local verification

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests
cd frontend && npm run lint && npm run build
```

### Deployment

Deploy frontend and backend separately:

| Part | Platform | Notes |
|------|----------|--------|
| Frontend | Vercel | Root directory: `frontend` |
| Backend | Render | `render.yaml` + `backend/Dockerfile` |

**Render (backend):** connect the repo, use Blueprint (`render.yaml`) or a Docker Web Service with root `backend`, health path `/health`.

**Vercel (frontend):** root `frontend`, framework Next.js, env:

```bash
NEXT_PUBLIC_API_URL=https://your-render-api.onrender.com
```

**CORS on Render:**

```bash
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
```

Comma-separate multiple origins. `localhost:3000` and `127.0.0.1:3000` are allowed by default for local dev.

Live demo (example): https://palmlens.vercel.app

### Report contents (non-diagnostic)

- Palm region: detection method, confidence, palm area ratio.
- Color: brightness, saturation, tone, redness index.
- Local redness: area ratio, largest patch ratio, patch count.
- Palm-line clarity: edge density, contrast, visibility level.
- Image quality notes: lighting, white balance, sharpness, pressure, environment.
- Wellness education only—consult a professional for persistent symptoms.
- Attention level: low / medium / high / uncertain from color and quality scores.
- Recheck plan and color explanations (red / yellow / pale).
- Entertainment palmistry: life, head, heart, and career line cards from visual features.

### Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/PalmLens.git
git push -u origin main
```

Ensure `.gitignore` excludes `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, etc.

### Roadmap

Optional: train a custom red-region detector (e.g. Ultralytics YOLO) as an extra analyzer. Keep non-diagnostic disclaimers and avoid mapping visuals directly to disease conclusions.

---

<a id="中文"></a>

## 中文

PalmLens 是一个基于手掌图像的互动式 AI 网站：上传一张手掌照片，前端展示原图预览，后端使用 FastAPI、OpenCV、NumPy 和 MediaPipe Hands 优先定位手掌区域，并返回掌心颜色、掌纹清晰度、局部红色区域分布等视觉特征分析。

**重要边界：** PalmLens 只输出图像视觉观察和健康科普提示，不提供医学诊断、疾病筛查、治疗建议或用药建议，也不能替代医生判断。趣味手相内容仅供娱乐，不用于预测、判断性格或指导人生决策。

### 功能

- 前端上传 JPG、PNG、WebP 手掌图片，限制 8MB。
- 页面显示上传原图预览。
- 后端 `/analyze` 接收图片并返回 JSON 报告。
- 页面显示分析分数：检测参考、掌心占比、画面亮度、发红指数、发红占比、掌纹评分。
- 页面显示三张分析图：综合叠加图、掌纹增强图、红色热力图。
- 页面显示健康科普提示文案、生活建议，并明确非诊断边界。
- 页面显示视觉关注等级、可能相关健康方向提示和生活建议。
- 健康分析包含总览、图片质量解读、掌色解释、红色区域解释、掌纹纹理解读、复查计划和咨询医生提示条件。
- 页面支持健康分析与趣味手相双模式展示。
- 趣味手相模块会把掌纹视觉特征转化为生命线、智慧线、感情线和事业线等娱乐解读。
- 后端优先使用 MediaPipe Hands；不可用或未检测到手时，自动使用 OpenCV 肤色分割兜底。

### 项目亮点

- 手掌 ROI 自动定位。
- 掌色量化评分。
- 掌纹增强图。
- 红色区域热力图。
- 可能相关健康方向的科普提示。
- 基于图像质量的生活建议。
- 偏红、偏黄、偏淡和图片质量的量化关注分数。
- 健康分析与趣味手相双模式展示。
- 健康内容标注为科普提示，不构成医学诊断；手相内容仅供娱乐。

### 技术栈

```text
frontend/  Next.js + React + Tailwind CSS
backend/   Python FastAPI + OpenCV + NumPy + MediaPipe
scripts/   项目视觉资产生成脚本
```

### 运行后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

接口测试示例：

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@../frontend/public/palm-lens-art.png"
```

### 运行前端

```bash
cd frontend
pnpm install   # 或：npm install
pnpm dev       # 或：npm run dev
```

默认前端会请求 `http://127.0.0.1:8000`。如果后端地址不同，在 `frontend/.env.local` 中设置：

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

打开 `http://127.0.0.1:3000`。

如果 macOS 阻止 Next.js 加载原生 SWC 二进制，可使用 wasm fallback：

```bash
cd frontend
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run build
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run dev
```

### 本地验证

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests
cd frontend && npm run lint && npm run build
```

### 正式部署

建议把前端和后端分开部署：

| 部分 | 平台 | 说明 |
|------|------|------|
| 前端 | Vercel | Root Directory：`frontend` |
| 后端 | Render | 使用 `render.yaml` 与 `backend/Dockerfile` |

**Render 后端：** 连接本仓库，使用 Blueprint 或 Docker Web Service（根目录 `backend`，健康检查 `/health`）。

**Vercel 前端：** 根目录 `frontend`，框架 Next.js，环境变量：

```bash
NEXT_PUBLIC_API_URL=https://你的-render-后端地址
```

**线上 CORS（Render 环境变量）：**

```bash
ALLOWED_ORIGINS=https://你的-vercel-前端地址
```

多个域名用英文逗号分隔。本地 `localhost:3000` 与 `127.0.0.1:3000` 默认已允许。

线上示例：https://palmlens.vercel.app

### 报告内容

报告只包含以下非诊断信息：

- 手掌区域：检测方法、置信参考值、掌心画面占比。
- 掌心色彩：平均亮度、饱和度、色彩倾向、发红指数。
- 局部发红：红色高饱和像素占比、较大色块占比、色块数量。
- 掌纹清晰度：边缘密度、局部对比分数、掌纹可见程度。
- 图像质量提示：光线、白平衡、锐度、按压和拍摄环境可能影响结果。
- 健康科普提示：只提醒用户如何理解图像特征；持续不适请咨询专业医生。
- 视觉关注等级：根据偏红、偏黄、偏淡和图片质量生成低、中、高或不确定等级。
- 图片质量与复查计划、颜色解释、生活建议。
- 趣味手相：生命线、智慧线、感情线、事业线等娱乐卡片。

### 上传到 GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/PalmLens.git
git push -u origin main
```

上传前确认 `.gitignore` 已排除：`node_modules/`、`.next/`、`.venv/`、`__pycache__/` 等。

### 后续方向

可接入 Ultralytics YOLO 等自定义红色区域检测模型作为可选分析器。上线前仍需保留非诊断边界声明，避免把视觉特征直接解释为疾病结论。
