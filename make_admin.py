import sqlite3

email = input("Enter your email address: ")

conn = sqlite3.connect('resume_optimizer.db')
cursor = conn.cursor()

cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
conn.commit()

if cursor.rowcount > 0:
    print(f"✅ {email} is now an admin.")
else:
    print(f"❌ No user found with email {email}. Make sure you registered first.")

conn.close()