telemetry = [{"battery":80 , "altitude": 0},
              {"battery":75 , "altitude": 25},
              {"battery":70 , "altitude": 40}]
with open("flight_log.txt","w") as file:
     for t in telemetry:
      file.write(f"{'battery'},{t['altitude']}\n")