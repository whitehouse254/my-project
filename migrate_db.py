import sqlite3

conn = sqlite3.connect('resume_optimizer.db')
c = conn.cursor()

# Check and add avatar column
try:
    c.execute("ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT 'default.png'")
    print("✅ Added 'avatar' column to users table")
except sqlite3.OperationalError:
    print("Column 'avatar' already exists")

# Check and add other possible missing columns
columns_to_add = [
    ("totp_secret", "TEXT"),
    ("totp_enabled", "INTEGER DEFAULT 0"),
    ("email_notifications", "INTEGER DEFAULT 1"),
]

for col_name, col_type in columns_to_add:
    try:
        c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        print(f"✅ Added '{col_name}' column")
    except sqlite3.OperationalError:
        print(f"Column '{col_name}' already exists")

conn.commit()
conn.close()
print("Migration complete!")