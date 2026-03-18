import threading
import time
import random
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from tensorflow.keras.models import load_model
from collections import deque

# ==========================================
# 1. THE HARDWARE LAYER (Virtual Node)
# ==========================================
class CloudServerNode(threading.Thread):
    def __init__(self, node_id, personality):
        super().__init__()
        self.node_id = node_id
        self.personality = personality
        self.active = True
        
        # Telemetry State
        self.cpu_usage = 0.0
        self.cpu_lag_1 = 0.0
        self.mem_usage_kb = 1024.0
        self.disk_read_kb = 0.0
        self.disk_write_kb = 0.0
        self.net_received_kb = 0.0
        self.net_transmitted_kb = 0.0
        
    def run(self):
        while self.active:
            self.cpu_lag_1 = self.cpu_usage
            # Cooling effect: Drop 12% usage every 2 seconds if idle
            if self.cpu_usage > 0:
                self.cpu_usage = max(0.0, self.cpu_usage - 12.0) 
            time.sleep(2)

    def process_packet(self, packet_size, complexity):
        self.cpu_usage = min(100.0, self.cpu_usage + (complexity * 3.0))
        self.mem_usage_kb += (packet_size * 0.05)
        self.net_received_kb += packet_size
        self.disk_write_kb += (packet_size * 0.02)

    def get_telemetry(self):
        return {
            "node_id": self.node_id,
            "CPU usage [%]": self.cpu_usage,
            "CPU_Lag_1": self.cpu_lag_1,
            "Memory usage [KB]": self.mem_usage_kb,
            "Disk read throughput [KB/s]": self.disk_read_kb,
            "Disk write throughput [KB/s]": self.disk_write_kb,
            "Network received throughput [KB/s]": self.net_received_kb,
            "Network transmitted throughput [KB/s]": self.net_transmitted_kb
        }

# ==========================================
# 2. THE ML INFERENCE ENGINE
# ==========================================
class MLPredictor:
    def __init__(self):
        print("\n[AI] Initializing Neural Networks and Forest Models...")
        # Define the exact feature names you used during training in Phase 2
        self.feature_cols = [
            "CPU usage [%]", "CPU_Lag_1", "Memory usage [KB]",
            "Disk read throughput [KB/s]", "Disk write throughput [KB/s]",
            "Network received throughput [KB/s]", "Network transmitted throughput [KB/s]"
        ]
        
        try:
            self.scaler = joblib.load('./Models/scaler.pkl')
            self.rf_model = joblib.load('./Models/rf_model.joblib')
            # FIX: compile=False ignores the version mismatch in the loss function
            self.lstm_model = load_model('./Models/lstm_model.h5', compile=False)
            self.meta_learner = joblib.load('./Models/meta_learner.joblib')
            print("[AI] Hybrid Brain Loaded Successfully.")
        except Exception as e:
            print(f"[CRITICAL ERROR] AI could not start: {e}")
            # Ensure attributes exist to prevent total crash
            self.lstm_model = None 

    def predict_energy(self, t):
        if self.lstm_model is None:
            return 0.0 # Safety return if models didn't load

        # 1. Map telemetry to a DataFrame to keep feature names consistent
        features_raw = [
            t["CPU usage [%]"], t["CPU_Lag_1"], t["Memory usage [KB]"],
            t["Disk read throughput [KB/s]"], t["Disk write throughput [KB/s]"],
            t["Network received throughput [KB/s]"], t["Network transmitted throughput [KB/s]"]
        ]
        
        # Convert to DataFrame to avoid the "Feature Names" warning
        import pandas as pd
        df_input = pd.DataFrame([features_raw], columns=self.feature_cols)
        
        # 2. Scale and Predict
        scaled = self.scaler.transform(df_input)
        rf_val = self.rf_model.predict(scaled)
        
        # LSTM 3D Reshape
        lstm_in = scaled.reshape((1, 1, scaled.shape[1]))
        lstm_val = self.lstm_model.predict(lstm_in, verbose=0).flatten()
        
        # Meta-Combination
        meta_in = np.column_stack((rf_val, lstm_val))
        return self.meta_learner.predict(meta_in)[0]


    
# ==========================================
# 4. EXTERNAL INTERFACES
# ==========================================
def traffic_generator(manager):
    while manager.running:
        mode = random.choice(["PEAK", "QUIET", "QUIET"]) 
        if mode == "PEAK":
            print(f"\n[TRAFFIC] >>> STARTING PEAK BURST")
            for _ in range(random.randint(15, 30)):
                if manager.nodes:
                    target = random.choice(list(manager.nodes.keys()))
                    manager.nodes[target].process_packet(random.randint(1000, 5000), random.randint(6, 12))
                time.sleep(0.4)
        else:
            print(f"\n[TRAFFIC] ... ENTERING QUIET PERIOD")
            time.sleep(12)

