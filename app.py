
from flask import Flask, render_template, request, redirect, url_for, flash
import database
from datetime import date

app = Flask(__name__)
app.secret_key = "laundry_system_secret_key"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/new-order")
def new_order():
    return render_template("new_order.html")


@app.route("/add-order", methods=["POST"])
def add_order():

    customer_name = request.form.get("customer_name", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    service = request.form.get("service", "")
    due_date = request.form.get("due_date", "")

    try:
        weight = float(request.form.get("weight", 0))
    except ValueError:
        flash("Invalid weight!")
        return redirect(url_for("new_order"))

    if not customer_name or not contact_number or not service or not due_date:
        flash("Please complete all fields!")
        return redirect(url_for("new_order"))

    if not contact_number.isdigit():
        flash("Contact number must contain numbers only!")
        return redirect(url_for("new_order"))

    if weight <= 0:
        flash("Weight must be greater than zero!")
        return redirect(url_for("new_order"))

    if service == "Wash Only":
        rate = 30
    elif service == "Wash and Dry":
        rate = 40
    elif service == "Wash, Dry and Fold":
        rate = 50
    else:
        flash("Invalid service selected!")
        return redirect(url_for("new_order"))

    if due_date < date.today().isoformat():
        flash("Due date cannot be in the past!")
        return redirect(url_for("new_order"))

    total_amount = weight * rate

    order = {
        "order_id": database.get_next_order_id(),
        "customer_name": customer_name,
        "contact_number": contact_number,
        "service": service,
        "weight": weight,
        "total_amount": total_amount,
        "amount_paid": 0,
        "change": 0,
        "status": "Waiting",
        "due_date": due_date
    }

    try:
        database.save_order(order)
    except Exception:
        flash("Unable to save order. Please try again.")
        return redirect(url_for("new_order"))

    flash(f"Order {order['order_id']} successfully saved!")
    return redirect(url_for("home"))

@app.route("/orders")
def orders():

    all_orders = database.get_all_orders()

    today = date.today().isoformat()

    return render_template(
        "orders.html",
        orders=all_orders,
        today=today
    )

@app.route("/order/<order_id>")
def order_details(order_id):

    order = database.search_order(order_id)

    if order:
        return render_template("order_details.html", order=order)

    return "Order not found", 404

@app.route("/search", methods=["GET", "POST"])
def search():

    order = None

    if request.method == "POST":

        order_id = request.form.get("order_id").strip().upper()

        order = database.search_order(order_id)

    return render_template("search.html", order=order)

@app.route("/payments", methods=["GET", "POST"])
def payments():

    order = None
    message = None
    payment_history = []

    if request.method == "POST":

        order_id = request.form.get("order_id", "").strip().upper()

        order = database.search_order(order_id)

        if order:

            total_amount = order[5]
            amount_paid = order[6]
            remaining_balance = total_amount - amount_paid

            payment_input = request.form.get("payment", "").strip()

            if payment_input:

                try:
                    payment = float(payment_input)

                    if payment <= 0 or payment > remaining_balance:
                        message = "Invalid payment amount!"

                    else:
                        new_amount_paid = amount_paid + payment

                        database.save_payment(order_id, payment)
                        database.update_order_payment(order_id, new_amount_paid)

                        message = "Payment successfully recorded!"

                        order = database.search_order(order_id)

                except ValueError:
                    message = "Please enter a valid payment amount."

            payment_history = database.get_payment_history(order_id)

        else:
            message = "Order not found."

    return render_template(
        "payments.html",
        order=order,
        message=message,
        payment_history=payment_history
    )

@app.route("/sales-report")
def sales_report():

    summary = database.get_sales_summary()

    return render_template("sales_report.html", summary=summary)

@app.route("/update-status", methods=["GET", "POST"])
def update_status():

    message = None

    if request.method == "POST":

        order_id = request.form.get("order_id", "").strip().upper()
        new_status = request.form.get("new_status", "").strip()

        order = database.search_order(order_id)

        if not order:
            message = "Order not found!"

        elif order[8] == "Waiting" and new_status == "Processing":

            database.update_order_status(order_id, new_status)
            message = "Order status successfully updated!"

        elif order[8] == "Processing" and new_status == "Ready":

            database.update_order_status(order_id, new_status)
            message = "Order status successfully updated!"

        else:
            message = "Invalid status transition!"

    return render_template("update_status.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)