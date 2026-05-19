


# 🛒 Victor's Supermarket Management System
A full‑featured, desktop‑based Point of Sale (POS) and inventory management system for supermarkets.  
Built with Python (Tkinter + SQLite) – green theme, role‑based access, 500+ products, sales reports, barcode printing .

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![SQLite](https://img.shields.io/badge/Database-SQLite-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📸 Screenshots
| Login | Main Menu | Point of Sale |
|-------|-----------|---------------|
| <img width="1357" height="640" alt="Screenshot 2026-05-19 205659" src="https://github.com/user-attachments/assets/0d2b8db8-00c9-4589-a912-d1e11aee04b7" /> | <img width="1346" height="642" alt="Screenshot 2026-05-19 205637" src="https://github.com/user-attachments/assets/3755c34a-716d-4e68-a268-616bf38bdb38" /> | <img width="1348" height="633" alt="Screenshot 2026-05-19 205520" src="https://github.com/user-attachments/assets/3f549a12-c434-4993-a516-7ad505c3b879" /> |

---

##  Features
- **Secure login** with roles: **Admin** (full control) and **Cashier** (POS only)
- **Point of Sale** – search products, scan barcode, add to cart, apply discount, print receipt
- **Inventory Management** – add, edit, delete products; low stock alerts; export to CSV
- **500+ pre‑loaded products** with realistic names, categories, and prices
- **Sales Reports** – daily sales, top products, payment method breakdown
- **Customer & Supplier Management** – track customer spending, manage supplier contacts
- **User Management** (admin only) – create/modify users, assign roles
- **Loyalty Program** – register customers, collect points, tier levels
- **Expense Tracking** – record operating costs, view total expenses
- **Returns Processing** – refund items with restocking fee
- **Barcode Printing** – generate printable barcodes for any product
- **Automatic Database Backup** – scheduled daily backup (configurable)
- **Advanced Charts** – sales trend graph, category revenue pie chart
- **Green Theme** – pleasant, consistent green colour palette
  
---

##  Technology Stack
| Component       | Technology                       |
|----------------|----------------------------------|
| Language       | Python 3.8+                      |
| GUI Framework  | Tkinter (built‑in)               |
| Database       | SQLite (no separate server)      |
| Charts         | Matplotlib                       |
| Barcode        | `python-barcode` + Pillow        |
| Scheduling     | `schedule`                       |
| Authentication | SHA‑256 + salt (no external auth)|

---

##  Installation
### 1. Clone the repository (or download the `.py` file)

```bash
git clone https://github.com/yourusername/supermarket-system.git
cd supermarket-system
