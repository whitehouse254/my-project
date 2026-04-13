import time
import random
from datetime import datetime
duration_seconds = 60
with open("log.csv", "w") as file:
    file.write("timestamp,speed,Altitude\n")
    for i in range(duration_seconds + 1):
        timestamp = datetime.now().strftime("%H:%M:%S")
        speed = random.randint(10,100 )
        altitude = random.randint(1000,10000)
        file.write(f"{timestamp},{speed},{altitude}\n")
        print(f"{timestamp} | speed={speed:3} km/h | altitude={altitude:5} m")
        time.sleep(1)
print("/n" "---flight summary---")
print(f"data capture complete")
print(f"total records: {duration_seconds}")
