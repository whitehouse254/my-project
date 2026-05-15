import sqlite3

conn = sqlite3.connect('resume_optimizer.db')
c = conn.cursor()

sources = ['JSearch', 'RemoteOK', 'Himalayas', 'Adzuna', 'Indeed', 'Demo']
for source in sources:
    count = c.execute('SELECT COUNT(*) FROM jobs WHERE source=? AND is_active=1', (source,)).fetchone()[0]
    print(f'{source}: {count} jobs')

conn.close()