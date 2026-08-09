from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(override=True)

app = Flask(__name__)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Today's Sales
    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS today_sales
        FROM sales
        WHERE DATE(sale_date) = CURDATE()
    """)
    today_sales = cursor.fetchone()["today_sales"]

    # Today's Profit
    cursor.execute("""
        SELECT COALESCE(
            SUM((selling_price - cost_price) * quantity), 0
        ) AS today_profit
        FROM sale_items
        JOIN sales
            ON sale_items.sale_id = sales.sale_id
        WHERE DATE(sales.sale_date) = CURDATE()
    """)
    today_profit = cursor.fetchone()["today_profit"]

    # Pending Udhaar
    cursor.execute("""
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN transaction_type = 'CREDIT' THEN amount
                    WHEN transaction_type = 'PAYMENT' THEN -amount
                    ELSE 0
                END
            ), 0
        ) AS pending_credit
        FROM credit_transactions
    """)
    pending_credit = cursor.fetchone()["pending_credit"]

    # Low Stock
    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE stock_qty <= low_stock_threshold
        AND is_active = TRUE
    """)
    low_stock = cursor.fetchone()["low_stock"]

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        today_profit=today_profit,
        pending_credit=pending_credit,
        low_stock=low_stock
    )


# =========================
# INVENTORY
# =========================

@app.route("/inventory")
def inventory():

    search = request.args.get("search", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if search:

        cursor.execute("""
            SELECT *
            FROM products
            WHERE vendor_id = 1
            AND is_active = TRUE
            AND (
                name LIKE %s
                OR category LIKE %s
            )
            ORDER BY product_id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT *
            FROM products
            WHERE vendor_id = 1
            AND is_active = TRUE
            ORDER BY product_id DESC
        """)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "inventory.html",
        products=products,
        search=search
    )


# =========================
# ADD PRODUCT
# =========================

@app.route("/inventory/add", methods=["POST"])
def add_product():

    name = request.form["name"]
    category = request.form.get("category")
    unit = request.form["unit"]

    stock_qty = float(request.form["stock_qty"])
    purchase_price = float(request.form["purchase_price"])
    selling_price = float(request.form["selling_price"])

    low_stock_threshold = float(
        request.form.get("low_stock_threshold", 5)
    )

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO products
        (
            vendor_id,
            name,
            category,
            unit,
            stock_qty,
            purchase_price,
            selling_price,
            low_stock_threshold,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
    """, (
        1,
        name,
        category,
        unit,
        stock_qty,
        purchase_price,
        selling_price,
        low_stock_threshold
    ))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("inventory"))


'''edit product'''

@app.route("/inventory/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        category = request.form.get("category")
        unit = request.form["unit"]

        stock_qty = float(request.form["stock_qty"])
        purchase_price = float(request.form["purchase_price"])
        selling_price = float(request.form["selling_price"])

        low_stock_threshold = float(
            request.form.get("low_stock_threshold", 5)
        )

        cursor.execute("""
            UPDATE products
            SET
                name = %s,
                category = %s,
                unit = %s,
                stock_qty = %s,
                purchase_price = %s,
                selling_price = %s,
                low_stock_threshold = %s
            WHERE product_id = %s
            AND vendor_id = 1
        """, (
            name,
            category,
            unit,
            stock_qty,
            purchase_price,
            selling_price,
            low_stock_threshold,
            product_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("inventory"))

    cursor.execute("""
        SELECT *
        FROM products
        WHERE product_id = %s
        AND vendor_id = 1
        AND is_active = TRUE
    """, (product_id,))

    product = cursor.fetchone()

    cursor.close()
    connection.close()

    if product is None:
        return "Product not found", 404

    return render_template(
        "edit_product.html",
        product=product
    )


# =========================
# DELETE PRODUCT
# =========================

@app.route("/inventory/delete/<int:product_id>")
def delete_product(product_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE products
        SET is_active = FALSE
        WHERE product_id = %s
        AND vendor_id = 1
    """, (product_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("inventory"))


# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)