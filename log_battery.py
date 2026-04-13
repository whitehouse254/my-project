def read_log_battery():
    with open("battery.txt", "w") as log:
        for f in range(100, 0, -2):
            log.write(f"{f}\n")
def write_analyze_battery():
    safe = 0
    warning = 0
    critical = 0
    with open("battery.txt", "r") as log:
        for line in log:
            battery = int(line.strip())
            if battery >= 50:
                safe += 1
            elif 20 <= battery <= 49:
                warning += 1
            else:
                critical += 1
    return safe, warning, critical
read_log_battery()
safe_count, warning_count, critical_count = write_analyze_battery()
print(f"Safe: {safe_count}")
print(f"Warning: {warning_count}")
print(f"Critical: {critical_count}")