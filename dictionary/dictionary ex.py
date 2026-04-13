plane={"battery":96,"altitude":50,"speed":450}
def flight_check(plane):
    if plane["battery"] <20 or plane["altitude"]>120:
        return "ABORT"
    else:
        return "fly"
print(flight_check(plane))



