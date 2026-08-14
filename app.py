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

    # =========================
    # TODAY'S SALES
    # =========================

    cursor.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS today_sales
        FROM sales
        WHERE vendor_id = 1
        AND DATE(sale_date) = CURDATE()
    """)

    today_sales = cursor.fetchone()["today_sales"]


    # =========================
    # TODAY'S GROSS PROFIT
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM((selling_price - cost_price) * quantity),
            0
        ) AS today_profit
        FROM sale_items
        JOIN sales
            ON sale_items.sale_id = sales.sale_id
        WHERE sales.vendor_id = 1
        AND DATE(sales.sale_date) = CURDATE()
    """)

    today_profit = cursor.fetchone()["today_profit"]


    # =========================
    # PENDING UDHAR
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN transaction_type = 'CREDIT'
                        THEN amount
                    WHEN transaction_type = 'PAYMENT'
                        THEN -amount
                    ELSE 0
                END
            ),
            0
        ) AS pending_credit
        FROM credit_transactions
        WHERE vendor_id = 1
    """)

    pending_credit = cursor.fetchone()["pending_credit"]


    # =========================
    # LOW STOCK
    # =========================

    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE vendor_id = 1
        AND stock_qty <= low_stock_threshold
    """)

    low_stock = cursor.fetchone()["low_stock"]


    # =========================
    # TODAY'S EXPENSES
    # =========================

    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0) AS today_expenses
        FROM expenses
        WHERE vendor_id = 1
        AND DATE(expense_date) = CURDATE()
    """)

    today_expenses = cursor.fetchone()["today_expenses"]


    # =========================
    # VENDOR PROFILE
    # =========================

    cursor.execute("""
        SELECT name
        FROM vendors
        WHERE vendor_id = 1
    """)

    vendor = cursor.fetchone()

    vendor_name = vendor["name"] if vendor else "Shop Owner"


    # =========================
    # CLOSE DATABASE
    # =========================

    cursor.close()
    connection.close()


    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        today_profit=today_profit,
        pending_credit=pending_credit,
        low_stock=low_stock,
        today_expenses=today_expenses,
        vendor_name=vendor_name
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


@app.route("/sales")
def sales():

    success = request.args.get("success")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Available products
    cursor.execute("""
        SELECT
            product_id,
            name,
            selling_price,
            stock_qty,
            unit
        FROM products
        WHERE vendor_id = 1
        AND stock_qty > 0
        ORDER BY name
    """)

    products = cursor.fetchall()

    # Customers
    cursor.execute("""
        SELECT
            customer_id,
            name
        FROM customers
        WHERE vendor_id = 1
        ORDER BY name
    """)

    customers = cursor.fetchall()

    # Recent Sales
    cursor.execute("""
        SELECT
            s.sale_id,
            s.sale_date,
            s.total_amount,
            s.payment_method,
            COALESCE(c.name, 'Walk-in Customer') AS customer_name
        FROM sales s
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        WHERE s.vendor_id = 1
        ORDER BY s.sale_id DESC
        LIMIT 10
    """)

    recent_sales = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "sales.html",
        products=products,
        customers=customers,
        recent_sales=recent_sales,
        success=success
    )
@app.route("/sales/create", methods=["POST"])
def create_sale():

    product_id = int(request.form["product_id"])
    quantity = float(request.form["quantity"])
    payment_method = request.form["payment_method"]

    customer_id = request.form.get("customer_id")

    if payment_method == "CREDIT" and not customer_id:
        return "Customer is required for Udhaar sale", 400

    # Empty customer = Walk-in customer
    if not customer_id:
        customer_id = None
    else:
        customer_id = int(customer_id)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # =========================
        # 1. GET PRODUCT
        # =========================

        # 1. GET PRODUCT

        cursor.execute("""
            SELECT
                product_id,
                name,
                stock_qty,
                selling_price,
                purchase_price
            FROM products
            WHERE product_id = %s
            AND vendor_id = 1
        """, (product_id,))

        product = cursor.fetchone()

        if product is None:
            return "Product not found", 404


        # =========================
        # 2. VALIDATE QUANTITY
        # =========================

        if quantity <= 0:
            return "Invalid quantity", 400

        if product["stock_qty"] < quantity:
            return "Not enough stock available", 400


        # =========================
        # 3. CALCULATE AMOUNTS
        # =========================

        selling_price = float(product["selling_price"])
        cost_price = float(product["purchase_price"])

        subtotal = selling_price * quantity
        total_amount = subtotal


        # =========================
        # 4. CREATE SALE
        # =========================

        cursor.execute("""
            INSERT INTO sales
            (
                vendor_id,
                customer_id,
                total_amount,
                payment_method
            )
            VALUES (%s, %s, %s, %s)
        """, (
            1,
            customer_id,
            total_amount,
            payment_method
        ))

        sale_id = cursor.lastrowid


        # =========================
        # 5. CREATE SALE ITEM
        # =========================

        cursor.execute("""
            INSERT INTO sale_items
            (
                sale_id,
                product_id,
                quantity,
                selling_price,
                cost_price,
                subtotal
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            sale_id,
            product_id,
            quantity,
            selling_price,
            cost_price,
            subtotal
        ))



