from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # For data validation
import asyncio
import threading
import uvicorn
import random
from fastapi.responses import HTMLResponse
from datetime import datetime
from CloudeServer import mgr, traffic_generator, cluster_monitor

app = FastAPI()

# Enable CORS for your React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NEW: Schema for External Client Packets ---
class ExternalPacket(BaseModel):
    packet_size: int
    complexity: int
    target_node: str = None  # Optional: Client can request a specific node


@app.get("/admin/controller", response_class=HTMLResponse)
async def get_mobile_controller():
    """ 
    This HTML is served directly to any phone that scans your QR code.
    It allows remote triggering of workloads.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cloud Load Trigger</title>
        <style>
            body { font-family: -apple-system, sans-serif; background: #0f172a; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 30px; border-radius: 20px; border: 1px solid #334155; width: 80%; max-width: 400px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
            h1 { font-size: 1.5rem; margin-bottom: 20px; color: #3b82f6; }
            button { background: #3b82f6; color: white; border: none; padding: 15px; width: 100%; border-radius: 12px; font-size: 1.1rem; font-weight: bold; margin: 10px 0; active: transform: scale(0.98); transition: 0.2s; }
            .burst { background: #ef4444; }
            #status { margin-top: 15px; font-size: 0.9rem; color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Cloud Orchestrator</h1>
            <p style="font-size: 0.8rem; color: #64748b;">Tap to send workload from your device to the AI Cluster</p>
            <button onclick="sendWork(2000, 5)">⚡ Normal Traffic</button>
            <button onclick="sendWork(8000, 25)" class="burst">🔥 Peak Burst Load</button>
            <div id="status">System Ready</div>
        </div>
        <script>
            function sendWork(size, comp) {
                const status = document.getElementById('status');
                status.innerText = "Transmitting Packet...";
                fetch('/api/ingest', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({packet_size: size, complexity: comp})
                })
                .then(res => res.json())
                .then(data => { 
                    status.innerText = "Success! Processed by: " + data.processed_by;
                    status.style.color = "#10b981";
                })
                .catch(err => { 
                    status.innerText = "Connection Failed"; 
                    status.style.color = "#ef4444";
                });
            }
        </script>
    </body>
    </html>
    """
# ==========================================
# 1. EXTERNAL INGESTION API (The "User" Entry)
# ==========================================
@app.post("/api/ingest")
async def ingest_external_workload(packet: ExternalPacket):
    """
    This is the endpoint your ngrok URL will point to.
    Example: https://your-url.ngrok-free.app/api/ingest
    """
    if not mgr.nodes:
        return {"status": "error", "message": "No active nodes available"}

    # Load Balancer: If no node specified, pick the one with lowest CPU
    target_id = packet.target_node
    if not target_id or target_id not in mgr.nodes:
        target_id = min(mgr.nodes, key=lambda k: mgr.nodes[k].cpu_usage)

    # Inject the packet into our Virtual OS Node
    mgr.nodes[target_id].process_packet(packet.packet_size, packet.complexity)
    
    print(f"[NETWORK] External Packet Injected -> {target_id} | CPU: {mgr.nodes[target_id].cpu_usage}%")
    
    return {
        "status": "success",
        "processed_by": target_id,
        "current_node_load": round(mgr.nodes[target_id].cpu_usage, 2)
    }

# ==========================================
# 2. LIVE WEBSOCKET BROADCASTER (For Frontend)
# ==========================================
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Admin Dashboard Connected")
    try:
        while True:
            if not mgr.historian.node_history:
                await websocket.send_json({"status": "waiting", "nodes": {}})
                await asyncio.sleep(1)
                continue

            combined_data = {
                "timestamp": datetime.now().strftime('%H:%M:%S'),
                "nodes": {},
                "global_metrics": {
                    "total_saved_energy": round(mgr.historian.total_saved_energy, 4),
                    "total_wasted_energy": round(mgr.historian.total_wasted_energy, 4),
                    "co2_offset": round(mgr.historian.total_saved_energy * 0.475, 4),
                    "active_nodes_count": len(mgr.nodes)
                }
            }

            for node_id, history in mgr.historian.node_history.items():
                if history:
                    combined_data["nodes"][node_id] = history[-1]

            await websocket.send_json(combined_data)
            await asyncio.sleep(1) 
            
    except WebSocketDisconnect:
        print("[WS] Admin Dashboard Disconnected")

# ==========================================
# 3. ANALYSIS APIs (For Graphs)
# ==========================================
@app.get("/api/node/{node_id}/telemetry")
async def get_detailed_node_stats(node_id: str):
    if node_id in mgr.historian.node_history:
        history = list(mgr.historian.node_history[node_id])
        return {
            "node_id": node_id,
            "cpu_history": [h["cpu"] for h in history],
            "mem_history": [h["mem"] for h in history],
            "io_history": [h["disk_io"] for h in history],
            "net_history": [h["network"] for h in history],
            "power_history": [h["actual_w"] for h in history],
            "timestamps": [h["timestamp"] for h in history]
        }
    return {"error": "Node not found"}

@app.get("/api/summary")
async def get_project_summary():
    return {
        "energy_saved_wh": round(mgr.historian.total_saved_energy, 2),
        "energy_wasted_wh": round(mgr.historian.total_wasted_energy, 2),
        "co2_offset_kg": round(mgr.historian.total_saved_energy * 0.475, 4),
        "active_nodes": list(mgr.nodes.keys()),
        "sleeping_nodes": mgr.available_ids
    }

# ==========================================
# 4. LIFECYCLE MANAGEMENT
# ==========================================
@app.on_event("startup")
async def startup_event():
    print("[API] Initializing Predictive Simulation...")
    if not mgr.nodes: 
        mgr.provision_node("Master_Node")
    
    # 1. Background Logic & Monitoring
    threading.Thread(target=mgr.predictive_scale_logic, daemon=True).start()
    threading.Thread(target=mgr.data_collection_loop, daemon=True).start()
    threading.Thread(target=cluster_monitor, args=(mgr,), daemon=True).start()

    # 2. INTERNAL TRAFFIC GENERATOR (COMMENTED OUT)
    # we turn this OFF so we can use external phones/laptops instead!
    # threading.Thread(target=traffic_generator, args=(mgr,), daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)