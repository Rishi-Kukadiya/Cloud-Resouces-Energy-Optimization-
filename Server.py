from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import threading
import uvicorn
from datetime import datetime
from CloudeServer import mgr, traffic_generator, cluster_monitor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. ENHANCED WEBSOCKET (All Metrics)
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

            # Send full telemetry for every node (Active or Sleeping)
            for node_id, history in mgr.historian.node_history.items():
                if history:
                    combined_data["nodes"][node_id] = history[-1]

            await websocket.send_json(combined_data)
            await asyncio.sleep(1) 
            
    except WebSocketDisconnect:
        print("[WS] Admin Dashboard Disconnected")

# ==========================================
# 2. ANALYSIS API (Individual Node Deep-Dive)
# ==========================================
@app.get("/api/node/{node_id}/telemetry")
async def get_detailed_node_stats(node_id: str):
    """
    Returns the last 100 steps of ALL metrics for a specific node.
    Used for the per-server dashboard graphs.
    """
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
# 3. LIFECYCLE MANAGEMENT
# ==========================================
@app.on_event("startup")
async def startup_event():
    print("[API] Initializing Simulation...")
    if not mgr.nodes: mgr.provision_node("Master_Node")
    
    threading.Thread(target=mgr.predictive_scale_logic, daemon=True).start()
    threading.Thread(target=mgr.data_collection_loop, daemon=True).start()
    threading.Thread(target=traffic_generator, args=(mgr,), daemon=True).start()
    threading.Thread(target=cluster_monitor, args=(mgr,), daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)