inventory = [
    {"name": "rice", "price": 1200},
    {"name": "eggs", "price": 14}
]
sales_log = []
def show_menu():
    print("\n--- SHOP INVENTORY SYSTEM ---")
    print("1. View products")
    print("2. Add product")
    print("3. Remove product")
    print("4. Record sale")
    print("5. Daily report")
    print("6. Exit")
def view_products():
    if not inventory:
        print("No products in inventory.")
    else:
        print("\n=== Current Inventory ==")
        for item in inventory:
            print(f"  Name: {item['name']} | Price: Ksh {item['price']}")
def add_product():
    name = input("Enter product name: ").strip().lower()
    if not name:
        print("Product name cannot be empty.")
        return
    try:
        price = float(input("Enter product price: "))
        if price < 0:
            print("Price cannot be negative.")
            return
        inventory.append({"name": name, "price": price})
        print(f"'{name}' has been added.")
    except ValueError:
        print("Invalid price. Please enter a number.")
def remove_product():
    name = input("Enter product to remove: ").strip().lower()
    original_length = len(inventory)
    if len(inventory) < original_length:
        print(f"'{name}' has been removed.")
    else:
        print(f"'{name}' was not found in inventory.")
def record_sale():
    name = input("Enter product sold: ").strip().lower()
    product_found = False
    for item in inventory:
        if item["name"] == name:
            sales_log.append({"name": name, "price": item["price"]})
            print(f"Sale recorded: {name} at Ksh {item['price']}.")
            product_found = True
            break
    if not product_found:
        print("Product not found in inventory.")
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
    while True:
        show_menu()
        choice = input("Select any option (1-6): ")
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
            print("Exiting system. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
run()