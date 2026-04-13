from datetime import datetime

inventory = [
    # Grains & Staples
    {"name": "rice", "price": 1200, "stock": 50},
    {"name": "maize flour", "price": 180, "stock": 80},
    {"name": "wheat flour", "price": 220, "stock": 60},
    {"name": "bread", "price": 65, "stock": 40},
    {"name": "pasta", "price": 150, "stock": 35},
    # Dairy & Eggs
    {"name": "eggs", "price": 14, "stock": 200},
    {"name": "milk", "price": 60, "stock": 100},
    {"name": "butter", "price": 280, "stock": 25},
    {"name": "yoghurt", "price": 120, "stock": 30},
    # Cooking Essentials
    {"name": "cooking oil", "price": 350, "stock": 45},
    {"name": "sugar", "price": 200, "stock": 70},
    {"name": "salt", "price": 50, "stock": 90},
    {"name": "tomato paste", "price": 85, "stock": 50},
    # Beverages
    {"name": "tea leaves", "price": 250, "stock": 40},
    {"name": "coffee", "price": 400, "stock": 20},
    {"name": "soda", "price": 80, "stock": 60},
    {"name": "water bottle", "price": 50, "stock": 100},
    # Household
    {"name": "soap", "price": 90, "stock": 55},
    {"name": "washing powder", "price": 320, "stock": 30},
    {"name": "toothpaste", "price": 150, "stock": 25},
]
sales_log = []


# ──────────────────────────────────────────
#  DISPLAY HELPERS
# ──────────────────────────────────────────

def divider():
    print("─" * 40)


def show_menu():
    divider()
    print("     SHOP INVENTORY SYSTEM")
    divider()
    print("  1. View inventory")
    print("  2. Add product")
    print("  3. Remove product")
    print("  4. Restock product")
    print("  5. Record sale")
    print("  6. Daily report")
    print("  7. Search product")
    print("  8. Exit")
    divider()


# ──────────────────────────────────────────
#  INVENTORY FUNCTIONS
# ──────────────────────────────────────────

def view_products():
    if not inventory:
        print("  No products in inventory.")
        return
    divider()
    print(f"  {'NAME':<15} {'PRICE (Ksh)':>12} {'STOCK':>8}")
    divider()
    for item in inventory:
        stock_warning = " [LOW]" if item["stock"] <= 5 else ""
        print(f"  {item['name'].title():<15} {item['price']:>12,.0f} {item['stock']:>8}{stock_warning}")
    divider()
    print(f"  Total products: {len(inventory)}")


def find_product(name):
    for item in inventory:
        if item["name"] == name:
            return item
    return None


def add_product():
    divider()
    print("  ADD NEW PRODUCT")
    divider()
    name = input("  Product name: ").strip().lower()
    if not name:
        print("  Error: Name cannot be empty.")
        return
    if find_product(name):
        print(f"  Error: '{name}' already exists. Use restock to update quantity.")
        return
    try:
        price = float(input("  Price (Ksh): "))
        if price < 0:
            print("  Error: Price cannot be negative.")
            return
        stock = int(input("  Initial stock quantity: "))
        if stock < 0:
            print("  Error: Stock cannot be negative.")
            return
    except ValueError:
        print("  Error: Invalid input. Please enter numbers.")
        return
    inventory.append({"name": name, "price": price, "stock": stock})
    print(f"  '{name.title()}' added — Ksh {price:,.0f} | Stock: {stock}")


def remove_product():
    divider()
    print("  REMOVE PRODUCT")
    divider()
    name = input("  Product to remove: ").strip().lower()
    item = find_product(name)
    if not item:
        print(f"  Error: '{name}' not found.")
        return
    confirm = input(f"  Remove '{name.title()}'? (yes/no): ").strip().lower()
    if confirm == "yes":
        inventory.remove(item)
        print(f"  '{name.title()}' has been removed.")
    else:
        print("  Cancelled.")


def restock_product():
    divider()
    print("  RESTOCK PRODUCT")
    divider()
    name = input("  Product to restock: ").strip().lower()
    item = find_product(name)
    if not item:
        print(f"  Error: '{name}' not found.")
        return
    try:
        qty = int(input(f"  Current stock: {item['stock']}. Add quantity: "))
        if qty <= 0:
            print("  Error: Quantity must be positive.")
            return
        item["stock"] += qty
        print(f"  '{name.title()}' restocked. New stock: {item['stock']}")
    except ValueError:
        print("  Error: Invalid quantity.")


def search_product():
    divider()
    print("  SEARCH PRODUCT")
    divider()
    keyword = input("  Enter name or keyword: ").strip().lower()
    results = [i for i in inventory if keyword in i["name"]]
    if not results:
        print(f"  No products found matching '{keyword}'.")
        return
    print(f"\n  Results for '{keyword}':")
    for item in results:
        print(f"  - {item['name'].title()} | Ksh {item['price']:,.0f} | Stock: {item['stock']}")


# ──────────────────────────────────────────
#  SALES FUNCTIONS
# ──────────────────────────────────────────

def record_sale():
    divider()
    print("  RECORD SALE")
    divider()
    name = input("  Product sold: ").strip().lower()
    item = find_product(name)
    if not item:
        print(f"  Error: '{name}' not found in inventory.")
        return
    if item["stock"] <= 0:
        print(f"  Error: '{name.title()}' is out of stock!")
        return
    try:
        qty = int(input(f"  Quantity sold (available: {item['stock']}): "))
        if qty <= 0:
            print("  Error: Quantity must be positive.")
            return
        if qty > item["stock"]:
            print(f"  Error: Not enough stock. Available: {item['stock']}")
            return
    except ValueError:
        print("  Error: Invalid quantity.")
        return
    item["stock"] -= qty
    total = item["price"] * qty
    sales_log.append({
        "name": name,
        "price": item["price"],
        "qty": qty,
        "total": total,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    print(f"  Sold {qty}x {name.title()} | Total: Ksh {total:,.0f}")
    if item["stock"] <= 5:
        print(f"  Warning: only {item['stock']} units left!")


def daily_report():
    divider()
    print("  DAILY SALES REPORT")
    print(f"  Date: {datetime.now().strftime('%d %b %Y')}")
    divider()
    if not sales_log:
        print("  No sales recorded yet.")
        return
    print(f"  {'PRODUCT':<15} {'QTY':>5} {'UNIT PRICE':>12} {'TOTAL':>12} {'TIME':>10}")
    divider()
    total_revenue = 0
    total_units = 0
    for sale in sales_log:
        print(f"  {sale['name'].title():<15} {sale['qty']:>5} "
              f"{sale['price']:>12,.0f} {sale['total']:>12,.0f} {sale['time']:>10}")
        total_revenue += sale["total"]
        total_units += sale["qty"]
    divider()
    print(f"  Total units sold : {total_units}")
    print(f"  Total revenue    : Ksh {total_revenue:,.0f}")
    divider()


# ──────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────

def run():
    print("\n  Welcome to the Shop Inventory System!")
    while True:
        show_menu()
        choice = input("  Select option (1-8): ").strip()

        if choice == "1":
            view_products()
        elif choice == "2":
            add_product()
        elif choice == "3":
            remove_product()
        elif choice == "4":
            restock_product()
        elif choice == "5":
            record_sale()
        elif choice == "6":
            daily_report()
        elif choice == "7":
            search_product()
        elif choice == "8":
            divider()
            print("  Goodbye! Have a great day.")
            divider()
            break
        else:
            print("  Invalid choice. Please enter 1-8.")


run()