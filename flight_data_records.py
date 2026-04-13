t = __import__("time")
with open("log.csv", "w") as file:
    file.write("Second,Value,Altitude\n")
    for i in range(61):
        second = i
        timestamp = t.strftime("%Y-%m-%d %H:%M:%S", t.localtime())
        value = 25 + (i % 6) * 0.5
        altitude = 100 + (i % 100) * 83
        file.write(f"{second},{value},{altitude}\n")
        print(f"{second},{timestamp},{value},{altitude}")
        t.sleep(1)
print("Done")