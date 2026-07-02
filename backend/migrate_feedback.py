import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "fraud_wallet_v2.db")
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE wallet_scans ADD COLUMN user_feedback INTEGER;")
        conn.commit()
        print("Migration successful: user_feedback added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists.")
        else:
            print(f"Error migrating: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
