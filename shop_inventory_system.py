import datetime
inventory = [
    {"name": "rice", "price": 1200, "quantity": 10},
    {"name": "maize flour", "price": 180, "quantity": 8},
    {"name": "wheat flour", "price": 220, "quantity": 6},
    {"name": "bread", "price": 65, "quantity": 15},
    {"name": "eggs", "price": 14, "quantity": 30},
    {"name": "milk", "price": 60, "quantity": 50},
]
sales_log = []
def show_menu():
    print("\n=== Welcome to Victor's Shop ===")
    print("1.View inventory")
    print("2.Add product")
    print("3.Remove product")
    print("4.search product")
    print("5.search_with_low_stock_alert")
    print("6.Record sale")
    print("7.Daily report")
    print("8.Exit")
    print("===please choose any option===")
def view_products():
    if not inventory:
        print("No products in inventory.")
    else:
        print("\n=== Current Inventory ==")
        for item in inventory:
            print(f"  Name: {item['name']} | Price: Ksh {item['price']}")
def add_product():
    print("\n=== Add New Product ===")
    name = input("please enter product name: ").strip().lower()
    for item in inventory:
        if item["name"] == name:
            print(f"'{name}' already exists in inventory")
            return
    try:
        price = float(input("please Enter the price price (Ksh): "))
        if price <= 0:
            print("Price must be greater than 0.")
            return
    except ValueError:
        print("price is too low. Please enter a number for price.")
        return
    inventory.append({"name": name, "price": price})
    print(f"'{name}' added successfully!")
def remove_product():
    name = input("Enter product to remove: ").strip().lower()
    for item in inventory:
        if item["name"] == name:
            inventory.remove(item)
            print(f"'{name}' has been removed.")
            return
    print(f"'{name}' was not found in inventory.")
def search_product():
    print("\n=== Search Products ===")
    name = input("\nWhat are you searching for: ").strip().lower()
    found = False
    for item in inventory:
        if name in item["name"].lower():
            print(f"\nFound: {name} = Price: {item['price']}")
            found = True
    if not found:
        print("\nNo matching products found.")
def search_with_low_stock_alert():
                print("\n===search_with_low_stock_alert ===")
                name = input("\nWhat are you searching for: ").strip().lower()
                found = False
                for item in inventory:
                    if name in item["name"].lower():
                        found = True
                        low_stock = item["quantity"] <= 2
                        if low_stock:
                            print(f"product Found: {item['name']} = Price: {item['price']}   low stock ({item['quantity']})")
                        else:
                            print(f"Found: {item['name']} | Price: {item['price']} | Stock: {item['quantity']}")
                if not found:
                    print("sorry product not found go and build your shop which has it")
def record_sale():
    print("\n=== record a Sale ===")
    while True:
        view_products()
        name = input("\n enter product name or DONE to finish: ").strip().lower()
        if name == "done":
            print("thank you for coming here and not going to the other shops.")
            break
        for item in inventory:
            if item["name"].lower() == name:
                try:
                    quantity = int(input("please enter quantity: "))
                except ValueError:
                    print(" please enter a the correct quantity .")
                    continue
                if quantity <= 0:
                    print("quantity must be greater than 0.")
                    continue
                if item.get("quantity", 0) < quantity:
                    print("Not enough stock available.")
                    continue
                total_price = item["price"] * quantity
                sales_log.append({
                    "name": item["name"], "quantity": quantity,"total": total_price,"time": datetime.datetime.now() })
                item["quantity"] -= quantity
                print(f"Total to pay: Ksh {total_price}")
                try:
                    cash = float(input("Enter cash paid: "))
                except ValueError:
                    print("Invalid amount entered.")
                    return
                if cash < total_price:
                    print("you have insufficient funds please tp up!!!!!!.")
                    return
                change = cash - total_price
                print("\n""====================")
                print(" RECEIPT")
                print("====================")
                print(f"Item: {item['name']}")
                print(f"Quantity: {quantity}")
                print(f"Unit Price: Ksh {item['price']}")
                print(f"Total: Ksh {total_price}")
                print(f"Cash Paid: Ksh {cash}")
                print(f"Change: Ksh {change}")
                print(f"Total: Ksh {total_price}")
                print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("======================")
                print("VICTOR`S shop saves you MONEYYYY!")
                print("======================""\n")
                break
        else:
            print(f"Product '{name}' not found. Try again.")
def daily_report():
    if not sales_log:
        print("No sales recorded yet.")
        return
    print("\n=== Daily Report ===")
    total_revenue = 0
    for sale in sales_log:
        print(f"  Sold: {sale['name']} | Price: Ksh {sale['price']}")
        total_revenue += sale["price"]
    print(f"  Total Revenue: Ksh {total_revenue}")
def run():
    print("VICTOR`S SHOP SAVES YOU MONEYYY!!!")
    while True:
        show_menu()
        choice = input("Select option (1-8): ").strip()
        if choice == "1":
            view_products()
        elif choice == "2":
            add_product()
        elif choice == "3":
            remove_product()
        elif choice == "4":
            search_product()
        elif choice == "5":
            search_with_low_stock_alert()
        elif choice == "6":
            record_sale()
        elif choice == "7":
            daily_report()
        elif choice == "8":
            print("Thank you coming using Victor's Shop. Goodbye!")
            break
run()