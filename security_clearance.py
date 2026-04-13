def check_access(time_of_day,role,emergency):
    if role == " A D M I N ":
        return "access granted: welcome sir"
    elif role == "family":
        if 600 <= time_of_day <= 2200 and not emergency :
            return "access granted"
        elif emergency:
            return "access denied: emergency lockdown"
        else:
             return "access denied:time restriction"
    elif role == "guest":
        if emergency or (800 < time_of_day <2000):
            return "access granted"
        else:
            return "access denied: time restriction"
    else:
        return "access denied:invalid role"
print(check_access(2300,"guest",False))
print(check_access(1900,"visitor",True))
print(check_access(100," A D M I N ",False))



