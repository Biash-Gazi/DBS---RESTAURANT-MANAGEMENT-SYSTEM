# Import necessary libraries
from flask import Flask, render_template, request, redirect, session, jsonify
import cx_Oracle

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'secret123'  # Secret key for session management

# Database connection function
def get_db_connection():
    dsn = cx_Oracle.makedsn('localhost', 1521, service_name='xe')  # Change as per your DB settings
    conn = cx_Oracle.connect(user='SYSTEM', password='RAYAN123', dsn=dsn)
    return conn

# Home Route
@app.route('/')
def home():
    return render_template('home.html')

# Admin Login Route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pin = request.form['pin']
        if pin == '1234':
            return redirect('/admin_dashboard')
        else:
            return "Access Denied! Incorrect PIN."
    return render_template('admin_login.html')

# Admin Dashboard Route
@app.route('/admin_dashboard')
def admin_dashboard():
    return render_template('admin_dashboard.html')

# Add Item to Menu
@app.route('/add_item')
def add_item():
    return render_template('add_item.html')

# Delete Item from Menu
@app.route('/delete_item')
def delete_item():
    return render_template('delete_item.html')

# View Orders
@app.route('/view_orders')
def view_orders():
    return render_template('view_orders.html')

# Find Most Popular Menu Item
@app.route('/popular_item')
def popular_item():
    return render_template('popular_item.html')

# User Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO Users (name, password) VALUES (:1, :2)", (name, password))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/login')
    return render_template('signup.html')


# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM Users WHERE name=:1 AND password=:2", (name, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session['user'] = user[0]
            return redirect('/menu')  # Redirecting to '/menu' which will show the menu page
        return "Invalid Credentials!"
    return render_template('login.html')

# Fetch Menu Items (Returns JSON) - Changed route name
@app.route('/menu-data', methods=['GET'])
def get_menu_data():
    conn = get_db_connection()
    cur = conn.cursor()
    # Updated query to include category join
    cur.execute("""
        SELECT m.item_id, m.name, m.price, c.title AS category
        FROM Menu m
        JOIN Category c ON m.category_id = c.category_id
    """)
    menu_items = [{"item_id": row[0], "name": row[1], "price": row[2], "category": row[3]} for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(menu_items)  # Return JSON for frontend

# Render the Menu Page
@app.route('/menu', methods=['GET'])  # New route for rendering the menu page
def menu():
    return render_template('menu.html')  # Renders the menu.html

# Order Page Route
@app.route('/order', methods=['POST'])
def place_order():
    try:
        # Get data sent from frontend
        order_data = request.get_json()
        user_id = session.get('user')
        item_id = order_data['item_id']
        quantity = int(order_data['quantity'])

        conn = get_db_connection()
        cur = conn.cursor()

        # Retrieve the price for the selected item_id
        cur.execute("SELECT price FROM Menu WHERE item_id = :1", (item_id,))
        price_row = cur.fetchone()
        if price_row is None:
            return "Item not found.", 404  # Handle case where item_id doesn't exist

        price = price_row[0]
        total_price = quantity * price  # Calculate total price based on quantity and item price

        # Insert the order record; order_id will auto-increment due to trigger
        cur.execute("INSERT INTO Orders (user_id, status) VALUES (:1, 'Pending')", (user_id,))

        # Get the last inserted order_id from the sequence
        cur.execute("SELECT Orders_seq.CURRVAL FROM dual")
        order_id = cur.fetchone()[0]

        # Insert order details for the specific item and quantity
        cur.execute("INSERT INTO Order_Details (order_id, item_id, quantity, total_price) VALUES (:1, :2, :3, :4)",
                    (order_id, item_id, quantity, total_price))

        conn.commit()
        return "Order Placed Successfully!"
    except Exception as e:
        print(f"Error occurred while placing order: {str(e)}")
        return "An error occurred while placing your order.", 500
    finally:
        if 'cur' in locals() and cur is not None:
            cur.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

# Book Table Page Route
@app.route('/book_table', methods=['GET'])
def book_table_page():
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetching available reservations
    cur.execute("SELECT table_id, status, seater FROM Reservations WHERE status = 'Available'")
    tables = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('book_table.html', tables=tables)

@app.route('/reserve_table', methods=['POST'])
def reserve_table():
    try:
        table_data = request.get_json()
        table_id = table_data['table_id']
        user_id = session.get('user')  # Get user_id from session if needed

        conn = get_db_connection()
        cur = conn.cursor()

        # Update the reservation status to 'Reserved'
        cur.execute("UPDATE Reservations SET status = 'Reserved' WHERE table_id = :1", (table_id,))
        conn.commit()

        return "Table reserved successfully!"
    except Exception as e:
        return f"An error occurred: {str(e)}", 500
    finally:
        if 'cur' in locals() and cur is not None:
            cur.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

@app.route('/generate_bill', methods=['GET'])
def generate_bill():
    user_id = session.get('user')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT SUM(total_price) FROM Order_Details d JOIN Orders o ON d.order_id = o.order_id WHERE o.user_id = :1", (user_id,))
        total = cur.fetchone()[0] or 0  # Handle case where there are no orders

        return jsonify({"total": total})
    except Exception as e:
        return f"An error occurred: {str(e)}", 500
    finally:
        if 'cur' in locals() and cur is not None:
            cur.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
