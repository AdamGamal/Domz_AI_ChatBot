import sqlite3
import csv

def create_database(db_file):
    """Create a SQLite database and the products table."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price TEXT,
            description TEXT,
            colors TEXT,
            sizes TEXT,
            stock_status TEXT,
            url TEXT
            
        );
    """)
    conn.commit()
    conn.close()

def insert_products_from_csv(db_file, csv_file):
    """Insert products from a CSV file into the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cursor.execute("""
                INSERT OR IGNORE INTO products (name, price, description, colors, sizes, stock_status, url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get('name', 'Unknown'),
                row.get('price', 'Unknown'),
                row.get('description', 'Unknown'),
                row.get('colors', 'no available colors'),
                row.get('sizes', 'no available sizes'),
                row.get('stock_status', 'out of'),
                row.get('url', 'Unknown')
                
            ))
    conn.commit()
    conn.close()

def fetch_products_by_name(database_path, product_name):
    """Fetch products from the database that match the given product name."""
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        # Prepare a SQL query to search for products by name
        query = """
        SELECT id, name, price, description, colors, sizes, stock_status, url
        FROM products
        WHERE name LIKE ?
        """
        # Execute the query using wildcard for partial match
        cursor.execute(query, ('%' + product_name + '%',))
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []  # Return an empty list in case of error
    finally:
        conn.close()

def fetch_all_products(db_file):
    """Fetch and display all products from the database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    conn.close()

if __name__ == "__main__":
    db_file = "ecommerce_products.db"
    csv_file = "scraper/products.csv" 
    create_database(db_file)
    insert_products_from_csv(db_file, csv_file)
    fetch_all_products(db_file)