# =========================
# 6. CREATE UDHAR TRANSACTION
# =========================

        if payment_method == "CREDIT" and customer_id is not None:

            cursor.execute("""
                INSERT INTO credit_transactions
                (
                    vendor_id,
                    customer_id,
                    sale_id,
                    transaction_type,
                    amount,
                    notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                1,
                customer_id,
                sale_id,
                "CREDIT",
                total_amount,
                "Credit from sale"
            ))
        # =========================
        # 6. REDUCE STOCK
        # =========================

        cursor.execute("""
            UPDATE products
            SET stock_qty = stock_qty - %s
            WHERE product_id = %s
            AND vendor_id = 1
        """, (
            quantity,
            product_id
        ))


        # =========================
        # 7. SAVE EVERYTHING
        # =========================

        connection.commit()

        return redirect(
            url_for("sales", success="Sale completed successfully!")
        )


    except Exception as e:

        connection.rollback()

        return f"Sale failed: {e}", 500


    finally:

        cursor.close()
        connection.close()



# =========================
# CUSTOMERS
# =========================

@app.route("/customers")
def customers():

    search = request.args.get("search", "").strip()
    success = request.args.get("success")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if search:

        cursor.execute("""
            SELECT
                customer_id,
                name,
                phone,
                address,
                created_at
            FROM customers
            WHERE vendor_id = 1
            AND (
                name LIKE %s
                OR phone LIKE %s
            )
            ORDER BY customer_id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT
                customer_id,
                name,
                phone,
                address,
                created_at
            FROM customers
            WHERE vendor_id = 1
            ORDER BY customer_id DESC
        """)

    customer_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "customer.html",
        customers=customer_list,
        search=search,
        success=success
    )


# =========================
# ADD CUSTOMER
# =========================

@app.route("/customers/add", methods=["POST"])
def add_customer():

    name = request.form["name"].strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not name:
        return "Customer name is required", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO customers
            (
                vendor_id,
                name,
                phone,
                address
            )
            VALUES (%s, %s, %s, %s)
        """, (
            1,
            name,
            phone if phone else None,
            address if address else None
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()
        return f"Customer creation failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(
        url_for(
            "customers",
            success="Customer added successfully!"
        )
    )


# =========================
# DELETE CUSTOMER
# =========================

@app.route("/customers/delete/<int:customer_id>")
def delete_customer(customer_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM customers
            WHERE customer_id = %s
            AND vendor_id = 1
        """, (customer_id,))

        connection.commit()

    except Exception as e:

        connection.rollback()
        return f"Customer deletion failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(
        url_for(
            "customers",
            success="Customer deleted successfully!"
        )
    )


# =========================
# EDIT CUSTOMER
# =========================

@app.route("/customers/edit/<int:customer_id>", methods=["GET", "POST"])
def edit_customer(customer_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            return "Customer name is required", 400

        cursor.execute("""
            UPDATE customers
            SET
                name = %s,
                phone = %s,
                address = %s
            WHERE customer_id = %s
            AND vendor_id = 1
        """, (
            name,
            phone if phone else None,
            address if address else None,
            customer_id
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "customers",
                success="Customer updated successfully!"
            )
        )

    # Get customer
    cursor.execute("""
        SELECT
            customer_id,
            name,
            phone,
            address
        FROM customers
        WHERE customer_id = %s
        AND vendor_id = 1
    """, (customer_id,))

    customer = cursor.fetchone()

    cursor.close()
    connection.close()

    if customer is None:
        return "Customer not found", 404

    return render_template(
        "edit_customer.html",
        customer=customer
    )


# =========================
# UDHAR / CREDIT
# =========================

@app.route("/udhaar")
def udhaar():

    search = request.args.get("search", "").strip()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Customers with their pending balance
    if search:

        cursor.execute("""
            SELECT
                c.customer_id,
                c.name,
                c.phone,
                COALESCE(
                    SUM(
                        CASE
                            WHEN ct.transaction_type = 'CREDIT'
                                THEN ct.amount
                            WHEN ct.transaction_type = 'PAYMENT'
                                THEN -ct.amount
                            ELSE 0
                        END
                    ), 0
                ) AS pending_amount
            FROM customers c
            LEFT JOIN credit_transactions ct
                ON c.customer_id = ct.customer_id
                AND ct.vendor_id = 1
            WHERE c.vendor_id = 1
            AND (
                c.name LIKE %s
                OR c.phone LIKE %s
            )
            GROUP BY
                c.customer_id,
                c.name,
                c.phone
            ORDER BY c.name
        """, (
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cursor.execute("""
            SELECT
                c.customer_id,
                c.name,
                c.phone,
                COALESCE(
                    SUM(
                        CASE
                            WHEN ct.transaction_type = 'CREDIT'
                                THEN ct.amount
                            WHEN ct.transaction_type = 'PAYMENT'
                                THEN -ct.amount
                            ELSE 0
                        END
                    ), 0
                ) AS pending_amount
            FROM customers c
            LEFT JOIN credit_transactions ct
                ON c.customer_id = ct.customer_id
                AND ct.vendor_id = 1
            WHERE c.vendor_id = 1
            GROUP BY
                c.customer_id,
                c.name,
                c.phone
            ORDER BY c.name
        """)

    customers = cursor.fetchall()

    # Recent transactions
    cursor.execute("""
        SELECT
            ct.transaction_id,
            ct.transaction_type,
            ct.amount,
            ct.notes,
            ct.transaction_date,
            c.name AS customer_name
        FROM credit_transactions ct
        JOIN customers c
            ON ct.customer_id = c.customer_id
        WHERE ct.vendor_id = 1
        ORDER BY ct.transaction_id DESC
        LIMIT 20
    """)

    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "udhaar.html",
        customers=customers,
        transactions=transactions,
        search=search
    )


# =========================
# ADD UDHAR / CREDIT
# =========================

@app.route("/udhaar/add", methods=["POST"])
def add_udhaar():

    customer_id = int(request.form["customer_id"])
    amount = float(request.form["amount"])
    notes = request.form.get("notes", "").strip()

    if amount <= 0:
        return "Amount must be greater than zero", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO credit_transactions
            (
                vendor_id,
                customer_id,
                sale_id,
                transaction_type,
                amount,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            1,
            customer_id,
            None,
            "CREDIT",
            amount,
            notes if notes else None
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return f"Udhaar creation failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("udhaar"))


# =========================
# RECEIVE PAYMENT
# =========================

@app.route("/udhaar/payment", methods=["POST"])
def receive_payment():

    customer_id = int(request.form["customer_id"])
    amount = float(request.form["amount"])
    notes = request.form.get("notes", "").strip()

    if amount <= 0:
        return "Amount must be greater than zero", 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Calculate current pending amount
        cursor.execute("""
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'CREDIT'
                                THEN amount
                            WHEN transaction_type = 'PAYMENT'
                                THEN -amount
                            ELSE 0
                        END
                    ), 0
                ) AS pending_amount
            FROM credit_transactions
            WHERE vendor_id = 1
            AND customer_id = %s
        """, (customer_id,))

        result = cursor.fetchone()

        pending_amount = float(result["pending_amount"] or 0)

        # Customer cannot pay more than pending amount
        if pending_amount <= 0:
            return "This customer has no pending Udhaar", 400

        if amount > pending_amount:
            return (
                f"Payment cannot exceed pending Udhaar "
                f"of ₹{pending_amount:.2f}"
            ), 400

        # Add payment transaction
        cursor.execute("""
            INSERT INTO credit_transactions
            (
                vendor_id,
                customer_id,
                sale_id,
                transaction_type,
                amount,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            1,
            customer_id,
            None,
            "PAYMENT",
            amount,
            notes if notes else None
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return f"Payment failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("udhaar"))




# =========================
# EXPENSES
# =========================

@app.route("/expenses")
def expenses():

    success = request.args.get("success")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM expenses
        WHERE vendor_id = 1
        ORDER BY expense_id DESC
    """)

    expense_list = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "expenses.html",
        expenses=expense_list,
        success=success
    )


# =========================
# ADD EXPENSE
# =========================

@app.route("/expenses/add", methods=["POST"])
def add_expense():

    category = request.form["category"].strip()
    amount = float(request.form["amount"])
    description = request.form.get("description", "").strip()

    if amount <= 0:
        return "Amount must be greater than zero", 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
    INSERT INTO expenses
    (
        vendor_id,
        category,
        amount,
        description,
        expense_date
    )
    VALUES (%s, %s, %s, %s, NOW())
""", (
    1,
    category,
    amount,
    description if description else None
    ))

        connection.commit()

    except Exception as e:

        connection.rollback()
        return f"Expense creation failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(
        url_for(
            "expenses",
            success="Expense added successfully!"
        )
    )


