
import sqlite3

def connect_database():
    connection = sqlite3.connect("laundry.db")
    return connection

def create_table():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            customer_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            service TEXT NOT NULL,
            weight REAL NOT NULL,
            total_amount REAL NOT NULL,
            amount_paid REAL NOT NULL,
            change_amount REAL NOT NULL,
            status TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in cursor.fetchall()]

    if "due_date" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN due_date TEXT")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

def save_order(order):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO orders (
            order_id,
            customer_name,
            contact_number,
            service,
            weight,
            total_amount,
            amount_paid,
            change_amount,
            status,
            due_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order["order_id"],
        order["customer_name"],
        order["contact_number"],
        order["service"],
        order["weight"],
        order["total_amount"],
        order["amount_paid"],
        order["change"],
        order["status"],
        order["due_date"]
    ))

    connection.commit()
    connection.close()

def get_next_order_id():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("SELECT MAX(id) FROM orders")

    last_id = cursor.fetchone()[0]

    connection.close()

    next_id = 1 if last_id is None else last_id + 1

    return f"LS-{next_id:03d}"

def get_all_orders():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            order_id,
            customer_name,
            contact_number,
            service,
            weight,
            total_amount,
            amount_paid,
            change_amount,
            status,
            due_date
        FROM orders
        ORDER BY id DESC
    """)

    orders = cursor.fetchall()

    connection.close()

    return orders
    connection.commit()
    connection.close()


create_table()

def search_order(order_id):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            order_id,
            customer_name,
            contact_number,
            service,
            weight,
            total_amount,
            amount_paid,
            change_amount,
            status,
            due_date
        FROM orders
        WHERE order_id = ?
    """, (order_id,))

    order = cursor.fetchone()

    connection.close()

    return order

def update_order_status(order_id, new_status):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = ?
        WHERE order_id = ?
    """, (new_status, order_id))

    connection.commit()

    updated = cursor.rowcount > 0

    connection.close()

    return updated

def get_sales_report():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_amount) FROM orders")
    total_sales = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(amount_paid) FROM orders")
    total_payments = cursor.fetchone()[0] or 0

    connection.close()

    return total_orders, total_sales, total_payments

def count_customer_orders(customer_name):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE LOWER(customer_name) = LOWER(?)
    """, (customer_name,))

    total_orders = cursor.fetchone()[0]

    connection.close()

    return total_orders

def save_payment(order_id, amount):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO payments (order_id, amount)
        VALUES (?, ?)
    """, (order_id, amount))

    connection.commit()
    connection.close()

def get_payment_history(order_id):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT amount, payment_date
        FROM payments
        WHERE order_id = ?
        ORDER BY id ASC
    """, (order_id,))

    payments = cursor.fetchall()

    connection.close()

    return payments

def update_order_payment(order_id, new_amount_paid):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE orders
        SET amount_paid = ?, change_amount = 0
        WHERE order_id = ?
    """, (new_amount_paid, order_id))

    connection.commit()
    connection.close()

def get_payment_status(order_id):

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT total_amount, amount_paid
        FROM orders
        WHERE order_id = ?
    """, (order_id,))

    order = cursor.fetchone()

    connection.close()

    if order is None:
        return "Order Not Found"

    total_amount = order[0]
    amount_paid = order[1]

    if amount_paid <= 0:
        return "Unpaid"

    elif amount_paid < total_amount:
        return "Partially Paid"

    else:
        return "Fully Paid"    

def get_payment_summary():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            SUM(total_amount - amount_paid),
            SUM(CASE WHEN amount_paid >= total_amount THEN 1 ELSE 0 END),
            SUM(CASE WHEN amount_paid > 0 AND amount_paid < total_amount THEN 1 ELSE 0 END),
            SUM(CASE WHEN amount_paid <= 0 THEN 1 ELSE 0 END)
        FROM orders
    """)

    summary = cursor.fetchone()

    connection.close()

    return summary    

def get_sales_summary():

    connection = connect_database()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            COALESCE(SUM(total_amount), 0),
            COALESCE(SUM(amount_paid), 0),
            COALESCE(SUM(total_amount - amount_paid), 0)
        FROM orders
    """)

    summary = cursor.fetchone()

    connection.close()

    return summary