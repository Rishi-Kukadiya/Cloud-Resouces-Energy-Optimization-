# AI-Driven Green Cloud Orchestrator

A full-stack prototype that simulates a cloud compute cluster, forecasts energy consumption using a hybrid ML model, and dynamically scales virtual nodes to minimize wasted power. The project includes data preprocessing, model training, a FastAPI backend with real-time WebSocket telemetry, and a React dashboard for monitoring.

---

## 🚀 What This Project Does

- **Simulates virtual server nodes** (`CloudServer.py`) that generate CPU, memory, disk, and network telemetry.
- **Predicts real-time power usage** using a hybrid ML architecture (Random Forest + LSTM + meta-learner).
- **Automatically scales** the simulated cluster up/down based on predicted power demand.
- **Provides a live frontend dashboard** (React + Vite) visualizing per-node metrics, energy savings, and CO₂ offset.
- **Allows external traffic injection** via a REST endpoint (`/api/ingest`) or through a simple built-in mobile-friendly controller UI (`/admin/controller`).

---

## 🧭 Architecture Overview

### 1) Data Processing + Model Training

- **`dataClean.py`**: Loads raw telemetry CSV(s), computes a synthetic energy consumption label, adds lag features, and writes `processed_cloud_data.csv`.
- **`Traning_Pipline.py`**: Reads `processed_cloud_data.csv`, splits into train/test, scales features, trains:
  - Random Forest regressor
  - LSTM time-series regressor
  - Meta-learner (linear regression) that blends RF + LSTM outputs
  It then exports models to `models/` and produces evaluation artifacts (`model_evaluation_matrix.csv`, charts).
- **`analisys.py`**: Generates exploratory visualizations (correlation matrix, lag/autocorrelation plots) using the processed data.

### 2) Simulation + Prediction Engine

- **`CloudeServer.py`** contains the core simulation logic:
  - `CloudServerNode` (threaded virtual node) simulates telemetry and processes artificial packets to raise CPU load.
  - `MLPredictor` loads pre-trained models from `models/` and predicts energy consumption using telemetry.
  - `AdminHistorian` records per-node telemetry history and tracks energy savings/waste.
  - `PredictiveClusterManager` provisions/de-provisions nodes automatically based on forecasted power demand.
  - `traffic_generator()` (optional) can simulate extra load spikes.

### 3) API + Real-Time WebSocket Backend

- **`Server.py`** runs a FastAPI service that:
  - Exposes `/api/ingest` to accept external workload packets (JSON) and route them to the least-loaded node.
  - Serves `/ws/dashboard` as a WebSocket endpoint that streams live telemetry to the React dashboard.
  - Provides historical metrics via `/api/node/{node_id}/telemetry` and `/api/summary`.
  - Hosts a simple mobile-friendly controller at `/admin/controller` to trigger workloads from a phone.

### 4) Frontend Dashboard

Located inside `Frontend/`.
- React + Vite dashboard that connects to the backend via WebSocket and REST.
- Displays:
  - Global metrics (energy saved, CO₂ offset, active nodes)
  - Node cards with live CPU/energy stats
  - Drill-down view per node with trend charts

---

## ▶️ Quick Start (Run Locally)

### 1) Backend (Python)

1. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install fastapi uvicorn pandas numpy scikit-learn tensorflow joblib matplotlib seaborn
   ```

3. Run the backend server:
   ```bash
   python Server.py
   ```

   - Server listens on `http://localhost:8000`
   - WebSocket dashboard endpoint: `ws://localhost:8000/ws/dashboard`


### 2) Frontend (React + Vite)

1. Install Node dependencies:
   ```bash
   cd Frontend
   npm install
   ```

2. Start the dev server:
   ```bash
   npm run dev
   ```

3. Open the dashboard in a browser (usually `http://localhost:5173`).

> 💡 If the backend and frontend run on different ports, adjust `API_BASE_URL` and `WS_URL` in `Frontend/src/App.jsx`.

---

## 🔧 Files & Folder Guide

### Top-level
- `Server.py` – FastAPI server and WebSocket broadcaster.
- `CloudeServer.py` – Simulation engine + auto scaling logic.
- `dataClean.py` – Data preprocessing and feature engineering.
- `Traning_Pipline.py` – Model training pipeline (RF + LSTM + meta-learner).
- `analisys.py` – Quick plotting scripts for data exploration.
- `processed_cloud_data.csv` – Cleaned dataset used for training.
- `model_evaluation_matrix.csv` – Evaluation metrics output by the training pipeline.

### Models
- `models/` contains trained model artifacts that the engine uses:
  - `scaler.pkl` – feature scaler
  - `rf_model.joblib` – Random Forest regressor
  - `lstm_model.h5` – LSTM neural network
  - `meta_learner.joblib` – stacking model that blends RF + LSTM

### Frontend
- `Frontend/src/App.jsx` – Single-page dashboard and WebSocket client.
- `Frontend/src/App.css` – UI styling.
- `Frontend/package.json` – Frontend dependencies/scripts.

---

## 🧪 How to Retrain Models

1. Prepare data by running the preprocessing script:
   ```bash
   python dataClean.py
   ```

2. Train and save models:
   ```bash
   python Traning_Pipline.py
   ```

3. Start the server (`python Server.py`) and confirm the `models/` folder contains updated model artifacts.

---

## 🔍 How to Use the System

### Send workload (API)

- POST to `http://localhost:8000/api/ingest` with JSON such as:
  ```json
  {
    "packet_size": 2000,
    "complexity": 5
  }
  ```

### Use the built-in mobile controller

- Open `http://localhost:8000/admin/controller` in a phone browser.
- Tap the buttons to send normal or burst traffic.

### Visualize live metrics

- Open the React dashboard (default `http://localhost:5173`) to view live telemetry and energy savings.

---

## 🧩 Customization Ideas

- Swap the energy model with real telemetry data from a cloud provider.
- Improve scaling logic: incorporate hysteresis, minimum uptime, or cost-aware decisions.
- Add authentication / rate-limiting to the service API.
- Extend the dashboard with alerting, node grouping, or a cluster view.

---

## 📌 Notes / Gotchas

- The simulation uses randomized values to mimic I/O and network traffic.
- The cluster manager uses a simple rule-based scaling algorithm; it is meant as a demo, not a production autoscaler.
- The project assumes the trained models exist under `models/` (the repository includes them). If you delete them, re-run `Traning_Pipline.py`.