# =========================
# DELETE EXPENSE
# =========================

@app.route("/expenses/delete/<int:expense_id>")
def delete_expense(expense_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM expenses
            WHERE expense_id = %s
            AND vendor_id = 1
        """, (expense_id,))

        connection.commit()

    except Exception as e:

        connection.rollback()
        return f"Expense deletion failed: {e}", 500

    finally:

        cursor.close()
        connection.close()

    return redirect(
        url_for(
            "expenses",
            success="Expense deleted successfully!"
        )
    )


# =========================
# REPORTS
# =========================

@app.route("/reports")
def reports():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # =========================
    # TOTAL SALES
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM(total_amount), 0
        ) AS total_sales
        FROM sales
        WHERE vendor_id = 1
    """)

    total_sales = cursor.fetchone()["total_sales"]


    # =========================
    # GROSS PROFIT
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM(
                (selling_price - cost_price) * quantity
            ), 0
        ) AS gross_profit
        FROM sale_items si
        JOIN sales s
            ON si.sale_id = s.sale_id
        WHERE s.vendor_id = 1
    """)

    gross_profit = cursor.fetchone()["gross_profit"]


    # =========================
    # TOTAL EXPENSES
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM(amount), 0
        ) AS total_expenses
        FROM expenses
        WHERE vendor_id = 1
    """)

    total_expenses = cursor.fetchone()["total_expenses"]


    # =========================
    # NET PROFIT
    # =========================

    net_profit = (
        float(gross_profit or 0)
        - float(total_expenses or 0)
    )


    # =========================
    # PENDING UDHAR
    # =========================

    cursor.execute("""
        SELECT COALESCE(
            SUM(
                CASE
                    WHEN transaction_type = 'CREDIT'
                        THEN amount
                    WHEN transaction_type = 'PAYMENT'
                        THEN -amount
                    ELSE 0
                END
            ), 0
        ) AS pending_credit
        FROM credit_transactions
        WHERE vendor_id = 1
    """)

    pending_credit = cursor.fetchone()["pending_credit"]


    # =========================
    # LOW STOCK
    # =========================

    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE vendor_id = 1
        AND stock_qty <= low_stock_threshold
    """)

    low_stock = cursor.fetchone()["low_stock"]


    # =========================
    # RECENT SALES
    # =========================

    cursor.execute("""
        SELECT
            s.sale_id,
            s.total_amount,
            s.payment_method,
            s.sale_date,
            COALESCE(
                c.name,
                'Walk-in Customer'
            ) AS customer_name
        FROM sales s
        LEFT JOIN customers c
            ON s.customer_id = c.customer_id
        WHERE s.vendor_id = 1
        ORDER BY s.sale_id DESC
        LIMIT 10
    """)

    recent_sales = cursor.fetchall()


    # =========================
    # RECENT EXPENSES
    # =========================

    cursor.execute("""
        SELECT
            category,
            description,
            amount,
            expense_date
        FROM expenses
        WHERE vendor_id = 1
        ORDER BY expense_id DESC
        LIMIT 10
    """)

    recent_expenses = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "reports.html",
        total_sales=total_sales,
        gross_profit=gross_profit,
        total_expenses=total_expenses,
        net_profit=net_profit,
        pending_credit=pending_credit,
        low_stock=low_stock,
        recent_sales=recent_sales,
        recent_expenses=recent_expenses
    )


# =========================
# PROFILE
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()

        cursor.execute("""
            UPDATE vendors
            SET
                name = %s,
                phone = %s,
                address = %s
            WHERE vendor_id = 1
        """, (
            name,
            phone if phone else None,
            address if address else None
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "profile",
                success="Profile updated successfully!"
            )
        )

    cursor.execute("""
        SELECT *
        FROM vendors
        WHERE vendor_id = 1
    """)

    vendor = cursor.fetchone()

    cursor.close()
    connection.close()

    if vendor is None:
        return "Vendor not found", 404

    success = request.args.get("success")

    return render_template(
        "profile.html",
        vendor=vendor,
        success=success
    )
# =========================
# RUN APP
# =========================

if __name__ == "__main__":
    app.run(debug=True)