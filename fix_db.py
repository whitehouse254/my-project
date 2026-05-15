import sqlite3

conn = sqlite3.connect('resume_optimizer.db')
cursor = conn.cursor()

# Add missing columns to jobs table
columns_to_add = [
    ('is_featured', 'INTEGER DEFAULT 0'),
    ('salary_min', 'INTEGER'),
    ('salary_max', 'INTEGER'),
    ('currency', 'TEXT DEFAULT "USD"'),
    ('experience_level', 'TEXT'),
    ('requirements', 'TEXT'),
    ('benefits', 'TEXT'),
    ('views_count', 'INTEGER DEFAULT 0'),
    ('applications_count', 'INTEGER DEFAULT 0'),
    ('industry', 'TEXT'),
    ('deadline', 'DATE'),
    ('company_size', 'TEXT'),
    ('employer_id', 'INTEGER')
]

for col_name, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
        print(f"✅ Added column: {col_name}")
    except:
        print(f"⚠️ Column {col_name} already exists or error")

conn.commit()
conn.close()
print("\n✅ Database fixed!")