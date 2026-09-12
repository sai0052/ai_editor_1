# AutoCut — Fast Automatic AI Video Editing

Professional AI-powered video editing, end to end: **Upload → Select options → Auto Edit → Preview → Export.**

---

## ✨ Features

- 🎬 Video upload with automatic metadata detection (duration, resolution, FPS, size)
- 🔇 Background noise reduction (voice-preserving `afftdn`)
- ✂️ Long silence removal (conservative / balanced / aggressive presets)
- 📝 Automatic captions (when a Whisper provider is available) with burn-in styles
- 🎨 Color grading presets, Auto Color, and manual sliders
- 📊 Real, stage-based processing progress with ETA
- 👀 Before / after preview and download
- 🧩 Feature cards for filler-word removal, reframe, jump cuts, and pause trimming (wired; advanced AI hooks ready)

---

## 🧱 Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 + TypeScript + Vite |
| Backend | FastAPI + Python 3.11 |
| Processing | FFmpeg (denoise, silence, color, captions, encode) |
| Jobs | Async in-process workers (swap-ready for Redis/Celery) |
| Captions AI | `faster-whisper` or OpenAI Whisper (pluggable) |

---

## 🏗️ Architecture

```
UPLOAD → ANALYSIS → SELECTED OPS → AUDIO → SILENCE → TRANSCRIBE
      → CAPTIONS → COLOR → REFRAME → RENDER
```

Only enabled stages run. AI providers are abstracted under `backend/app/ai/`.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ (`py -3.11`)
- Node.js 20+
- FFmpeg on PATH

### Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Optional local captions:
# pip install faster-whisper

uvicorn app.main:app --reload --port 8000
```

Or simply run `start-backend.bat` from the repo root.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Or simply run `start-frontend.bat`.

Then open **http://localhost:5173**

### Captions (optional)

Without a transcription provider, noise reduction, silence removal, color grading, reframe, and jump-cuts all still work.

```powershell
pip install faster-whisper
# or set OPENAI_API_KEY and TRANSCRIPTION_PROVIDER=openai
```

---

## 🌐 Production Deployment (`aieditor.website`)

The frontend is deployed on **Vercel** as project **`aieditor`**.

- Temporary URL: https://aieditor-neon.vercel.app
- Custom domains attached: `aieditor.website`, `www.aieditor.website`

### DNS Configuration (GoDaddy / DomainControl)

At your registrar (currently `ns19/ns20.domaincontrol.com`), set:

| Type | Name | Value |
|---|---|---|
| A | `@` | `216.198.79.1` |
| A | `@` | `64.29.17.1` |
| CNAME | `www` | `cname.vercel-dns.com` |

> Alternative single A record: `@` → `76.76.21.21`

After DNS propagates, run:

```bash
vercel domains verify aieditor.website
```

(or wait for Vercel's confirmation email). Once verified, **https://aieditor.website** will serve the editor UI.

> ⚠️ **Important:** Video processing (the FFmpeg backend) cannot run on Vercel. For full Auto Edit functionality, also host the FastAPI backend (e.g. via Docker Compose on a VPS) and point `/api` to it — or run the full stack with Docker.

---.
