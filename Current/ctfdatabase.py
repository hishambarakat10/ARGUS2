import sqlite3

# Connect to the database (it will create it if it doesn't exist)
conn = sqlite3.connect('ctf.db')
cursor = conn.cursor()

# Create the 'users' table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
''')

# Insert a default user if the table is empty (prevent duplicates)
cursor.execute("INSERT OR IGNORE INTO users (username, password) VALUES ('admin', 'supersecure')")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and users table created successfully!")
