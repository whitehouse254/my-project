def write_flight_log(filename):
    with open(filename, "w") as log:
        for altitude in range(0, 501, 5):
            log.write(f"{altitude}\n")
def read_flight_log(filename):
    with open(filename, 'r') as log:
        return [(line.strip()) for line in log ]
filename = "flight_log.txt"
write_flight_log(filename)
for altitude in read_flight_log(filename):
        print(altitude)



