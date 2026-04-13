inventory = [
    {"name": "rice", "price": 1200},
    {"name": "maize flour", "price": 180},
    {"name": "wheat flour", "price": 220},
    {"name": "bread", "price": 65},
    {"name": "eggs", "price": 14},
    {"name": "milk", "price": 60},
]
sales_log = []
def show_menu():
    print("\n=== Welcome to Victor's Shop ===")
    print("  1. View inventory")
    print("  2. Add product")
    print("  3. Remove product")
    print("  4. Record sale")
    print("  5. Daily report")
    print("  6. Exit")
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
def remove_product():
    name = input("Enter product to remove: ").strip().lower()
    original_length = len(inventory)
    if len(inventory) < original_length:
        print(f"'{name}' has been removed.")
    else:
        print(f"'{name}' was not found in inventory.")
def record_sale():
        print("\n=== Record a Sale ===")
        view_products()
        name = input("\n please Enter product name sold: ").strip().lower()
        for item in inventory:
            if item["name"] == name:
                sales_log.append({"name": name, "total": item["price"]})
                print(f"Sale recorded: {name} = Ksh {item['price']}")
                return
        print(f"Product '{name}' not found in inventory.")
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
        choice = input("Select option (1-6): ").strip()
        if choice == "1":
            view_products()
        elif choice == "2":
            add_product()
        elif choice == "3":
            remove_product()
        elif choice == "4":
            record_sale()
        elif choice == "5":
            daily_report()
        elif choice == "6":
            print("Thank you coming using Victor's Shop. Goodbye!")
            break
run()