def cluster_monitor(manager):
    while manager.running:
        print(f"\n--- CLUSTER STATUS [{datetime.now().strftime('%H:%M:%S')}] ---")
        print(f"Nodes: {len(manager.nodes)} | ID Pool: {manager.available_ids}")
        for nid in sorted(manager.nodes.keys()):
            n = manager.nodes[nid]
            print(f"  > {nid} | CPU: {n.cpu_usage:>5.1f}% | RAM: {n.mem_usage_kb/1024:>6.2f} MB")
        time.sleep(3)

class AdminHistorian:
    def __init__(self, max_logs=100):
        self.max_logs = max_logs
        self.node_history = {} # { "Node_01": deque }
        self.total_saved_energy = 0.0
        self.total_wasted_energy = 0.0

    def record_node_step(self, node_id, telemetry, predicted_w, actual_w, is_active):
        if node_id not in self.node_history:
            self.node_history[node_id] = deque(maxlen=self.max_logs)
        
        # Sustainability Logic
        baseline_w = 120.0 
        saved = max(0, baseline_w - actual_w) if not is_active else 0
        wasted = actual_w if (telemetry["CPU usage [%]"] < 5.0 and is_active) else 0

        # Convert Watts to Watt-seconds for real-time accumulation
        self.total_saved_energy += (saved / 3600) 
        self.total_wasted_energy += (wasted / 3600)

        log_entry = {
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "node_id": node_id,
            "cpu": round(telemetry["CPU usage [%]"], 2),
            "mem": round(telemetry["Memory usage [KB]"] / 1024, 2),
            "predicted_w": round(predicted_w, 2),
            "actual_w": round(actual_w, 2),
            "saved_w": round(saved, 2),
            "wasted_w": round(wasted, 2),
            "status": "ACTIVE" if is_active else "SLEEP"
        }
        self.node_history[node_id].append(log_entry)
        return log_entry

class PredictiveClusterManager:
    def __init__(self):
        self.nodes = {}
        self.running = True
        self.available_ids = []
        self.max_node_index = 0
        self.ai_brain = MLPredictor()
        self.historian = AdminHistorian() # Integrated Historian
        
        self.UPPER_WATTS = 240.0 
        self.LOWER_WATTS = 115.0

    def provision_node(self, personality="Worker"):
        if self.available_ids:
            self.available_ids.sort()
            node_id = self.available_ids.pop(0)
        else:
            self.max_node_index += 1
            node_id = f"Node_{self.max_node_index:02d}"

        new_node = CloudServerNode(node_id, personality)
        self.nodes[node_id] = new_node
        new_node.start()
        print(f"\n[SYSTEM] >>> PROVISIONED {node_id}")

    def deprovision_node(self, node_id):
        if node_id in self.nodes:
            self.nodes[node_id].active = False
            self.nodes[node_id].join()
            del self.nodes[node_id]
            self.available_ids.append(node_id)
            print(f"\n[SYSTEM] <<< TERMINATED {node_id}")

    def data_collection_loop(self):
        """ 
        NEW: This thread runs every 1 second to feed the historian 
        so the frontend graphs never stop.
        """
        while self.running:
            for node_id, node in list(self.nodes.items()):
                telemetry = node.get_telemetry()
                # Get a live prediction for this node
                pred_w = self.ai_brain.predict_energy(telemetry)
                # In simulation, actual is close to prediction + noise
                actual_w = pred_w * random.uniform(0.9, 1.1) 
                
                # Push to historian
                self.historian.record_node_step(node_id, telemetry, pred_w, actual_w, True)
            time.sleep(1)

    def predictive_scale_logic(self):
        while self.running:
            if self.nodes:
                total_forecast = 0
                node_list = list(self.nodes.values())
                for node in node_list:
                    total_forecast += self.ai_brain.predict_energy(node.get_telemetry())
                
                avg_forecast = total_forecast / len(self.nodes)
                print(f"[AI MONITOR] Forecasted Avg Energy: {avg_forecast:.2f}W")

                if avg_forecast > self.UPPER_WATTS:
                    self.provision_node("Predictive_Scale_Up")
                elif avg_forecast < self.LOWER_WATTS and len(self.nodes) > 1:
                    target = min(self.nodes, key=lambda k: self.nodes[k].cpu_usage)
                    self.deprovision_node(target)
            time.sleep(5)

mgr = PredictiveClusterManager()

    
