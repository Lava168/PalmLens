# PalmLens Local Docker Deployment Guide

> This document is an English step-by-step guide to help you deploy and experience all features of PalmLens locally using Docker.
>
> **Estimated time:** 10–15 minutes (depending on network and hardware)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Docker Container Deployment](#2-docker-container-deployment)
3. [Verifying the Services](#3-verifying-the-services)
4. [Full Feature Walkthrough](#4-full-feature-walkthrough)
5. [Docker Management Commands](#5-docker-management-commands)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites

### 1.1 Install Docker Desktop

If you don't have Docker Desktop yet, please install it first:

1. Visit [Docker's official website](https://www.docker.com/products/docker-desktop/) to download Docker Desktop
2. After installation, launch Docker Desktop (administrator privileges may be required on Windows)
3. Wait until the Docker Engine status turns green "Running"

### 1.2 Verify Docker Environment

Open a terminal (CMD or PowerShell) and run:

```bash
docker --version
docker compose version
```

If version numbers are returned, the environment is ready.

### 1.3 Get the Project Code

```bash
# If you haven't cloned the project yet
git clone https://github.com/YOUR_USERNAME/PalmLens.git
cd PalmLens
```

Or open the `PalmLens` folder directly in VS Code.

---

## 2. Docker Container Deployment

### 2.1 Project Structure Overview

All Docker configuration files are ready in the project:

```
PalmLens/
├── docker-compose.yml         # Docker Compose orchestration file
├── backend/
│   ├── Dockerfile             # Backend image build file
│   └── app/                   # FastAPI source code
├── frontend/
│   ├── Dockerfile             # Frontend image build file
│   ├── next.config.mjs        # Configured with standalone output mode
│   └── src/                   # Next.js source code
```

### 2.2 One-Command Build and Start

Run the following command from the project root:

```bash
docker compose up -d --build
```

This command will:

1. **Build the backend image** (`palmlens-backend`):
   - Based on `python:3.11-slim`
   - Installs OpenCV, NumPy, MediaPipe, and other dependencies
   - Automatically starts FastAPI service on port `8000`

2. **Build the frontend image** (`palmlens-frontend`):
   - Based on `node:22-alpine`
   - Uses Next.js standalone output mode for an optimized production build
   - Automatically starts Next.js service on port `3000`

3. **Start both containers** and create the internal network `palmlens-network`

### 2.3 Check Container Status

```bash
docker compose ps
```

Expected output:

```
NAME                IMAGE               SERVICE     STATUS        PORTS
palmlens-api        palmlens-backend    backend     Up (healthy)  0.0.0.0:8000->8000/tcp
palmlens-frontend   palmlens-frontend   frontend    Up            0.0.0.0:3000->3000/tcp
```

- ✅ `STATUS` shows `Up (healthy)` → backend health check passed
- ✅ `PORTS` shows successful port mapping

### 2.4 View Live Logs

```bash
# View logs of all services
docker compose logs -f

# View only backend logs
docker compose logs -f backend

# View only frontend logs
docker compose logs -f frontend
```

Press `Ctrl+C` to exit log following.

---

## 3. Verifying the Services

### 3.1 Backend Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"PalmLens API","scope":"visual-analysis-only"}
```

### 3.2 Frontend Page Access

Open your browser and visit: **[http://localhost:3000](http://localhost:3000)**

You should see the PalmLens interface:
- Title: "PalmLens — 基于手掌图像的健康科普提示网站"
- Left side: upload area with "上传手掌照片" placeholder
- Right side: "等待分析" placeholder image

### 3.3 API Endpoint Test

Test the analysis endpoint with the sample image:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@frontend/public/palm-lens-art.png"
```

A successful response includes the following data:

| Category | Content |
|----------|---------|
| Image info | Detection method (MediaPipe Hands or OpenCV skin segmentation), confidence, three analysis images (overlay, line-enhanced, red heatmap) |
| Color metrics | Hue, brightness, saturation, redness index, color tone |
| Redness metrics | Red area ratio, largest patch ratio, patch count, attention level |
| Line metrics | Edge density, contrast score, clarity level |
| Health suggestions | Attention level, score breakdown (redness/yellowness/paleness/lighting), color explanation, texture explanation, recheck plan, consult-doctor-if list |
| Palmistry | Archetype, keywords, four line cards (with visual basis and entertainment copy) |

---

## 4. Full Feature Walkthrough

Follow the steps below to experience all features and highlights described in the README.

### 4.1 Step 1: Upload a Palm Photo

1. Open your browser and visit **[http://localhost:3000](http://localhost:3000)**
2. Click the upload area and select a palm photo (JPG, PNG, WebP supported, max 8 MB)
3. **Or** simply drag and drop an image onto the upload area
4. After upload, the page displays:
   - ✅ **Image preview** — your uploaded photo shown on the left
   - ✅ File name and size information
   - ✅ "生成视觉报告" button becomes enabled

**Highlight experience:** Automatic palm ROI detection — the backend identifies the palm region.

### 4.2 Step 2: Generate the Visual Report

1. Click **"生成视觉报告"** button
2. Wait a few seconds (the backend processes and analyzes the image)
3. The report area on the right automatically displays the analysis results

### 4.3 Step 3: Read the Health Analysis Report

The report includes the following sections (project highlights ✨):

#### Analysis Images
- ✅ **Overlay image** — Shows palm detection ROI, landmarks, and red area annotations
- ✅ **Line-enhanced image** — Enhanced palm crease visualization
- ✅ **Red heatmap** — Distribution heatmap of red areas

#### Metric Scores (shown as progress bars)
- ✅ **Detection reference** — Confidence score of the detection method
- ✅ **Palm area ratio** — Proportion of the palm region in the frame
- ✅ **Brightness** — Average brightness value
- ✅ **Redness index** — Quantified redness score
- ✅ **Redness area** — Red area ratio
- ✅ **Line score** — Palm crease clarity score

#### Health Summary
- ✅ **Summary** — A comprehensive overview of the health analysis
- ✅ **Quality notes** — Text explanation of image quality

#### Visual Attention Level
- ✅ Generates **low / medium / high / uncertain** level based on redness, yellowness, paleness, and image quality
- ✅ Color-coded indicators

#### Color & Texture Breakdown
- ✅ **Redness score** — Estimated from red dominance, red area ratio, and saturation
- ✅ **Yellowness score** — Estimated from hue, saturation, and warm color tendency
- ✅ **Paleness score** — Estimated from high brightness and low saturation
- ✅ **Redness explanation** — Description of red visual features in the photo
- ✅ **Texture explanation** — Palm crease clarity assessment

#### Recheck Plan
- ✅ Provides specific re-photography advice (lighting, time intervals, etc.)

#### Consult a Doctor If
- ✅ Clearly lists symptoms that warrant medical consultation

#### Observations & Educational Tips
- ✅ **Health科普 tips** — Educational explanation of visual features
- ✅ **Non-diagnostic disclaimer** — Tags at top: "视觉观察 · 非诊断"
- ✅ Full disclaimer at the bottom

#### Lifestyle Advice
- ✅ Generates re-photography tips, observation advice, and daily routine suggestions based on image quality and palm color

### 4.4 Step 4: Switch to Palmistry Mode

1. Find the **"趣味手相"** tab at the top-right of the report
2. Click to switch — the page shows palmistry reading cards:

#### Project Highlights ✨
- ✅ **Archetype** — Entertainment label such as "热感表达型" (Warm Expressive Type)
- ✅ **Keyword tags** — e.g., "直觉留白·轻盈调整·行动感" (Intuition, Lightness, Action)
- ✅ **Life line** — Entertainment reading based on palm crease clarity
- ✅ **Wisdom line** — Fun description based on edge density and contrast
- ✅ **Heart line** — Entertainment analysis combining palm area ratio and color atmosphere
- ✅ **Career line** — Fun speculation from comprehensive visual features
- ✅ **Visual basis per line** — Explains which image metrics feed into each entertainment card
- ✅ **Entertainment copy advice per line** — Shareable status quotes
- ✅ **Relationship / work rhythm / daily rhythm cards** — Additional entertainment dimensions
- ✅ **Photo tips** — Palmistry-optimized photography suggestions
- ✅ **Share copy** — Pre-written social sharing text
- ✅ **Disclaimer** — "手相解读模块仅基于掌纹视觉特征生成娱乐化文本..."

3. Click **"健康分析"** to switch back to health analysis mode

### 4.5 Step 5: Test Error Tolerance with Suboptimal Images

Intentionally upload the following types of images to test the system's resilience:

- **Non-palm images** (e.g., landscapes, objects) → Shows error: "未检测到足够清晰的手掌区域..."
- **Blurry images** → Shows image quality notes
- **Very dark images** → Color analysis shows "光线偏暗"
- **Invalid files** → Shows corresponding error message

**Highlight experience:** The system uses MediaPipe Hands by default and automatically falls back to OpenCV skin segmentation when unavailable.

### 4.6 Step 6: Reset and Re-analyze

- Click the **reset button (circular arrow icon)** at the top-left to clear the current image and report
- Upload a new image and analyze again

---

## 5. Docker Management Commands

### Start / Stop Services

```bash
# Start all services (background)
docker compose up -d

# Stop all services
docker compose down

# Restart all services
docker compose restart
```

### Check Status

```bash
# Check container status
docker compose ps

# Check resource usage
docker stats palmlens-api palmlens-frontend
```

### View Logs

```bash
# Follow live logs from all services
docker compose logs -f

# View last 100 lines of logs
docker compose logs --tail=100
```

### Rebuild

```bash
# Rebuild and restart after code changes
docker compose up -d --build

# Force rebuild (no cache)
docker compose build --no-cache
```

### Access Container Internals

```bash
# Enter backend container
docker exec -it palmlens-api /bin/sh

# Enter frontend container
docker exec -it palmlens-frontend /bin/sh
```

---

## 6. Troubleshooting

### Issue 1: Docker Engine Not Running

```
error during connect: this error may indicate that the docker daemon is not running
```

**Solution:** Start Docker Desktop and wait until the engine status turns "Running".

### Issue 2: Port Already Allocated

```
port is already allocated
```

**Solution:** Check if other programs are using ports 8000 or 3000:

```bash
# Windows
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# macOS / Linux
lsof -i :8000
lsof -i :3000
```

Modify the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Map host 8001 to container 8000
```

### Issue 3: Backend Health Check Fails

If `docker compose ps` shows the backend status as `unhealthy`:

```bash
# Check backend logs
docker compose logs backend
```

Common cause: MediaPipe may have compatibility issues on some CPUs — the code handles this automatically by falling back to OpenCV.

### Issue 4: Frontend Cannot Connect to Backend

If the frontend loads but analysis fails:

1. Verify the backend container is running: `docker compose ps`
2. Check environment variable: `docker compose exec frontend env | grep NEXT_PUBLIC_API_URL`
3. Default should be `http://127.0.0.1:8000`

To modify, edit `docker-compose.yml`:

```yaml
environment:
  - NEXT_PUBLIC_API_URL=http://your-backend-address:8000
```

Then rebuild:

```bash
docker compose up -d --build frontend
```

### Issue 5: Analysis Timeout

If clicking "生成视觉报告" takes too long:

- The image may be too large (over 8 MB)
- MediaPipe's first load may be slow — try again
- The frontend has a default timeout of 45 seconds

---

## Appendix: Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend Framework | Next.js | 15.5 |
| UI Framework | React | 19 |
| Styling | Tailwind CSS | 3.4 |
| Backend Framework | FastAPI | 0.115 |
| Image Processing | OpenCV | 4.10 |
| Numerical Computing | NumPy | 1.26 |
| Hand Detection | MediaPipe | 0.10 |
| Containerization | Docker + Compose | - |

---

> **Important notice:** PalmLens only analyzes visual features from the photo and provides health科普 tips. It does NOT constitute medical diagnosis, disease screening, treatment advice, or medication recommendations. The palmistry module is for entertainment purposes only. If you experience persistent discomfort, please consult a qualified healthcare professional.

---

*Document generated: 2026-06-04*