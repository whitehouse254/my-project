def write_flight_log(filepath = "flight_log.txt") -> None:
    with open(filepath, "w") as log:
        for altitude in range(0, 501, 5):
            log.write(f"{altitude}\n")
def read_flight_log(filepath: str = "flight_log.txt"):
    with open(filepath, "r") as log:
        return [(line.strip()) for line in log if line.strip()]
if __file__ == "__main__":
    write_flight_log()
    for altitude in read_flight_log():
        print(altitude)
