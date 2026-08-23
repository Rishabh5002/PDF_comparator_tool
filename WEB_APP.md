# FormDiff Web Application (React + Python Backend)

## Architecture

- **Frontend**: React + Vite (located in `frontend/`)
- **Backend**: FastAPI + Uvicorn (located in `backend/` and launched via `run_local.py`)
- **Engine**: PyMuPDF + deterministic local matching core

---

## Quick Start (Production / Single Server)

1. Build the React frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. Run the local server:
   ```bash
   python run_local.py
   ```

3. Open:
   `http://127.0.0.1:8000`

---

## Development Mode

Run backend and frontend independently with hot reloading:

1. **Start Backend API** (Port 8000):
   ```bash
   python run_local.py
   ```

2. **Start Vite React Dev Server** (Port 5173):
   ```bash
   cd frontend
   npm run dev
   ```

3. Open:
   `http://localhost:5173` (requests to `/api/*` are automatically proxied to backend at `http://127.0.0.1:8000`).

---

## Features

- **Local & Offline**: All processing is strictly local.
- **Dual PDF Drag & Drop**: Drop original and revised PDFs, with encrypted PDF password support.
- **Adjustable Match Confidence**: Interactive threshold slider.
- **Dedicated Results View**:
  - **Detected Differences Tab**: Searchable and filterable (Added, Removed, Modified) with side-by-side diff views.
  - **Question Alignment Tab**: Side-by-side question comparison with match confidence signals breakdown.
  - **Overview & Details Tab**: Document metadata, change counts, and offline verification status.
  - **Multi-format Exports**: Download reports in JSON, HTML, PDF, and Excel.
  - **Dark / Light Theme**: Seamless toggle with persistent preference.
