# PalmLens 本地 Docker 部署与体验完整操作指南

> 本文档为中文操作步骤指南，帮助你使用 Docker 在本地完整部署并体验 PalmLens 的所有功能。
>
> **操作时间预估：** 10-15 分钟（取决于网络和硬件性能）

---

## 目录

1. [前置准备](#1-前置准备)
2. [Docker 容器部署](#2-docker-容器部署)
3. [验证服务正常运行](#3-验证服务正常运行)
4. [完整功能体验](#4-完整功能体验)
5. [Docker 常用管理命令](#5-docker-常用管理命令)
6. [常见问题与排查](#6-常见问题与排查)

---

## 1. 前置准备

### 1.1 安装 Docker Desktop

如果你还没有 Docker Desktop，请先安装：

1. 访问 [Docker 官网](https://www.docker.com/products/docker-desktop/) 下载 Docker Desktop
2. 安装完成后启动 Docker Desktop（Windows 下可能需要管理员权限）
3. 等待 Docker Engine 状态变为绿色 "Running"

### 1.2 验证 Docker 环境

打开终端（CMD 或 PowerShell），运行：

```bash
docker --version
docker compose version
```

若正常返回版本号，说明环境就绪。

### 1.3 获取项目代码

```bash
# 如果你还没有克隆项目
git clone https://github.com/YOUR_USERNAME/PalmLens.git
cd PalmLens
```

或者直接在 VS Code 中打开项目文件夹 `PalmLens`。

---

## 2. Docker 容器部署

### 2.1 项目结构概览

项目已经为你准备好了所有 Docker 配置文件：

```
PalmLens/
├── docker-compose.yml         # Docker Compose 编排文件
├── backend/
│   ├── Dockerfile             # 后端镜像构建文件
│   └── app/                   # FastAPI 源代码
├── frontend/
│   ├── Dockerfile             # 前端镜像构建文件
│   ├── next.config.mjs        # 已配置 standalone 输出模式
│   └── src/                   # Next.js 源代码
```

### 2.2 一键构建并启动

在项目根目录执行：

```bash
docker compose up -d --build
```

这个命令会：

1. **构建后端镜像**（`palmlens-backend`）：
   - 基于 `python:3.11-slim`
   - 安装 OpenCV、NumPy、MediaPipe 等依赖
   - 自动启动 FastAPI 服务，监听 `8000` 端口

2. **构建前端镜像**（`palmlens-frontend`）：
   - 基于 `node:22-alpine`
   - 使用 Next.js standalone 输出模式，生成优化生产版本
   - 自动启动 Next.js 服务，监听 `3000` 端口

3. **启动两个容器**，并建立内部网络 `palmlens-network`

### 2.3 查看容器状态

```bash
docker compose ps
```

预期输出：

```
NAME                IMAGE               SERVICE     STATUS        PORTS
palmlens-api        palmlens-backend    backend     Up (healthy)  0.0.0.0:8000->8000/tcp
palmlens-frontend   palmlens-frontend   frontend    Up            0.0.0.0:3000->3000/tcp
```

- ✅ `STATUS` 列显示 `Up (healthy)` 表示后端健康检查通过
- ✅ `PORTS` 列显示端口映射成功

### 2.4 查看实时日志

```bash
# 查看所有服务的日志
docker compose logs -f

# 只查看后端日志
docker compose logs -f backend

# 只查看前端日志
docker compose logs -f frontend
```

按 `Ctrl+C` 退出日志跟随。

---

## 3. 验证服务正常运行

### 3.1 后端健康检查

```bash
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{"status":"ok","service":"PalmLens API","scope":"visual-analysis-only"}
```

### 3.2 前端页面访问

在浏览器中打开：**[http://localhost:3000](http://localhost:3000)**

你应该能看到 PalmLens 的界面：
- 标题："PalmLens — 基于手掌图像的健康科普提示网站"
- 左侧有上传区域，显示"上传手掌照片"
- 右侧显示"等待分析"的占位图

### 3.3 API 接口测试

使用项目自带的示例图片测试后端分析接口：

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -F "file=@frontend/public/palm-lens-art.png"
```

正常会返回一个包含以下信息的 JSON 报告：

| 类别 | 内容 |
|------|------|
| 图像信息 | 检测方法（MediaPipe Hands 或 OpenCV 肤色分割）、置信度、三张分析图（综合叠加、掌纹增强、热力图） |
| 掌色指标 | 色调、亮度、饱和度、发红指数、色彩倾向 |
| 发红指标 | 红色占比、较大色块占比、色块数量、关注等级 |
| 掌纹指标 | 边缘密度、对比度评分、清晰度等级 |
| 健康建议 | 视觉关注等级、分数解读（偏红/偏黄/偏淡/图片质量）、颜色说明、纹理说明、复查计划、就医警示 |
| 趣味手相 | 原型归类、关键词、四条线卡片（含视觉依据和娱乐文案） |

---

## 4. 完整功能体验

按照以下步骤，体验 README.md 中描述的所有功能和项目亮点。

### 4.1 步骤一：上传手掌照片

1. 打开浏览器访问 **[http://localhost:3000](http://localhost:3000)**
2. 点击上传区域，选择一张手掌照片（支持 JPG、PNG、WebP 格式，不超过 8MB）
3. **或** 直接将图片拖拽到上传区域
4. 上传后页面显示：
   - ✅ **原图预览** — 左侧区域展示你上传的图片
   - ✅ 文件名和文件大小信息
   - ✅ "生成视觉报告"按钮变为可用

**项目亮点体验：** 手掌 ROI 自动定位 — 后端会自动识别手掌区域。

### 4.2 步骤二：生成视觉报告

1. 点击 **"生成视觉报告"** 按钮
2. 等待几秒钟（后端进行处理和分析）
3. 右侧报告区域会自动展示分析结果

### 4.3 步骤三：阅读健康分析报告

报告会显示以下打分项（项目亮点 ✨）：

#### 分析图区
- ✅ **综合叠加图** — 显示手掌检测框、关键点和红色区域标注
- ✅ **掌纹增强图** — 增强后的掌纹线条可视化
- ✅ **红色热力图** — 红色区域的分布热力图

#### 指标评分（以进度条显示）
- ✅ **检测参考** — 检测方法的置信度评分
- ✅ **掌心占比** — 手掌区域占画面的比例
- ✅ **画面亮度** — 平均亮度值
- ✅ **发红指数** — 红色程度量化评分
- ✅ **发红占比** — 红色区域占比
- ✅ **掌纹评分** — 掌纹清晰度评分

#### 健康分析总览
- ✅ **总览摘要** — 一段综合性的健康分析总结
- ✅ **图片质量解读** — 对照片质量的文字说明

#### 视觉关注等级
- ✅ 根据偏红、偏黄、偏淡和图片质量生成 **低 / 中 / 高 / 不确定** 等级
- ✅ 显示对应的颜色标识

#### 颜色与纹理详细解读
- ✅ **偏红分数** — 红色优势、红色区域占比和饱和度估算
- ✅ **偏黄分数** — 掌心色相、饱和度和暖色倾向估算
- ✅ **偏淡分数** — 亮度偏高、饱和度偏低等特征估算
- ✅ **红色区域解释** — 照片中红色视觉特征的说明
- ✅ **掌纹纹理解读** — 纹理清晰度评估

#### 复查计划
- ✅ 提供具体的复查拍照建议（光照、时间间隔等）

#### 就医警示
- ✅ 明确列出需要咨询医生的症状条件

#### 观察与科普提示
- ✅ **健康科普提示** — 图像视觉特征的科普说明
- ✅ **明确标注"非诊断"边界** — 顶部有"视觉观察 · 非诊断"标签
- ✅ 底部有完整的非诊断声明

#### 生活建议
- ✅ 根据图片质量和掌色视觉特征，生成复拍建议、观察建议、日常作息建议

### 4.4 步骤四：切换趣味手相模式

1. 在报告右上角找到 **"趣味手相"** 选项卡
2. 点击切换，页面显示手相解读卡片：

#### 项目亮点 ✨
- ✅ **原型归类** — 如"热感表达型"等娱乐识别
- ✅ **关键词标签** — 如"直觉留白·轻盈调整·行动感"等
- ✅ **生命线** — 基于掌纹清晰度的娱乐解读
- ✅ **智慧线** — 根据边缘密度和对比度的趣味描述
- ✅ **感情线** — 结合掌心占比和掌色氛围的娱乐分析
- ✅ **事业线** — 综合视觉特征的趣味推测
- ✅ **每条线的视觉依据** — 说明娱乐卡片基于哪些图像数值
- ✅ **每条线的娱乐文案建议** — 适合分享的状态语录
- ✅ **关系/工作/日常节奏卡片** — 更多维度的娱乐解读
- ✅ **拍摄技巧** — 针对手相模式优化的拍照建议
- ✅ **分享文案** — 可直接复制使用的社交分享文本
- ✅ **底部声明** — "手相解读模块仅基于掌纹视觉特征生成娱乐化文本..."

3. 点击 **"健康分析"** 可切回健康分析模式

### 4.5 步骤五：使用不理想图片测试容错

你可以故意上传以下类型的图片来测试系统的容错能力：

- **非手掌图片**（如风景、物体） → 显示错误提示："未检测到足够清晰的手掌区域..."
- **模糊图片** → 显示图像质量提示
- **光线很暗的图片** → 掌色分析显示"光线偏暗"
- **格式错误的文件** → 显示对应的错误提示

**项目亮点体验：** 系统自动使用 MediaPipe Hands 检测，不可用时自动降级到 OpenCV 肤色分割。

### 4.6 步骤六：重置并重新分析

- 点击左上角的 **重置按钮（循环箭头图标）** 可以清除当前图片和报告
- 上传新图片后重新分析

---

## 5. Docker 常用管理命令

### 启动/停止服务

```bash
# 启动所有服务（后台运行）
docker compose up -d

# 停止所有服务
docker compose down

# 重启所有服务
docker compose restart
```

### 查看状态

```bash
# 查看容器状态
docker compose ps

# 查看资源占用
docker stats palmlens-api palmlens-frontend
```

### 日志查看

```bash
# 实时查看所有日志
docker compose logs -f

# 查看最近 100 行日志
docker compose logs --tail=100
```

### 重新构建

```bash
# 修改代码后重新构建并启动
docker compose up -d --build

# 强制重新构建（不使用缓存）
docker compose build --no-cache
```

### 进入容器内部

```bash
# 进入后端容器
docker exec -it palmlens-api /bin/sh

# 进入前端容器
docker exec -it palmlens-frontend /bin/sh
```

---

## 6. 常见问题与排查

### 问题 1：Docker Engine 未运行

```
error during connect: this error may indicate that the docker daemon is not running
```

**解决：** 启动 Docker Desktop，等待引擎状态变为 Running。

### 问题 2：端口被占用

```
port is already allocated
```

**解决：** 检查是否有其他程序占用了 8000 或 3000 端口。

```bash
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3000
```

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8001:8000"  # 将宿主机 8001 映射到容器 8000
```

### 问题 3：后端健康检查失败

如果 `docker compose ps` 显示后端状态为 `unhealthy`：

```bash
# 查看后端日志排查
docker compose logs backend
```

常见原因：MediaPipe 在部分 CPU 上可能有兼容性问题，代码已自动处理（降级到 OpenCV）。

### 问题 4：前端无法连接到后端

如果前端页面打开但分析时出错：

1. 确认后端容器正常运行：`docker compose ps`
2. 检查环境变量：`docker compose exec frontend env | grep NEXT_PUBLIC_API_URL`
3. 默认应显示 `http://127.0.0.1:8000`

如需修改，编辑 `docker-compose.yml`：

```yaml
environment:
  - NEXT_PUBLIC_API_URL=http://你的后端地址:8000
```

然后重新构建：

```bash
docker compose up -d --build frontend
```

### 问题 5：分析超时

如果点击"生成视觉报告"后长时间无响应：

- 可能是图片过大（超过 8MB）
- 可能是 MediaPipe 首次加载较慢，再次尝试即可
- 前端默认超时 45 秒，极复杂的图片可能需要更长时间

---

## 附录：技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | Next.js | 15.5 |
| UI 框架 | React | 19 |
| 样式 | Tailwind CSS | 3.4 |
| 后端框架 | FastAPI | 0.115 |
| 图像处理 | OpenCV | 4.10 |
| 数值计算 | NumPy | 1.26 |
| 手部检测 | MediaPipe | 0.10 |
| 容器化 | Docker + Compose | - |

---

> **重要提醒：** PalmLens 仅分析照片中的视觉特征并给出健康科普提示，不构成医学诊断、疾病筛查、治疗建议或用药建议。趣味手相内容仅供娱乐。如果现实中持续不适，请咨询专业医生。

---

*文档生成日期：2026-06-04*