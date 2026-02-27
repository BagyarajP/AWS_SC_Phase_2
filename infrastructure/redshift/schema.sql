-- Redshift Serverless Schema for Supply Chain AI Platform
-- Region: us-east-1 (N. Virginia)
-- Workgroup: supply-chain-workgroup
-- Database: supply_chain

-- Core operational tables

CREATE TABLE product (
    product_id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    unit_cost DECIMAL(10,2),
    reorder_point INTEGER,
    reorder_quantity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE warehouse (
    warehouse_id VARCHAR(50) PRIMARY KEY,
    warehouse_name VARCHAR(100) NOT NULL,
    location VARCHAR(100),
    capacity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE supplier (
    supplier_id VARCHAR(50) PRIMARY KEY,
    supplier_name VARCHAR(200) NOT NULL,
    contact_email VARCHAR(100),
    reliability_score DECIMAL(3,2),
    avg_lead_time_days INTEGER,
    defect_rate DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE inventory (
    inventory_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES product(product_id),
    warehouse_id VARCHAR(50) REFERENCES warehouse(warehouse_id),
    quantity_on_hand INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_order_header (
    po_id VARCHAR(50) PRIMARY KEY,
    supplier_id VARCHAR(50) REFERENCES supplier(supplier_id),
    order_date DATE,
    expected_delivery_date DATE,
    total_amount DECIMAL(12,2),
    status VARCHAR(50),
    created_by VARCHAR(100),
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_order_line (
    po_line_id VARCHAR(50) PRIMARY KEY,
    po_id VARCHAR(50) REFERENCES purchase_order_header(po_id),
    product_id VARCHAR(50) REFERENCES product(product_id),
    quantity INTEGER,
    unit_price DECIMAL(10,2),
    line_total DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_order_header (
    so_id VARCHAR(50) PRIMARY KEY,
    order_date DATE,
    warehouse_id VARCHAR(50) REFERENCES warehouse(warehouse_id),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales_order_line (
    so_line_id VARCHAR(50) PRIMARY KEY,
    so_id VARCHAR(50) REFERENCES sales_order_header(so_id),
    product_id VARCHAR(50) REFERENCES product(product_id),
    quantity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent decision and audit tables

CREATE TABLE agent_decision (
    decision_id VARCHAR(50) PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    decision_type VARCHAR(100) NOT NULL,
    decision_data VARCHAR(MAX),
    rationale VARCHAR(MAX),
    confidence_score DECIMAL(3,2),
    status VARCHAR(50),
    requires_approval BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE approval_queue (
    approval_id VARCHAR(50) PRIMARY KEY,
    decision_id VARCHAR(50) REFERENCES agent_decision(decision_id),
    assigned_role VARCHAR(100),
    status VARCHAR(50),
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    rejection_reason VARCHAR(MAX),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_log (
    event_id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100),
    user_name VARCHAR(100),
    action_type VARCHAR(100),
    entity_type VARCHAR(100),
    entity_id VARCHAR(50),
    rationale VARCHAR(MAX),
    confidence_score DECIMAL(3,2),
    before_state VARCHAR(MAX),
    after_state VARCHAR(MAX),
    metadata VARCHAR(MAX)
);

-- Forecasting tables

CREATE TABLE demand_forecast (
    forecast_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES product(product_id),
    warehouse_id VARCHAR(50) REFERENCES warehouse(warehouse_id),
    forecast_date DATE,
    forecast_horizon_days INTEGER,
    predicted_demand INTEGER,
    confidence_interval_lower INTEGER,
    confidence_interval_upper INTEGER,
    confidence_level DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE forecast_accuracy (
    accuracy_id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES product(product_id),
    forecast_date DATE,
    actual_demand INTEGER,
    predicted_demand INTEGER,
    mape DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
