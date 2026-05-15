import datetime
import csv
import os
import sqlite3
saves_file = "sales.csv"
inventory = [
    {"name": "rice", "price": 1200, "quantity": 10},
    {"name": "maize flour", "price": 180, "quantity": 8},
    {"name": "wheat flour", "price": 220, "quantity": 6},
    {"name": "bread", "price": 120, "quantity": 15},
    {"name": "eggs", "price": 23, "quantity": 30},
    {"name": "milk", "price": 90, "quantity": 50},
]
def save_sale(sale):
    file_exists = os.path.exists(saves_file)
    with open(saves_file, "a",newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["time", "name", "price", "quantity", "subtotal", "discount", "total", "cash", "change"])
        if not file_exists:writer.writeheader()
        writer.writerow({"time": sale["time"].strftime("%Y-%m-%d %H:%M:%S"),
            "name": sale["name"],
            "price": sale["price"],
            "quantity": sale["quantity"],
            "subtotal": sale["subtotal"],
            "discount": round(sale["discount"]),
            "total": round(sale["total"]),
            "cash": round(sale["cash"]),
            "change": round(sale["change"]),
        })
sales_log = []
def show_menu():
    print("\n=== Welcome to Victor's Shop ===")
    print("1.View inventory")
    print("2.Add product")
    print("3.Remove product")
    print("4.search_with_low_stock_alert")
    print("5.Record sale")
    print("6.generate_Daily_report")
    print("7.Exit")
    print("=== please choose any option ===")
def view_products():
    if not inventory:
        print("No products in inventory.")
    else:
        print("\n=== Current Inventory ==")
        for item in inventory:
            print(f"Name: {item['name']} | Price: Ksh {item['price']} | Stock: {item['quantity']}")
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
        print(" Please enter a number for price")
        return
    try:
        quantity = int(input("Enter quantity: "))
        if quantity < 0:
            print("Quantity cannot be negative.")
            return
    except ValueError:
        print("Please enter a valid number for quantity.")
        return
    new_product = {"name":name, "price":price, "quantity":quantity}
    inventory.append(new_product)
    print(f"{name} has been added")
def remove_product():
        print("\n=== Remove Product ===")
        name = input("Enter product to remove: ").strip().lower()
        for item in inventory:
            if item["name"] == name:
                inventory.remove(item)
                print(f"'{name}' has been removed.")
                return
        print(f"'{name}' was not found in inventory")
def search_with_low_stock_alert():
                print("\n===search_with_low_stock_alert ===")
                name = input("\nWhat are you searching for: ").strip().lower()
                found = False
                for item in inventory:
                    if name == item["name"].lower():
                        found = True
                        low_stock = item["quantity"] <= 2
                        if low_stock:
                            print(f"product Found: {item['name']} = Price: {item['price']}   low stock ({item['quantity']})")
                        else:
                            print(f"Found: {item['name']} | Price: {item['price']} | Stock: {item['quantity']}")
                if not found:
                    print("sorry product not found go and build your shop which has it")
def apply_discount(subtotal, quantity, loyalty_card):
    discount = 0
    if loyalty_card:
        if subtotal >= 10000:
            discount += 0.10 * subtotal
        elif subtotal >= 5000:
            discount += 0.05 * subtotal
        elif subtotal >= 3000:
            discount += 0.02 * subtotal
    if quantity >= 10:
        discount = max(discount, 0.05 * subtotal)
    final_total = subtotal - discount
    return final_total, discount
def record_sale():
    print("\n=== Record a Sale ===")
    while True:
        view_products()
        name = input("\nEnter product name or DONE to finish: ").strip().lower()
        if name == "done":
            print("Thank you for coming here and not going to the other shops")
            break
        for item in inventory:
            if item["name"].lower() == name:
                try:
                    quantity = int(input("Please enter quantity: "))
                except ValueError:
                    print("Please enter a valid quantity or leave the place.")
                    continue
                if quantity <= 0:
                    print("Quantity must be greater than 0.")
                    continue
                if item.get("quantity", 0) < quantity:
                    print("Not enough stock available.")
                    continue
                subtotal = item["price"] * quantity
                loyalty_input = input("Does customer have a loyalty card? (yes/no): ").strip().lower()
                loyalty_card = loyalty_input == "yes"
                final_total, discount = apply_discount(subtotal, quantity, loyalty_card)
                try:
                    cash = float(input("Enter cash paid: "))
                except ValueError:
                    print("Please enter the right amount.")
                    continue
                if cash < final_total:
                    print("Insufficient funds please top up")
                    continue
                change = cash - final_total
                sales_log.append({"name": item["name"],"price": item["price"],"quantity": quantity,"subtotal": subtotal,"discount": discount,"total": final_total,"cash": cash,"change": change,"time": datetime.datetime.now()
                })
                save_sale(sales_log[-1])
                item["quantity"] -= quantity
                print("====================")
                print(" 🛒🛒🛒🛒RECEIPT🛒🛒🛒🛒")
                print("====================")
                print(f"Item: {item['name']}")
                print(f"Quantity: {quantity}")
                print(f"Unit Price: Ksh {item['price']}")
                print(f"Subtotal: Ksh {subtotal}")
                print(f"Discount: -Ksh {discount}")
                print(f"Final Total: Ksh {final_total}")
                print(f"Cash Paid: Ksh {cash}")
                print(f"Change: Ksh {change}")
                print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("====================")
                print("VICTOR'S SHOP SAVES YOU MONEY!")
                print("====================\n")
                break
        else:
            print(f"Product '{name}' not found. Try again")
def generate_daily_report():
    if not sales_log:
        print("No sales recorded yet.")
        return
    print("\n=== Daily Sales Report ===")
    total_revenue = 0
    total_items_sold = 0
    print("\n==== Transactions ====")
    for sale in sales_log:
        total_revenue += sale["total"]
        total_items_sold += sale["quantity"]
        print(f"  {sale['name']} x{sale['quantity']} | Total: Ksh {sale['total']}")
    print("\n==== Summary ====")
    print(f"  Total items sold : {total_items_sold}")
    print(f"  Total revenue    : Ksh {total_revenue}")
    threshold = 5
    low_stock_items = [item for item in inventory if item["quantity"] <= threshold]
    if low_stock_items:
        print("\n==== Low Stock Alert ====")
        low_stock_items.sort(key=lambda x: x["quantity"])
        for item in low_stock_items:
            print(f"  {item['name']:} | Remaining: {item['quantity']}")
    else:
        print("\n  All items are well stocked.")
def run():
    print("\n=================" )
    print("   Welcome to Victor's Shop!")
    print("   Your savings start here.")
    print("================== \n" )
    while True:
        show_menu()
        choice = input("Select option (1-7): ").strip()
        if choice == "1":
            view_products()
        elif choice == "2":
            add_product()
        elif choice == "3":
            remove_product()
        elif choice == "4":
            search_with_low_stock_alert()
        elif choice == "5":
            record_sale()
        elif choice == "6":
            generate_daily_report()
        elif choice == "7":
            print("Thank you coming using Victor's Shop Goodbye!")
            break
run()