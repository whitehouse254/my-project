inventory={"laptop":{"quantity":10,"price":900},
            "mouse":{"quantity":25,"price":25},
            "monitor":{"quantity":7,"price":200}}
inventory.update({"monitor": {"quantity": 5, "price": 25}})
inventory["keyboard"]={"quantity":7,"price":200}
print(inventory)
for name, item in inventory.items():
    total_value = item["quantity"] * item["price"]
    print(f"{name}: ksh{total_value}")
