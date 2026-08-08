CREATE DATABASE IF NOT EXISTS vyapaaros;

USE vyapaaros;

-- =========================================
-- 1. VENDORS
-- =========================================

CREATE TABLE vendors (
    vendor_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    shop_name VARCHAR(150) NOT NULL,
    address TEXT,
    language VARCHAR(30) DEFAULT 'English',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);


-- =========================================
-- 2. PRODUCTS
-- =========================================

CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit VARCHAR(20) NOT NULL,
    stock_qty DECIMAL(10,2) DEFAULT 0,
    purchase_price DECIMAL(10,2) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    low_stock_threshold DECIMAL(10,2) DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_products_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON DELETE CASCADE
);


-- =========================================
-- 3. CUSTOMERS
-- =========================================

CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_customers_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON DELETE CASCADE
);


-- =========================================
-- 4. SALES
-- =========================================

CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    customer_id INT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    sale_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_sales_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_sales_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE SET NULL
);


-- =========================================
-- 5. SALE ITEMS
-- =========================================


CREATE TABLE sale_items (
    sale_item_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    selling_price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,

    CONSTRAINT fk_sale_items_sale
        FOREIGN KEY (sale_id)
        REFERENCES sales(sale_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_sale_items_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT
);


-- =========================================
-- 6. CREDIT TRANSACTIONS
-- =========================================

CREATE TABLE credit_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    customer_id INT NOT NULL,
    sale_id INT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    notes TEXT,
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_credit_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_credit_customer
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_credit_sale
        FOREIGN KEY (sale_id)
        REFERENCES sales(sale_id)
        ON DELETE SET NULL
);


-- =========================================
-- 7. EXPENSES
-- =========================================

CREATE TABLE expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    expense_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_expenses_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON DELETE CASCADE
);