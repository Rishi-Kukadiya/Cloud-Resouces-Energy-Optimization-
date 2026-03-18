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
            if self.cpu_usage > 0:
                self.cpu_usage = max(0.0, self.cpu_usage - 12.0) 
            time.sleep(2)

    def process_packet(self, packet_size, complexity):
        self.cpu_usage = min(100.0, self.cpu_usage + (complexity * 3.0))
        self.mem_usage_kb += (packet_size * 0.05)
        self.net_received_kb += packet_size
        self.disk_write_kb += (packet_size * 0.02)
        # Randomize IO and Network Out for realism
        self.disk_read_kb = random.uniform(10, 100)
        self.net_transmitted_kb = random.uniform(50, 200)

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
        self.feature_cols = [
            "CPU usage [%]", "CPU_Lag_1", "Memory usage [KB]",
            "Disk read throughput [KB/s]", "Disk write throughput [KB/s]",
            "Network received throughput [KB/s]", "Network transmitted throughput [KB/s]"
        ]
        try:
            self.scaler = joblib.load('./Models/scaler.pkl')
            self.rf_model = joblib.load('./Models/rf_model.joblib')
            self.lstm_model = load_model('./Models/lstm_model.h5', compile=False)
            self.meta_learner = joblib.load('./Models/meta_learner.joblib')
            print("[AI] Hybrid Brain Loaded Successfully.")
        except Exception as e:
            print(f"[CRITICAL ERROR] AI could not start: {e}")
            self.lstm_model = None 

    def predict_energy(self, t):
        if self.lstm_model is None: return 120.0 # Return static baseline if ML fails
        features_raw = [
            t["CPU usage [%]"], t["CPU_Lag_1"], t["Memory usage [KB]"],
            t["Disk read throughput [KB/s]"], t["Disk write throughput [KB/s]"],
            t["Network received throughput [KB/s]"], t["Network transmitted throughput [KB/s]"]
        ]
        df_input = pd.DataFrame([features_raw], columns=self.feature_cols)
        scaled = self.scaler.transform(df_input)
        rf_val = self.rf_model.predict(scaled)
        lstm_in = scaled.reshape((1, 1, scaled.shape[1]))
        lstm_val = self.lstm_model.predict(lstm_in, verbose=0).flatten()
        meta_in = np.column_stack((rf_val, lstm_val))
        return self.meta_learner.predict(meta_in)[0]

# ==========================================
# 3. ADMIN HISTORIAN & CLUSTER MANAGEMENT
# ==========================================
class AdminHistorian:
    def __init__(self, max_logs=100):
        self.max_logs = max_logs
        self.node_history = {} 
        self.total_saved_energy = 0.0
        self.total_wasted_energy = 0.0

    def record_node_step(self, node_id, telemetry, predicted_w, actual_w, is_active):
        if node_id not in self.node_history:
            self.node_history[node_id] = deque(maxlen=self.max_logs)
        
        baseline_w = 150.0 # What a physical server uses if always ON
        
        # LOGIC FIX: If node is Terminated/Sleep, actual_w is 0. 
        # Therefore, Saved = Baseline.
        if not is_active:
            saved = baseline_w 
            actual_w = 0.0
            telemetry = {k: 0.0 for k in telemetry} # Zero out stats for UI
        else:
            saved = 0.0 # It's running, so we aren't "saving" its static power

        wasted = actual_w if (telemetry.get("CPU usage [%]", 0) < 5.0 and is_active) else 0

        self.total_saved_energy += (saved / 3600) 
        self.total_wasted_energy += (wasted / 3600)

        log_entry = {
            "timestamp": datetime.now().strftime('%H:%M:%S'),
            "node_id": node_id,
            "cpu": round(telemetry.get("CPU usage [%]", 0), 2),
            "mem": round(telemetry.get("Memory usage [KB]", 0) / 1024, 2),
            "disk_io": round(telemetry.get("Disk read throughput [KB/s]", 0) + telemetry.get("Disk write throughput [KB/s]", 0), 2),
            "network": round(telemetry.get("Network received throughput [KB/s]", 0) + telemetry.get("Network transmitted throughput [KB/s]", 0), 2),
            "predicted_w": round(predicted_w, 2),
            "actual_w": round(actual_w, 2),
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
        self.historian = AdminHistorian()
        self.UPPER_WATTS = 220.0 
        self.LOWER_WATTS = 110.0

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
        while self.running:
            # We must account for ALL possible IDs (Active + Pool) to calculate savings
            all_ids = set(list(self.nodes.keys()) + self.available_ids)
            for node_id in all_ids:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    telemetry = node.get_telemetry()
                    pred_w = self.ai_brain.predict_energy(telemetry)
                    actual_w = pred_w * random.uniform(0.95, 1.05)
                    self.historian.record_node_step(node_id, telemetry, pred_w, actual_w, True)
                else:
                    # It's in the pool (Sleep), so record a zero-power step to count savings
                    dummy_tel = {"CPU usage [%]": 0, "Memory usage [KB]": 0, "Disk read throughput [KB/s]": 0, "Disk write throughput [KB/s]": 0, "Network received throughput [KB/s]": 0, "Network transmitted throughput [KB/s]": 0}
                    self.historian.record_node_step(node_id, dummy_tel, 0, 0, False)
            time.sleep(1)

    def predictive_scale_logic(self):
        while self.running:
            if self.nodes:
                node_list = list(self.nodes.values())
                total_forecast = sum(self.ai_brain.predict_energy(n.get_telemetry()) for n in node_list)
                avg_forecast = total_forecast / len(self.nodes)
                if avg_forecast > self.UPPER_WATTS:
                    self.provision_node("Dynamic_Scale_Up")
                elif avg_forecast < self.LOWER_WATTS and len(self.nodes) > 1:
                    target = min(self.nodes, key=lambda k: self.nodes[k].cpu_usage)
                    self.deprovision_node(target)
            time.sleep(5)

def traffic_generator(manager):
    while manager.running:
        mode = random.choice(["PEAK", "QUIET", "QUIET"]) 
        if mode == "PEAK":
            for _ in range(random.randint(15, 30)):
                if manager.nodes:
                    target = random.choice(list(manager.nodes.keys()))
                    manager.nodes[target].process_packet(random.randint(1000, 5000), random.randint(6, 12))
                time.sleep(0.4)
        else:
            time.sleep(12)

def cluster_monitor(manager):
    while manager.running:
        time.sleep(5)

mgr = PredictiveClusterManager()