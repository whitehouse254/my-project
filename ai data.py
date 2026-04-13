import csv
import time
from datetime import datetime
import random

# Configuration
log_interval = 60
total_logs = 5
csv_file = "flight_log.csv"
data = []
def get_altitude():
    return round(random.uniform(1000, 5000), 2)
def get_speed():
    return round(random.uniform(200, 900), 2)
def log_data():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    altitude = get_altitude()
    speed = get_speed()
    return [timestamp, altitude, speed]
def save_to_csv(data):
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Altitude (m)", "Speed (km/h)"])
        writer.writerows(data)
def print_summary(data):
    altitudes = [row[1] for row in data]
    speeds = [row[2] for row in data]
    print("\n--- SUMMARY ---")
    print(f"Total logs: {len(data)}")
    print(f"Average altitude: {sum(altitudes) / len(altitudes):.2f} m")
    print(f"Max altitude: {max(altitudes)} m")
    print(f"Min altitude: {min(altitudes)} m")
    print(f"Average speed: {sum(speeds) / len(speeds):.2f} km/h")
    print(f"Max speed: {max(speeds)} km/h")
    print(f"Min speed: {min(speeds)} km/h")
print("Logging started...\n")
for i in range(total_logs):
    entry = log_data()
    data.append(entry)
    print(f"Logged: {entry}")
    if i < total_logs - 1:
        time.sleep(log_interval)
save_to_csv(data)
print_summary(data)
print(f"\nData saved to {csv_file}")