# update_db.py
import sqlite3

def update_schema():
    conn = sqlite3.connect('website/database.db')
    cursor = conn.cursor()
    
    try:
        # Add is_deleted column to post table
        cursor.execute("ALTER TABLE post ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
        print("✅ Success: 'is_deleted' column added to Post table.")
    except sqlite3.OperationalError:
        print("ℹ️ Note: 'is_deleted' column already exists.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_schema()