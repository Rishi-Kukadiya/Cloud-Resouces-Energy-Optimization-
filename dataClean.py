import pandas as pd
import glob
import numpy as np

path = 'fastStorage/2013-8/*.csv' 
files = glob.glob(path)

def load_and_preprocess(file_path):
    df = pd.read_csv(file_path, sep=';\t', engine='python')
    df.columns = [c.strip() for c in df.columns]

    df['Datetime'] = pd.to_datetime(df['Timestamp [ms]'], unit='ms')
    
    def calculate_energy(row):
        p_static, p_max = 100.0, 300.0
        cpu_p = p_static + (p_max - p_static) * (row['CPU usage [%]'] / 100.0)
        mem_p = (row['Memory usage [KB]'] / (8 * 1024 * 1024)) * 3.0
        disk_p = (row['Disk read throughput [KB/s]'] + row['Disk write throughput [KB/s]']) * 0.00001
        return cpu_p + mem_p + disk_p

    df['Energy_Consumption_Watts'] = df.apply(calculate_energy, axis=1)
    df['CPU_Lag_1'] = df['CPU usage [%]'].shift(1)    
    return df

df = load_and_preprocess(files[0])
features = [
    'CPU usage [%]', 
    'CPU_Lag_1',         # Key for Time-Series
    'Memory usage [KB]', 
    'Disk read throughput [KB/s]', 
    'Disk write throughput [KB/s]',
    'Network received throughput [KB/s]',
    'Network transmitted throughput [KB/s]'
]

target = 'Energy_Consumption_Watts'

df_final = df[features + [target]].dropna().copy()
df_final.to_csv('processed_cloud_data.csv', index=False)