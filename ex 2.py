def calculate_tickets(age,day_of_week):
    day= day_of_week.lower()
    weekday = ["monday", "tuesday", "wednesday", "Thursday", "friday"]
    weekend = ["saturday","sunday"]
    if age<=12:
        base_price=8
    elif 13<= age <=64:
        base_price=12
    else:
        base_price=10
        return base_price
    if day in weekday: 
        final_price = base_price - 2
        return final_price
    elif day in weekend:
        final_price = base_price
        return final_price

print(calculate_tickets(54,"monday"))







