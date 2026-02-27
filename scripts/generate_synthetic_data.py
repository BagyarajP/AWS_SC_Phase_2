"""
Synthetic Data Generation Script for Supply Chain AI Platform
Generates realistic operational data for 2,000 SKUs, 500 suppliers, 3 warehouses, and 12 months of sales orders
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import uuid
import os

# Configuration
NUM_SKUS = 2000
NUM_SUPPLIERS = 500
NUM_WAREHOUSES = 3
MONTHS_OF_DATA = 12
OUTPUT_DIR = 'data/synthetic'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_products():
    """Generate 2,000 SKUs with realistic attributes"""
    categories = ['Electrical', 'Plumbing', 'HVAC', 'Safety', 'Tools']
    products = []
    
    for i in range(NUM_SKUS):
        category = random.choice(categories)
        products.append({
            'product_id': f'PROD-{i:05d}',
            'sku': f'SKU-{category[:3].upper()}-{i:04d}',
            'product_name': f'{category} Product {i}',
            'category': category,
            'unit_cost': round(random.uniform(5, 500), 2),
            'reorder_point': random.randint(50, 200),
            'reorder_quantity': random.randint(100, 500),
            'created_at': datetime.now().isoformat()
        })
    
    return pd.DataFrame(products)

def generate_warehouses():
    """Generate 3 warehouses (South, Midland, North)"""
    warehouses = [
        {
            'warehouse_id': 'WH1_South',
            'warehouse_name': 'South Warehouse',
            'location': 'London',
            'capacity': 50000,
            'created_at': datetime.now().isoformat()
        },
        {
            'warehouse_id': 'WH_Midland',
            'warehouse_name': 'Midland Warehouse',
            'location': 'Birmingham',
            'capacity': 40000,
            'created_at': datetime.now().isoformat()
        },
        {
            'warehouse_id': 'WH_North',
            'warehouse_name': 'North Warehouse',
            'location': 'Manchester',
            'capacity': 35000,
            'created_at': datetime.now().isoformat()
        }
    ]
    return pd.DataFrame(warehouses)

def generate_suppliers():
    """Generate 500 suppliers with performance metrics"""
    suppliers = []
    
    for i in range(NUM_SUPPLIERS):
        suppliers.append({
            'supplier_id': f'SUP-{i:04d}',
            'supplier_name': f'Supplier {i} Ltd',
            'contact_email': f'contact@supplier{i}.com',
            'reliability_score': round(random.uniform(0.70, 0.99), 2),
            'avg_lead_time_days': random.randint(3, 21),
            'defect_rate': round(random.uniform(0.001, 0.05), 4),
            'created_at': datetime.now().isoformat()
        })
    
    return pd.DataFrame(suppliers)

def generate_sales_orders(products, warehouses):
    """Generate 12 months of sales orders with seasonality"""
    start_date = datetime.now() - timedelta(days=365)
    orders = []
    order_lines = []
    
    for day in range(365):
        current_date = start_date + timedelta(days=day)
        
        # Seasonal multiplier (higher in winter months for energy/services company)
        month = current_date.month
        seasonal_factor = 1.5 if month in [11, 12, 1, 2] else 1.0
        
        # Generate 20-50 orders per day with seasonality
        num_orders = int(random.randint(20, 50) * seasonal_factor)
        
        for _ in range(num_orders):
            so_id = f'SO-{uuid.uuid4().hex[:12]}'
            warehouse_id = random.choice(warehouses['warehouse_id'].tolist())
            
            orders.append({
                'so_id': so_id,
                'order_date': current_date.date().isoformat(),
                'warehouse_id': warehouse_id,
                'status': 'completed',
                'created_at': current_date.isoformat()
            })
            
            # 1-5 line items per order
            num_lines = random.randint(1, 5)
            for _ in range(num_lines):
                product = products.sample(1).iloc[0]
                order_lines.append({
                    'so_line_id': f'SOL-{uuid.uuid4().hex[:12]}',
                    'so_id': so_id,
                    'product_id': product['product_id'],
                    'quantity': random.randint(1, 20),
                    'created_at': current_date.isoformat()
                })
    
    return pd.DataFrame(orders), pd.DataFrame(order_lines)

def generate_inventory(products, warehouses):
    """Generate initial inventory levels for all SKUs across all warehouses"""
    inventory = []
    
    for _, product in products.iterrows():
        for _, warehouse in warehouses.iterrows():
            # Random initial inventory, some below reorder point to trigger procurement
            quantity = random.randint(0, 300)
            
            inventory.append({
                'inventory_id': f'INV-{uuid.uuid4().hex[:12]}',
                'product_id': product['product_id'],
                'warehouse_id': warehouse['warehouse_id'],
                'quantity_on_hand': quantity,
                'last_updated': datetime.now().isoformat()
            })
    
    return pd.DataFrame(inventory)

def generate_purchase_orders(products, suppliers):
    """Generate sample purchase orders"""
    po_headers = []
    po_lines = []
    
    # Generate 100 sample purchase orders
    for i in range(100):
        po_id = f'PO-{uuid.uuid4().hex[:12]}'
        supplier = suppliers.sample(1).iloc[0]
        order_date = datetime.now() - timedelta(days=random.randint(0, 90))
        
        po_headers.append({
            'po_id': po_id,
            'supplier_id': supplier['supplier_id'],
            'order_date': order_date.date().isoformat(),
            'expected_delivery_date': (order_date + timedelta(days=supplier['avg_lead_time_days'])).date().isoformat(),
            'total_amount': 0,  # Will calculate after lines
            'status': random.choice(['pending', 'approved', 'delivered']),
            'created_by': 'system',
            'approved_by': 'manager' if random.random() > 0.3 else None,
            'approved_at': order_date.isoformat() if random.random() > 0.3 else None,
            'created_at': order_date.isoformat()
        })
        
        # 1-3 line items per PO
        total_amount = 0
        num_lines = random.randint(1, 3)
        for _ in range(num_lines):
            product = products.sample(1).iloc[0]
            quantity = random.randint(50, 500)
            unit_price = product['unit_cost'] * random.uniform(0.9, 1.1)  # Slight price variation
            line_total = quantity * unit_price
            total_amount += line_total
            
            po_lines.append({
                'po_line_id': f'POL-{uuid.uuid4().hex[:12]}',
                'po_id': po_id,
                'product_id': product['product_id'],
                'quantity': quantity,
                'unit_price': round(unit_price, 2),
                'line_total': round(line_total, 2),
                'created_at': order_date.isoformat()
            })
        
        # Update total amount
        po_headers[-1]['total_amount'] = round(total_amount, 2)
    
    return pd.DataFrame(po_headers), pd.DataFrame(po_lines)

def main():
    """Main execution function"""
    print("=" * 60)
    print("Supply Chain AI Platform - Synthetic Data Generation")
    print("=" * 60)
    print()
    
    print("Generating products...")
    products_df = generate_products()
    print(f"✓ Generated {len(products_df)} products")
    
    print("Generating warehouses...")
    warehouses_df = generate_warehouses()
    print(f"✓ Generated {len(warehouses_df)} warehouses")
    
    print("Generating suppliers...")
    suppliers_df = generate_suppliers()
    print(f"✓ Generated {len(suppliers_df)} suppliers")
    
    print("Generating sales orders (this may take a moment)...")
    sales_orders_df, sales_order_lines_df = generate_sales_orders(products_df, warehouses_df)
    print(f"✓ Generated {len(sales_orders_df)} sales orders")
    print(f"✓ Generated {len(sales_order_lines_df)} sales order lines")
    
    print("Generating inventory...")
    inventory_df = generate_inventory(products_df, warehouses_df)
    print(f"✓ Generated {len(inventory_df)} inventory records")
    
    print("Generating purchase orders...")
    po_headers_df, po_lines_df = generate_purchase_orders(products_df, suppliers_df)
    print(f"✓ Generated {len(po_headers_df)} purchase orders")
    print(f"✓ Generated {len(po_lines_df)} purchase order lines")
    
    print()
    print("Saving CSV files...")
    
    # Save all dataframes to CSV
    products_df.to_csv(f'{OUTPUT_DIR}/product.csv', index=False)
    warehouses_df.to_csv(f'{OUTPUT_DIR}/warehouse.csv', index=False)
    suppliers_df.to_csv(f'{OUTPUT_DIR}/supplier.csv', index=False)
    sales_orders_df.to_csv(f'{OUTPUT_DIR}/sales_order_header.csv', index=False)
    sales_order_lines_df.to_csv(f'{OUTPUT_DIR}/sales_order_line.csv', index=False)
    inventory_df.to_csv(f'{OUTPUT_DIR}/inventory.csv', index=False)
    po_headers_df.to_csv(f'{OUTPUT_DIR}/purchase_order_header.csv', index=False)
    po_lines_df.to_csv(f'{OUTPUT_DIR}/purchase_order_line.csv', index=False)
    
    print(f"✓ All CSV files saved to {OUTPUT_DIR}/")
    print()
    print("=" * 60)
    print("Data Generation Complete!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Products: {len(products_df)}")
    print(f"  - Warehouses: {len(warehouses_df)}")
    print(f"  - Suppliers: {len(suppliers_df)}")
    print(f"  - Sales Orders: {len(sales_orders_df)}")
    print(f"  - Sales Order Lines: {len(sales_order_lines_df)}")
    print(f"  - Inventory Records: {len(inventory_df)}")
    print(f"  - Purchase Orders: {len(po_headers_df)}")
    print(f"  - Purchase Order Lines: {len(po_lines_df)}")
    print()
    print("Next steps:")
    print("  1. Upload CSV files to S3 using: python scripts/upload_to_s3.py")
    print("  2. Create Redshift Serverless workgroup in AWS Console")
    print("  3. Run schema.sql to create tables")
    print("  4. Load data using AWS Glue or COPY commands")

if __name__ == '__main__':
    main()
