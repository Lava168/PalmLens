# PalmLens

PalmLens 是一个基于手掌图像的视觉特征分析网站：上传一张手掌照片，前端展示原图预览，后端使用 FastAPI、OpenCV、NumPy 和 MediaPipe Hands 优先定位手掌区域，并返回掌心颜色、掌纹清晰度、局部发红颜色分布等视觉特征分析。

重要边界：PalmLens 只输出图像视觉观察和健康科普提示，不提供医学诊断、疾病筛查、治疗建议或用药建议，也不能替代医生判断。

## 功能

- 前端上传 JPG、PNG、WebP 手掌图片，限制 8MB。
- 页面显示上传原图预览。
- 后端 `/analyze` 接收图片并返回 JSON 报告。
- 页面显示分析分数：检测参考、掌心占比、画面亮度、发红指数、发红占比、掌纹评分。
- 页面显示三张分析图：综合叠加图、掌纹增强图、红色热力图。
- 页面显示健康科普提示文案，并明确非诊断边界。
- 后端优先使用 MediaPipe Hands；不可用或未检测到手时，自动使用 OpenCV 肤色分割兜底。

## 技术栈

```text
frontend/  Next.js + React + Tailwind CSS
backend/   Python FastAPI + OpenCV + NumPy + MediaPipe
scripts/   项目视觉资产生成脚本
```

## 运行后端

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

## 运行前端

```bash
cd frontend
npm install
npm run dev
```

默认前端会请求 `http://127.0.0.1:8000`。如果后端地址不同，在 `frontend/.env.local` 中设置：

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:3000
```

如果 macOS 阻止 Next.js 加载原生 SWC 二进制，可使用已声明的 wasm fallback：

```bash
cd frontend
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run build
NEXT_TEST_WASM_DIR="$(pwd)/node_modules/@next/swc-wasm-nodejs" npm run dev
```

## 本地验证

后端测试：

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests
```

前端生产构建：

```bash
cd frontend
npm run lint
npm run build
```

## 正式部署

建议把前端和后端分开部署：

- 前端：Vercel，Root Directory 设置为 `frontend`。
- 后端：Render，使用仓库根目录下的 `render.yaml` 和 `backend/Dockerfile` 部署 FastAPI API。

### 部署后端到 Render

1. 在 Render 创建 Blueprint 或 Web Service，并连接本仓库。
2. 如果使用 Blueprint，Render 会读取仓库根目录的 `render.yaml`。
3. 如果手动创建 Web Service：
   - Root Directory：`backend`
   - Runtime：Docker
   - Health Check Path：`/health`
4. 部署完成后，记录后端 URL，例如：

```text
https://palmlens-api.onrender.com
```

### 部署前端到 Vercel

1. 在 Vercel 导入本仓库。
2. Root Directory 设置为 `frontend`。
3. Framework Preset 选择 Next.js。
4. 添加环境变量：

```bash
NEXT_PUBLIC_API_URL=https://你的-render-后端地址
```

5. 部署完成后，记录前端 URL，例如：

```text
https://palmlens.vercel.app
```

### 配置线上 CORS

把 Vercel 前端 URL 添加到 Render 后端环境变量：

```bash
ALLOWED_ORIGINS=https://你的-vercel-前端地址
```

如果有多个前端域名，用英文逗号分隔：

```bash
ALLOWED_ORIGINS=https://palmlens.vercel.app,https://www.example.com
```

配置后重新部署后端。`ALLOWED_ORIGINS` 不需要包含本地地址，后端默认已经允许 `http://localhost:3000` 和 `http://127.0.0.1:3000`。

## 报告内容

报告只包含以下非诊断信息：

- 手掌区域：检测方法、置信参考值、掌心画面占比。
- 掌心色彩：平均亮度、饱和度、色彩倾向、发红指数。
- 局部发红：红色高饱和像素占比、较大色块占比、色块数量。
- 掌纹清晰度：边缘密度、局部对比分数、掌纹可见程度。
- 图像质量提示：光线、白平衡、锐度、按压和拍摄环境可能影响结果。
- 健康科普提示：只提醒用户如何理解图像特征；如果现实中持续不适，建议咨询专业医生。

## 上传到 GitHub

```bash
git init
git add .gitignore README.md backend frontend scripts
git commit -m "Initial PalmLens"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/PalmLens.git
git push -u origin main
```

上传前建议确认 `.gitignore` 已排除这些本地文件夹：`node_modules/`、`.next/`、`.venv/`、`.tools/`、`.home/`、`__pycache__/`。

## 后续方向

如果要训练更具体的红色区域检测模型，可以接入 Ultralytics YOLO 的自定义数据训练流程，把检测框或分割结果作为后端的一个可选分析器。上线前仍需保留非诊断边界声明，并避免把视觉特征直接解释为疾病结论。
