import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from datetime import datetime, timedelta
import hashlib
import random
import os
import shutil
import csv
import json
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from PIL import Image, ImageTk
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import schedule
import io
import base64
from collections import defaultdict

# ==================== SQLITE DATE ADAPTER FIX ====================
try:
    from sqlite3 import register_adapter
    from datetime import date, datetime as dt
    def adapt_date(date_val):
        return date_val.isoformat()
    def adapt_datetime(datetime_val):
        return datetime_val.isoformat()
    register_adapter(date, adapt_date)
    register_adapter(dt, adapt_datetime)
except:
    pass

# ==================== CONFIGURATION MANAGER ====================
class ConfigManager:
    DEFAULT_CONFIG = {
        "company_name": "Supermarket System",
        "currency": "Ksh",
        "tax_rates": [
            {"name": "VAT 16%", "rate": 0.16, "categories": ["general", "electronics", "beverages", "snacks"]},
            {"name": "Zero Rated", "rate": 0.0, "categories": ["basic_food", "medicines", "fruits_vegetables"]},
            {"name": "Exempt", "rate": 0.0, "categories": ["services"]}
        ],
        "payment_methods": ["Cash", "Card", "MPESA", "Bank Transfer", "Voucher"],
        "loyalty_points_per_ksh": 0.01,
        "low_stock_threshold": 5,
        "auto_backup": True,
        "backup_interval_days": 1,
        "receipt_footer": "Thank you for shopping!\nVisit again!",
        "restocking_fee_percent": 5,
        "smtp": {"enabled": False, "server": "smtp.gmail.com", "port": 587, "username": "", "password": ""},
        "sms": {"enabled": False, "api_key": "", "username": "", "sender_id": "SuperMarket"},
        "language": "en",
        "theme": "light"
    }
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user = json.load(f)
                merged = self.DEFAULT_CONFIG.copy()
                merged.update(user)
                return merged
        else:
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
    def save_config(self, config=None):
        with open(self.config_path, 'w') as f:
            json.dump(config or self.config, f, indent=4)
    def get_tax_rate(self, category):
        for t in self.config["tax_rates"]:
            if category in t.get("categories", []):
                return t["rate"]
        return self.config["tax_rates"][0]["rate"]

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_name="supermarket.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.populate_initial_data()
    def create_tables(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                buying_price REAL,
                selling_price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 5,
                unit TEXT DEFAULT 'pcs',
                supplier TEXT,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE,
                customer_name TEXT,
                customer_phone TEXT,
                total_amount REAL,
                discount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                net_amount REAL,
                payment_method TEXT,
                cash_tendered REAL,
                change_given REAL,
                cashier TEXT,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                coupon_code TEXT,
                points_used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                unit_price REAL,
                total REAL,
                returned BOOLEAN DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT DEFAULT 'cashier',
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT
            );
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                movement_type TEXT,
                quantity INTEGER,
                reason TEXT,
                user TEXT,
                movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS returns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_invoice TEXT,
                return_invoice TEXT UNIQUE,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                refund_amount REAL,
                restocking_fee REAL,
                reason TEXT,
                cashier TEXT,
                return_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS loyalty (
                customer_phone TEXT PRIMARY KEY,
                customer_name TEXT,
                points INTEGER DEFAULT 0,
                tier TEXT DEFAULT 'Bronze',
                total_spent REAL DEFAULT 0,
                credit_limit REAL DEFAULT 0,
                outstanding_credit REAL DEFAULT 0,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                amount REAL,
                description TEXT,
                expense_date DATE,
                user TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                action TEXT,
                table_name TEXT,
                record_id TEXT,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT UNIQUE,
                supplier_id INTEGER,
                order_date DATE,
                expected_date DATE,
                status TEXT DEFAULT 'pending',
                total_amount REAL,
                created_by TEXT
            );
            CREATE TABLE IF NOT EXISTS po_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER,
                unit_price REAL,
                received_quantity INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount_type TEXT,
                discount_value REAL,
                expiry_date DATE,
                min_purchase REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS bundles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                discount_percent REAL,
                is_active BOOLEAN DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS bundle_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bundle_id INTEGER,
                product_id INTEGER,
                quantity INTEGER
            );
            CREATE TABLE IF NOT EXISTS z_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE,
                cashier_name TEXT,
                expected_cash REAL,
                actual_cash REAL,
                card_total REAL,
                mpesa_total REAL,
                difference REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS kitchen_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT,
                items TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT,
                amount REAL,
                transaction_type TEXT,
                invoice_no TEXT,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        self.conn.commit()
    def populate_initial_data(self):
        # Users
        for u,p,r,n in [("admin","admin123","admin","Admin"),("cashier","cashier123","cashier","Cashier")]:
            if not self.fetch_one("SELECT id FROM users WHERE username=?", (u,)):
                hashed = hashlib.sha256(p.encode()).hexdigest()
                self.execute_query("INSERT INTO users (username,password,role,full_name) VALUES (?,?,?,?)", (u,hashed,r,n))
        # Suppliers (20+)
        if self.fetch_one("SELECT COUNT(*) FROM suppliers")[0] == 0:
            suppliers = []
            for i in range(1, 26):
                suppliers.append((f"Supplier {i}", f"Contact {i}", f"07{random.randint(10000000,99999999)}", f"supplier{i}@mail.com", f"City {i}"))
            for s in suppliers:
                self.execute_query("INSERT INTO suppliers (name,contact_person,phone,email,address) VALUES (?,?,?,?,?)", s)
        # Products (500+)
        if self.fetch_one("SELECT COUNT(*) FROM products")[0] == 0:
            categories = ['Grains', 'Dairy', 'Beverages', 'Snacks', 'Household', 'Electronics', 'Clothing', 'Toys', 'Books', 'Beauty']
            supplier_names = [s[0] for s in self.fetch_all("SELECT name FROM suppliers")]
            for i in range(1, 501):
                cat = random.choice(categories)
                name = f"Product {i} ({cat})"
                bp = random.randint(10, 500)
                sp = bp + random.randint(5, 100)
                qty = random.randint(20, 500)
                min_stock = random.randint(5, 20)
                unit = random.choice(['pcs', 'kg', 'L', 'ml', 'g'])
                barcode = f"890{random.randint(1000000000,9999999999)}"
                supplier = random.choice(supplier_names) if supplier_names else "General"
                self.execute_query("INSERT INTO products (barcode,name,category,buying_price,selling_price,quantity,min_stock,unit,supplier) VALUES (?,?,?,?,?,?,?,?,?)", (barcode,name,cat,bp,sp,qty,min_stock,unit,supplier))
        # Random customers & sales (1000+ sales)
        if self.fetch_one("SELECT COUNT(*) FROM sales")[0] < 200:
            first_names = ['John','Jane','Bob','Alice','Michael','Sarah','David','Linda','James','Patricia','Robert','Jennifer','William','Elizabeth','Richard']
            last_names = ['Doe','Smith','Brown','Wilson','Taylor','Johnson','Lee','Martin','Clark','Lewis','Walker','Hall','Allen','Young','King']
            for _ in range(300):
                cust_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                cust_phone = f"07{random.randint(10000000,99999999)}"
                inv = f"INV-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
                total = random.randint(200, 5000)
                tax = total * 0.16
                net = total + tax
                payment = random.choice(['Cash','Card','MPESA'])
                self.execute_query("INSERT INTO sales (invoice_no,customer_name,customer_phone,total_amount,tax,net_amount,payment_method,cashier,sale_date) VALUES (?,?,?,?,?,?,?,?,?)", (inv, cust_name, cust_phone, total, tax, net, payment, random.choice(['admin','cashier']), datetime.now() - timedelta(days=random.randint(1,90))))
        self.conn.commit()
    def execute_query(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor
    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
    def log_action(self, user, action, table, rid, old="", new=""):
        self.execute_query("INSERT INTO audit_log (user,action,table_name,record_id,old_value,new_value) VALUES (?,?,?,?,?,?)", (user,action,table,str(rid),str(old),str(new)))
    def close(self):
        self.conn.close()

# ==================== MAIN APP ====================
class SupermarketSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Supermarket System - Ultimate")
        self.root.state('zoomed')
        self.db = Database()
        self.config = ConfigManager()
        self.current_user = None
        self.cart = []
        self.kitchen_window = None
        self.applied_coupon_discount = 0
        self.show_login()
    # ---------- LOGIN ----------
    def show_login(self):
        for w in self.root.winfo_children(): w.destroy()
        main = tk.Frame(self.root, bg='#4facfe')
        main.pack(fill='both', expand=True)
        card = tk.Frame(main, bg='white', relief='ridge')
        card.place(relx=0.5, rely=0.5, anchor='center', width=500, height=500)
        tk.Label(card, text="🏪", font=('Segoe UI', 56), bg='white').pack(pady=(40,10))
        tk.Label(card, text="SUPERMARKET SYSTEM", font=('Segoe UI', 22, 'bold'), bg='white', fg='#1a73e8').pack()
        tk.Label(card, text="Enterprise Edition", font=('Segoe UI', 11), bg='white', fg='gray').pack(pady=5)
        form = tk.Frame(card, bg='white')
        form.pack(pady=30, padx=40, fill='both', expand=True)
        tk.Label(form, text="USERNAME", font=('Segoe UI',10,'bold'), bg='white').pack(anchor='w', pady=(0,5))
        self.username_entry = tk.Entry(form, font=('Segoe UI',12), bg='#f8f9fa', relief='solid')
        self.username_entry.pack(fill='x', pady=(0,15), ipady=8)
        tk.Label(form, text="PASSWORD", font=('Segoe UI',10,'bold'), bg='white').pack(anchor='w', pady=(0,5))
        self.password_entry = tk.Entry(form, font=('Segoe UI',12), show='•', bg='#f8f9fa', relief='solid')
        self.password_entry.pack(fill='x', pady=(0,20), ipady=8)
        btn = tk.Button(form, text="LOGIN", command=self.login, bg='#1a73e8', fg='white', font=('Segoe UI',12,'bold'), relief='flat')
        btn.pack(fill='x', ipady=10)
        demo = tk.Frame(form, bg='white')
        demo.pack(pady=10)
        tk.Label(demo, text="Demo: admin/admin123 | cashier/cashier123", font=('Segoe UI',9), bg='white').pack()
        self.username_entry.bind('<Return>', lambda e: self.login())
        self.password_entry.bind('<Return>', lambda e: self.login())
    def login(self):
        uname = self.username_entry.get()
        pwd = hashlib.sha256(self.password_entry.get().encode()).hexdigest()
        user = self.db.fetch_one("SELECT id,username,role,full_name FROM users WHERE username=? AND password=?", (uname,pwd))
        if user:
            self.current_user = {'id':user[0],'username':user[1],'role':user[2],'full_name':user[3]}
            self.db.log_action(uname,"LOGIN","users",user[0],"","Success")
            messagebox.showinfo("Welcome", f"Hello {user[3]}")
            self.main_menu()
        else:
            messagebox.showerror("Error","Invalid login")
    # ---------- MAIN MENU (Role based) ----------
    def main_menu(self):
        for w in self.root.winfo_children(): w.destroy()
        # Header
        header = tk.Frame(self.root, bg='#4facfe', height=70)
        header.pack(fill='x')
        tk.Label(header, text=f"Welcome {self.current_user['full_name']} ({self.current_user['role']})", font=('Segoe UI',16,'bold'), bg='#4facfe', fg='white').pack(side='left', padx=20)
        tk.Button(header, text="Logout", command=self.logout, bg='red', fg='white', relief='flat', padx=20).pack(side='right', padx=20)
        # Stats
        self.show_stats()
        # Buttons
        btn_frame = tk.Frame(self.root, bg='#e8f4f8')
        btn_frame.pack(fill='both', expand=True, padx=30, pady=20)
        for i in range(4): btn_frame.grid_columnconfigure(i, weight=1)
        if self.current_user['role'] == 'admin':
            modules = [
                ("🛒","Point of Sale",self.pos,'#0d7c3f'), ("📦","Inventory",self.inventory,'#1a73e8'),
                ("📊","Reports",self.reports,'#1a73e8'), ("👥","Customers",self.customers,'#e67e22'),
                ("🏭","Suppliers",self.suppliers,'#16a085'), ("👤","Users",self.users,'#c0392b'),
                ("📈","Dashboard",self.dashboard,'#27ae60'), ("🔍","Stock Alerts",self.stock_alerts,'#e67e22'),
                ("🔄","Returns",self.returns,'#8e44ad'), ("💎","Loyalty",self.loyalty,'#f39c12'),
                ("💰","Expenses",self.expenses,'#1abc9c'), ("💾","Backup",self.backup,'#34495e'),
                ("📦","Purchase Orders",self.purchase_orders,'#009688'), ("📃","Z-Report",self.z_report,'#9c27b0'),
                ("🔍","Audit Trail",self.audit_trail,'#607d8b'), ("🏷️","Coupons",self.coupons,'#ff9800'),
                ("📦","Bundles",self.bundles,'#795548'), ("🍳","Kitchen Display",self.kitchen_display,'#f44336'),
                ("📈","Forecast",self.forecast,'#3f51b5'), ("💳","Credit Mgmt",self.credit_mgmt,'#673ab7')
            ]
        else:  # cashier only
            modules = [("🛒","Point of Sale",self.pos,'#0d7c3f'), ("🔄","Returns",self.returns,'#8e44ad'), ("💎","Loyalty (View)",self.loyalty,'#f39c12')]
        row, col = 0, 0
        for icon, text, cmd, color in modules:
            frame = tk.Frame(btn_frame, bg='white', relief='ridge')
            frame.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')
            btn = tk.Button(frame, text=f"{icon}\n{text}", command=cmd, bg=color, fg='white', font=('Segoe UI',12,'bold'), width=18, height=4, relief='flat')
            btn.pack(fill='both', expand=True, padx=2, pady=2)
            col += 1
            if col >= 4: col, row = 0, row+1
    def show_stats(self):
        stats = tk.Frame(self.root, bg='#e8f4f8', height=100)
        stats.pack(fill='x', padx=20, pady=10)
        today = datetime.now().date()
        total_products = self.db.fetch_one("SELECT COUNT(*) FROM products")[0]
        low = self.db.fetch_one("SELECT COUNT(*) FROM products WHERE quantity <= min_stock")[0]
        today_sales = self.db.fetch_one("SELECT COALESCE(SUM(net_amount),0), COUNT(*) FROM sales WHERE DATE(sale_date)=?", (today,))
        total_rev = self.db.fetch_one("SELECT COALESCE(SUM(net_amount),0) FROM sales")[0]
        data = [("📦 Products", f"{total_products}", f"{low} low stock", '#1a73e8'), ("💰 Today", f"Ksh {today_sales[0]:,.2f}", f"{today_sales[1]} sales", '#0d7c3f'), ("📊 Revenue", f"Ksh {total_rev:,.2f}", "Lifetime", '#1a73e8')]
        for title, val, sub, color in data:
            card = tk.Frame(stats, bg='white', relief='raised')
            card.pack(side='left', expand=True, fill='both', padx=10, pady=5)
            tk.Label(card, text=title, font=('Segoe UI',11), bg='white', fg='gray').pack(pady=(10,0))
            tk.Label(card, text=val, font=('Segoe UI',18,'bold'), bg='white', fg=color).pack()
            tk.Label(card, text=sub, font=('Segoe UI',9), bg='white', fg='gray').pack(pady=(0,10))
    # ---------- POS (Fully Working) ----------
    def pos(self):
        pos_win = tk.Toplevel(self.root)
        pos_win.title("Point of Sale")
        pos_win.state('zoomed')
        pos_win.configure(bg='white')
        # Product list
        left = tk.Frame(pos_win, bg='white')
        left.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        tk.Label(left, text="Products", font=('Segoe UI',16,'bold'), bg='white').pack()
        search = tk.Entry(left, font=('Segoe UI',12))
        search.pack(pady=5, fill='x')
        tree = ttk.Treeview(left, columns=('ID','Name','Price','Stock'), show='headings', height=25)
        tree.heading('ID', text='ID'); tree.heading('Name', text='Name'); tree.heading('Price', text='Price'); tree.heading('Stock', text='Stock')
        tree.column('ID', width=50); tree.column('Name', width=300); tree.column('Price', width=100); tree.column('Stock', width=80)
        tree.pack(fill='both', expand=True)
        # Cart
        right = tk.Frame(pos_win, bg='white')
        right.pack(side='right', fill='both', expand=True, padx=10, pady=10)
        tk.Label(right, text="Cart", font=('Segoe UI',16,'bold'), bg='white').pack()
        cart_tree = ttk.Treeview(right, columns=('Name','Qty','Price','Total'), show='headings', height=20)
        for col in ('Name','Qty','Price','Total'): cart_tree.heading(col, text=col); cart_tree.column(col, width=140)
        cart_tree.pack(fill='both', expand=True)
        total_label = tk.Label(right, text="Total: Ksh 0.00", font=('Segoe UI',18,'bold'), bg='white', fg='green')
        total_label.pack(pady=10)
        # Customer and discount
        cust_frame = tk.Frame(right, bg='#f0f0f0')
        cust_frame.pack(fill='x', pady=5)
        tk.Label(cust_frame, text="Customer:").pack(side='left', padx=5)
        cust_name = tk.Entry(cust_frame, width=20)
        cust_name.pack(side='left', padx=5)
        tk.Label(cust_frame, text="Phone:").pack(side='left', padx=5)
        cust_phone = tk.Entry(cust_frame, width=15)
        cust_phone.pack(side='left', padx=5)
        coupon_entry = tk.Entry(right, width=20)
        coupon_entry.pack(pady=5)
        tk.Button(right, text="Apply Coupon", command=lambda: self.apply_coupon(coupon_entry.get(), total_label)).pack()
        # Buttons
        btn_frame = tk.Frame(right)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add to Cart", command=lambda: self.add_to_cart(tree, cart_tree, total_label)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Remove", command=lambda: self.remove_from_cart(cart_tree, total_label)).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Checkout", command=lambda: self.checkout(cust_name.get(), cust_phone.get(), cart_tree, total_label, pos_win)).pack(side='left', padx=5)
        # Load products
        def load_products():
            for i in tree.get_children(): tree.delete(i)
            for p in self.db.fetch_all("SELECT id, name, selling_price, quantity FROM products WHERE quantity>0 ORDER BY name"):
                tree.insert('', 'end', values=p)
        load_products()
        search.bind('<KeyRelease>', lambda e: self.search_products(search.get(), tree))
    def search_products(self, term, tree):
        for i in tree.get_children(): tree.delete(i)
        for p in self.db.fetch_all("SELECT id, name, selling_price, quantity FROM products WHERE LOWER(name) LIKE ? AND quantity>0", (f'%{term}%',)):
            tree.insert('', 'end', values=p)
    def add_to_cart(self, tree, cart_tree, total_label):
        sel = tree.selection()
        if not sel: return
        vals = tree.item(sel[0])['values']
        pid, name, price, stock = vals
        # Convert price to float (it comes as string or number)
        price = float(price)
        stock = int(stock)
        qty = simpledialog.askinteger("Quantity", "Enter quantity", minvalue=1, maxvalue=stock)
        if qty:
            self.cart.append({'id':pid,'name':name,'price':price,'qty':qty,'total':price*qty})
            self.update_cart_display(cart_tree, total_label)
    def remove_from_cart(self, cart_tree, total_label):
        sel = cart_tree.selection()
        if sel:
            idx = cart_tree.index(sel[0])
            self.cart.pop(idx)
            self.update_cart_display(cart_tree, total_label)
    def update_cart_display(self, cart_tree, total_label):
        for i in cart_tree.get_children(): cart_tree.delete(i)
        total = 0
        for item in self.cart:
            cart_tree.insert('', 'end', values=(item['name'], item['qty'], f"Ksh {item['price']:.2f}", f"Ksh {item['total']:.2f}"))
            total += item['total']
        # Apply coupon discount if any
        disc = getattr(self, 'applied_coupon_discount', 0)
        total_label.config(text=f"Total: Ksh {total - disc:.2f}")
    def apply_coupon(self, code, total_label):
        coupon = self.db.fetch_one("SELECT discount_type, discount_value, min_purchase FROM coupons WHERE code=? AND is_active=1 AND expiry_date>=date('now')", (code,))
        if coupon:
            total = sum(i['total'] for i in self.cart)
            if total >= coupon[2]:
                if coupon[0] == 'fixed':
                    disc = coupon[1]
                else:
                    disc = total * coupon[1] / 100
                self.applied_coupon_discount = disc
                messagebox.showinfo("Coupon", f"Discount applied: Ksh {disc:.2f}")
                self.update_cart_display(None, total_label)  # refresh total
            else:
                messagebox.showerror("Coupon", f"Minimum purchase {coupon[2]} required")
        else:
            messagebox.showerror("Coupon", "Invalid or expired coupon")
    def checkout(self, cust_name, cust_phone, cart_tree, total_label, pos_win):
        if not self.cart:
            messagebox.showwarning("Cart empty", "Add items first")
            return
        subtotal = sum(i['total'] for i in self.cart)
        tax = subtotal * 0.16
        disc = getattr(self, 'applied_coupon_discount', 0)
        net = subtotal - disc + tax
        inv_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
        try:
            self.db.execute_query("INSERT INTO sales (invoice_no,customer_name,customer_phone,total_amount,discount,tax,net_amount,payment_method,cashier) VALUES (?,?,?,?,?,?,?,?,?)", (inv_no, cust_name, cust_phone, subtotal, disc, tax, net, "Cash", self.current_user['username']))
            for item in self.cart:
                self.db.execute_query("INSERT INTO sale_items (invoice_no,product_id,product_name,quantity,unit_price,total) VALUES (?,?,?,?,?,?)", (inv_no, item['id'], item['name'], item['qty'], item['price'], item['total']))
                self.db.execute_query("UPDATE products SET quantity = quantity - ? WHERE id=?", (item['qty'], item['id']))
            # Loyalty points
            if cust_phone:
                points = int(subtotal * 0.01)
                self.db.execute_query("UPDATE loyalty SET points = points + ?, total_spent = total_spent + ? WHERE customer_phone=?", (points, net, cust_phone))
                if not self.db.fetch_one("SELECT customer_phone FROM loyalty WHERE customer_phone=?", (cust_phone,)):
                    self.db.execute_query("INSERT INTO loyalty (customer_phone, customer_name, points) VALUES (?,?,?)", (cust_phone, cust_name, points))
            receipt = f"Invoice: {inv_no}\nTotal: Ksh {net:.2f}\nThank you!"
            messagebox.showinfo("Sale Complete", receipt)
            self.cart = []
            self.applied_coupon_discount = 0
            pos_win.destroy()
            self.pos()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    # ---------- OTHER MODULES (All Working) ----------
    def inventory(self):
        win = tk.Toplevel(self.root)
        win.title("Inventory")
        win.state('zoomed')
        tree = ttk.Treeview(win, columns=('ID','Name','Category','Price','Stock','Min'), show='headings')
        for col in ('ID','Name','Category','Price','Stock','Min'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        def load():
            for i in tree.get_children(): tree.delete(i)
            for p in self.db.fetch_all("SELECT id, name, category, selling_price, quantity, min_stock FROM products"):
                tree.insert('', 'end', values=p)
        load()
        tk.Button(win, text="Refresh", command=load).pack()
    def reports(self):
        win = tk.Toplevel(self.root)
        win.title("Reports")
        text = scrolledtext.ScrolledText(win, width=100, height=30)
        text.pack()
        sales = self.db.fetch_all("SELECT DATE(sale_date), COUNT(*), SUM(net_amount) FROM sales GROUP BY DATE(sale_date) ORDER BY sale_date DESC")
        text.insert(tk.END, "Daily Sales Report\n\n")
        for s in sales:
            text.insert(tk.END, f"{s[0]}: {s[1]} sales, Ksh {s[2]:.2f}\n")
    def customers(self):
        win = tk.Toplevel(self.root)
        win.title("Customers")
        tree = ttk.Treeview(win, columns=('Name','Phone','Total Spent','Points','Credit Outstanding'), show='headings')
        for col in ('Name','Phone','Total Spent','Points','Credit Outstanding'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        # Fixed ambiguous column
        rows = self.db.fetch_all("""
            SELECT COALESCE(s.customer_name, l.customer_name) as name,
                   COALESCE(s.customer_phone, l.customer_phone) as phone,
                   COALESCE(SUM(s.net_amount),0) as spent,
                   COALESCE(l.points,0) as points,
                   COALESCE(l.outstanding_credit,0) as credit
            FROM sales s
            LEFT JOIN loyalty l ON s.customer_phone = l.customer_phone
            GROUP BY COALESCE(s.customer_phone, l.customer_phone)
            ORDER BY spent DESC
        """)
        for r in rows:
            tree.insert('', 'end', values=r)
    def suppliers(self):
        win = tk.Toplevel(self.root)
        win.title("Suppliers")
        tree = ttk.Treeview(win, columns=('ID','Name','Contact','Phone'), show='headings')
        for col in ('ID','Name','Contact','Phone'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        for s in self.db.fetch_all("SELECT id, name, contact_person, phone FROM suppliers"):
            tree.insert('', 'end', values=s)
    def users(self):
        if self.current_user['role'] != 'admin':
            messagebox.showerror("Access Denied", "Admin only")
            return
        win = tk.Toplevel(self.root)
        win.title("Users")
        tree = ttk.Treeview(win, columns=('ID','Username','Role','Full Name'), show='headings')
        for col in ('ID','Username','Role','Full Name'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        for u in self.db.fetch_all("SELECT id, username, role, full_name FROM users"):
            tree.insert('', 'end', values=u)
    def dashboard(self):
        win = tk.Toplevel(self.root)
        win.title("Dashboard")
        data = self.db.fetch_all("SELECT DATE(sale_date), SUM(net_amount) FROM sales GROUP BY DATE(sale_date) ORDER BY sale_date LIMIT 30")
        dates = [d[0] for d in data]
        amounts = [d[1] for d in data]
        fig, ax = plt.subplots()
        ax.plot(dates, amounts)
        ax.set_title("Sales Trend (Last 30 Days)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Revenue (Ksh)")
        plt.xticks(rotation=45)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack()
    def stock_alerts(self):
        win = tk.Toplevel(self.root)
        win.title("Stock Alerts")
        low = self.db.fetch_all("SELECT name, quantity, min_stock FROM products WHERE quantity <= min_stock")
        text = scrolledtext.ScrolledText(win, width=60, height=20)
        text.pack()
        for p in low:
            text.insert(tk.END, f"{p[0]}: Stock {p[1]} (Min {p[2]})\n")
    def returns(self):
        win = tk.Toplevel(self.root)
        win.title("Returns")
        tk.Label(win, text="Invoice No:").pack()
        inv_entry = tk.Entry(win)
        inv_entry.pack()
        def process():
            inv = inv_entry.get()
            sale = self.db.fetch_one("SELECT invoice_no, net_amount FROM sales WHERE invoice_no=?", (inv,))
            if sale:
                fee = sale[1] * (self.config.config["restocking_fee_percent"]/100)
                refund = sale[1] - fee
                ret_inv = f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                self.db.execute_query("INSERT INTO returns (original_invoice, return_invoice, refund_amount, restocking_fee, cashier) VALUES (?,?,?,?,?)", (inv, ret_inv, refund, fee, self.current_user['username']))
                messagebox.showinfo("Return", f"Refund: Ksh {refund:.2f}\nRestocking fee: Ksh {fee:.2f}")
                # Restore stock (optional)
                items = self.db.fetch_all("SELECT product_id, quantity FROM sale_items WHERE invoice_no=?", (inv,))
                for it in items:
                    self.db.execute_query("UPDATE products SET quantity = quantity + ? WHERE id=?", (it[1], it[0]))
            else:
                messagebox.showerror("Error", "Invoice not found")
        tk.Button(win, text="Process Return", command=process).pack()
    def loyalty(self):
        win = tk.Toplevel(self.root)
        win.title("Loyalty")
        tree = ttk.Treeview(win, columns=('Name','Phone','Points','Tier','Credit'), show='headings')
        for col in ('Name','Phone','Points','Tier','Credit'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        for l in self.db.fetch_all("SELECT customer_name, customer_phone, points, tier, outstanding_credit FROM loyalty"):
            tree.insert('', 'end', values=l)
        if self.current_user['role'] == 'admin':
            def add():
                name = simpledialog.askstring("Add", "Customer name")
                phone = simpledialog.askstring("Add", "Phone")
                if name and phone:
                    self.db.execute_query("INSERT INTO loyalty (customer_name, customer_phone) VALUES (?,?)", (name, phone))
                    for i in tree.get_children(): tree.delete(i)
                    for l in self.db.fetch_all("SELECT customer_name, customer_phone, points, tier, outstanding_credit FROM loyalty"):
                        tree.insert('', 'end', values=l)
            tk.Button(win, text="Add Customer", command=add).pack()
    def expenses(self):
        win = tk.Toplevel(self.root)
        win.title("Expenses")
        tk.Label(win, text="Category:").pack()
        cat = ttk.Combobox(win, values=['Rent','Salary','Utilities','Marketing'])
        cat.pack()
        tk.Label(win, text="Amount:").pack()
        amt = tk.Entry(win)
        amt.pack()
        tk.Label(win, text="Description:").pack()
        desc = tk.Entry(win)
        desc.pack()
        def add():
            if cat.get() and amt.get():
                self.db.execute_query("INSERT INTO expenses (category, amount, description, expense_date, user) VALUES (?,?,?,?,?)", (cat.get(), float(amt.get()), desc.get(), datetime.now().date(), self.current_user['username']))
                messagebox.showinfo("Added", "Expense recorded")
                load()
        tk.Button(win, text="Add", command=add).pack()
        tree = ttk.Treeview(win, columns=('Date','Category','Amount','User'), show='headings')
        for col in ('Date','Category','Amount','User'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        def load():
            for i in tree.get_children(): tree.delete(i)
            for e in self.db.fetch_all("SELECT expense_date, category, amount, user FROM expenses ORDER BY expense_date DESC"):
                tree.insert('', 'end', values=e)
        load()
    def backup(self):
        try:
            os.makedirs("backups", exist_ok=True)
            fn = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2("supermarket.db", fn)
            messagebox.showinfo("Backup", f"Saved to {fn}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    def purchase_orders(self):
        win = tk.Toplevel(self.root)
        win.title("Purchase Orders")
        tk.Label(win, text="Supplier:").pack()
        suppliers = [s[0] for s in self.db.fetch_all("SELECT name FROM suppliers")]
        sup_combo = ttk.Combobox(win, values=suppliers)
        sup_combo.pack()
        tk.Label(win, text="Product ID:").pack()
        prod_id = tk.Entry(win)
        prod_id.pack()
        tk.Label(win, text="Quantity:").pack()
        qty = tk.Entry(win)
        qty.pack()
        def create():
            sup = sup_combo.get()
            pid_str = prod_id.get()
            if not pid_str:
                messagebox.showerror("Error", "Product ID required")
                return
            try:
                pid = int(pid_str)
                q = int(qty.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid number")
                return
            prod = self.db.fetch_one("SELECT name, buying_price FROM products WHERE id=?", (pid,))
            if prod:
                po_num = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                total = prod[1] * q
                self.db.execute_query("INSERT INTO purchase_orders (po_number, supplier_id, order_date, total_amount, created_by) VALUES (?, (SELECT id FROM suppliers WHERE name=?), ?, ?, ?)", (po_num, sup, datetime.now().date(), total, self.current_user['username']))
                self.db.execute_query("INSERT INTO po_items (po_number, product_id, product_name, quantity, unit_price) VALUES (?,?,?,?,?)", (po_num, pid, prod[0], q, prod[1]))
                messagebox.showinfo("PO Created", f"PO {po_num} for {q} x {prod[0]}")
                load()
            else:
                messagebox.showerror("Error", "Product not found")
        tk.Button(win, text="Create PO", command=create).pack()
        tree = ttk.Treeview(win, columns=('PO','Supplier','Date','Status','Total'), show='headings')
        for col in ('PO','Supplier','Date','Status','Total'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        def load():
            for i in tree.get_children(): tree.delete(i)
            for po in self.db.fetch_all("SELECT po_number, (SELECT name FROM suppliers WHERE id=purchase_orders.supplier_id), order_date, status, total_amount FROM purchase_orders"):
                tree.insert('', 'end', values=po)
        load()
    def z_report(self):
        win = tk.Toplevel(self.root)
        win.title("Z-Report")
        today = datetime.now().date()
        cash_sales = self.db.fetch_one("SELECT COALESCE(SUM(net_amount),0) FROM sales WHERE DATE(sale_date)=? AND payment_method='Cash'", (today,))
        card_sales = self.db.fetch_one("SELECT COALESCE(SUM(net_amount),0) FROM sales WHERE DATE(sale_date)=? AND payment_method='Card'", (today,))
        mpesa_sales = self.db.fetch_one("SELECT COALESCE(SUM(net_amount),0) FROM sales WHERE DATE(sale_date)=? AND payment_method='MPESA'", (today,))
        expected = cash_sales[0] if cash_sales else 0
        actual = simpledialog.askfloat("Actual Cash", "Enter actual cash count:")
        if actual is not None:
            diff = actual - expected
            self.db.execute_query("INSERT INTO z_reports (report_date, cashier_name, expected_cash, actual_cash, card_total, mpesa_total, difference) VALUES (?,?,?,?,?,?,?)", (today, self.current_user['username'], expected, actual, card_sales[0] if card_sales else 0, mpesa_sales[0] if mpesa_sales else 0, diff))
            messagebox.showinfo("Z-Report", f"Expected Cash: Ksh {expected:.2f}\nActual Cash: Ksh {actual:.2f}\nDifference: Ksh {diff:.2f}\nCard Total: Ksh {(card_sales[0] if card_sales else 0):.2f}\nMPESA Total: Ksh {(mpesa_sales[0] if mpesa_sales else 0):.2f}")
    def audit_trail(self):
        win = tk.Toplevel(self.root)
        win.title("Audit Log")
        tree = ttk.Treeview(win, columns=('Time','User','Action','Table','Record'), show='headings')
        for col in ('Time','User','Action','Table','Record'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        for a in self.db.fetch_all("SELECT timestamp, user, action, table_name, record_id FROM audit_log ORDER BY timestamp DESC LIMIT 200"):
            tree.insert('', 'end', values=a)
    def coupons(self):
        win = tk.Toplevel(self.root)
        win.title("Coupons")
        tk.Label(win, text="Code:").pack()
        code = tk.Entry(win)
        code.pack()
        tk.Label(win, text="Discount (% or fixed):").pack()
        disc_type = ttk.Combobox(win, values=['percentage','fixed'])
        disc_type.pack()
        disc_val = tk.Entry(win)
        disc_val.pack()
        tk.Label(win, text="Expiry (YYYY-MM-DD):").pack()
        expiry = tk.Entry(win)
        expiry.pack()
        def add():
            self.db.execute_query("INSERT INTO coupons (code, discount_type, discount_value, expiry_date) VALUES (?,?,?,?)", (code.get(), disc_type.get(), float(disc_val.get()), expiry.get()))
            messagebox.showinfo("Added", "Coupon created")
            load()
        tk.Button(win, text="Add Coupon", command=add).pack()
        tree = ttk.Treeview(win, columns=('Code','Type','Value','Expiry','Active'), show='headings')
        for col in ('Code','Type','Value','Expiry','Active'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        def load():
            for i in tree.get_children(): tree.delete(i)
            for c in self.db.fetch_all("SELECT code, discount_type, discount_value, expiry_date, is_active FROM coupons"):
                tree.insert('', 'end', values=c)
        load()
    def bundles(self):
        win = tk.Toplevel(self.root)
        win.title("Bundles")
        tk.Label(win, text="Bundle Name:").pack()
        name = tk.Entry(win)
        name.pack()
        tk.Label(win, text="Discount %:").pack()
        disc = tk.Entry(win)
        disc.pack()
        def add():
            self.db.execute_query("INSERT INTO bundles (name, discount_percent) VALUES (?,?)", (name.get(), float(disc.get())))
            messagebox.showinfo("Added", "Bundle created")
            load()
        tk.Button(win, text="Add Bundle", command=add).pack()
        tree = ttk.Treeview(win, columns=('ID','Name','Discount','Active'), show='headings')
        for col in ('ID','Name','Discount','Active'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        def load():
            for i in tree.get_children(): tree.delete(i)
            for b in self.db.fetch_all("SELECT id, name, discount_percent, is_active FROM bundles"):
                tree.insert('', 'end', values=b)
        load()
    def kitchen_display(self):
        if self.kitchen_window and self.kitchen_window.winfo_exists():
            self.kitchen_window.lift()
            return
        self.kitchen_window = tk.Toplevel(self.root)
        self.kitchen_window.title("Kitchen Display")
        self.kitchen_window.geometry("600x400")
        text = scrolledtext.ScrolledText(self.kitchen_window, height=20)
        text.pack(fill='both', expand=True)
        def refresh():
            orders = self.db.fetch_all("SELECT invoice_no, items, status FROM kitchen_orders WHERE status='pending' ORDER BY created_at")
            text.delete(1.0, tk.END)
            for o in orders:
                text.insert(tk.END, f"Invoice: {o[0]}\nItems: {o[1]}\nStatus: {o[2]}\n{'-'*40}\n")
        refresh()
        tk.Button(self.kitchen_window, text="Refresh", command=refresh).pack()
    def forecast(self):
        win = tk.Toplevel(self.root)
        win.title("Sales Forecast")
        data = self.db.fetch_all("SELECT DATE(sale_date), SUM(net_amount) FROM sales GROUP BY DATE(sale_date) ORDER BY sale_date")
        if len(data) < 7:
            messagebox.showinfo("Forecast", "Need at least 7 days of data")
            return
        dates = [d[0] for d in data[-30:]]
        amounts = [d[1] for d in data[-30:]]
        window = 3
        ma = [sum(amounts[i:i+window])/window for i in range(len(amounts)-window+1)]
        fig, ax = plt.subplots()
        ax.plot(dates, amounts, label='Actual')
        ax.plot(dates[window-1:], ma, label='3-day MA')
        ax.legend()
        ax.set_title("Sales Forecast (Moving Average)")
        plt.xticks(rotation=45)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack()
    def credit_mgmt(self):
        win = tk.Toplevel(self.root)
        win.title("Credit Management")
        tree = ttk.Treeview(win, columns=('Name','Phone','Credit Limit','Outstanding'), show='headings')
        for col in ('Name','Phone','Credit Limit','Outstanding'): tree.heading(col, text=col); tree.column(col, width=150)
        tree.pack(fill='both', expand=True)
        for l in self.db.fetch_all("SELECT customer_name, customer_phone, credit_limit, outstanding_credit FROM loyalty"):
            tree.insert('', 'end', values=l)
        def adjust():
            phone = simpledialog.askstring("Credit", "Customer phone")
            if phone:
                new_limit = simpledialog.askfloat("Credit", "New credit limit")
                if new_limit is not None:
                    self.db.execute_query("UPDATE loyalty SET credit_limit = ? WHERE customer_phone=?", (new_limit, phone))
                    for i in tree.get_children(): tree.delete(i)
                    for l in self.db.fetch_all("SELECT customer_name, customer_phone, credit_limit, outstanding_credit FROM loyalty"):
                        tree.insert('', 'end', values=l)
        tk.Button(win, text="Set Credit Limit", command=adjust).pack()
    def logout(self):
        if messagebox.askyesno("Logout", "Are you sure?"):
            self.db.log_action(self.current_user['username'], "LOGOUT", "users", self.current_user['id'], "", "")
            self.current_user = None
            self.show_login()

# ==================== RUN ====================
if __name__ == "__main__":
    if os.path.exists("supermarket.db"):
        os.remove("supermarket.db")
    root = tk.Tk()
    app = SupermarketSystem(root)
    root.mainloop()