def check_altitude(altitude):
    if altitude>120:
        print("too high")
    elif 120 > altitude > 30:
        print("suitable altitude")
    else:
        print("too low")
altitudes=[20,28,148,72,10,47,60,19,44,54,95]
for a in altitudes:
    check_altitude(a)