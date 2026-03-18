from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import threading
from datetime import datetime
import uvicorn
from CloudeServer import mgr, traffic_generator, cluster_monitor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. LIVE WEBSOCKET BROADCASTER
# ==========================================
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Admin Dashboard Connected")
    try:
        while True:
            # Safe check: if no nodes, send empty structure
            if not mgr.nodes or not mgr.historian.node_history:
                await websocket.send_json({"status": "waiting", "nodes": {}})
                await asyncio.sleep(1)
                continue

            # 1. Collect the latest step from all active nodes
            # We use list() to prevent "dictionary changed size" errors
            active_ids = list(mgr.nodes.keys())
            
            combined_data = {
                "timestamp": datetime.now().strftime('%H:%M:%S'),
                "nodes": {},
                "global_metrics": {
                    "total_saved_energy": round(mgr.historian.total_saved_energy, 4),
                    "total_wasted_energy": round(mgr.historian.total_wasted_energy, 4),
                    "active_nodes_count": len(mgr.nodes)
                }
            }

            for node_id in active_ids:
                history_deque = mgr.historian.node_history.get(node_id)
                if history_deque and len(history_deque) > 0:
                    combined_data["nodes"][node_id] = history_deque[-1]

            await websocket.send_json(combined_data)
            await asyncio.sleep(1) 
            
    except WebSocketDisconnect:
        print("[WS] Admin Dashboard Disconnected")
    except Exception as e:
        print(f"[WS ERROR] {e}")

# ==========================================
# 2. ANALYSIS API
# ==========================================
@app.get("/api/history/{node_id}")
async def get_node_history(node_id: str):
    if node_id in mgr.historian.node_history:
        return list(mgr.historian.node_history[node_id])
    return {"error": "Node not found"}

@app.get("/api/summary")
async def get_project_summary():
    return {
        "energy_saved_wh": round(mgr.historian.total_saved_energy, 2),
        "energy_wasted_wh": round(mgr.historian.total_wasted_energy, 2),
        "co2_offset_kg": round(mgr.historian.total_saved_energy * 0.475, 4),
        "system_status": "OPTIMIZED" if len(mgr.nodes) > 0 else "IDLE"
    }

# ==========================================
# 3. LIFECYCLE MANAGEMENT
# ==========================================
@app.on_event("startup")
async def startup_event():
    print("[API] Initializing Simulation Environment...")
    
    if not mgr.nodes:
        mgr.provision_node("Master_Node")

    # START ALL LOGIC IN BACKGROUND THREADS
    # We move cluster_monitor to a thread so it doesn't block FastAPI
    threading.Thread(target=mgr.predictive_scale_logic, daemon=True).start()
    threading.Thread(target=mgr.data_collection_loop, daemon=True).start()
    threading.Thread(target=traffic_generator, args=(mgr,), daemon=True).start()
    threading.Thread(target=cluster_monitor, args=(mgr,), daemon=True).start()
    
    print("[API] All Simulation Threads are now Running in Background.")

if __name__ == "__main__":
    # Running uvicorn directly
    uvicorn.run(app, host="0.0.0.0", port=8000)