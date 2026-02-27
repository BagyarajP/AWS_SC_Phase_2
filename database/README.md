# Database Setup Guide

This directory contains the SQL DDL scripts for the Supply Chain AI Platform Redshift database.

## Schema Overview

The database schema includes 13 tables organized into three categories:

### Core Operational Tables
- `product` - 2,000 SKUs with attributes
- `warehouse` - 3 distribution centers
- `supplier` - 500 suppliers with performance metrics
- `inventory` - Current stock levels by warehouse and SKU
- `purchase_order_header` - Purchase order headers
- `purchase_order_line` - Purchase order line items
- `sales_order_header` - Sales order headers
- `sales_order_line` - Sales order line items

### Agent Decision Tables
- `agent_decision` - All agent decisions with rationale and confidence scores
- `approval_queue` - High-risk decisions requiring human approval
- `audit_log` - Complete audit trail of all actions

### Forecasting Tables
- `demand_forecast` - Demand predictions with confidence intervals
- `forecast_accuracy` - Historical forecast accuracy metrics (MAPE)

## Setup Instructions

### 1. Create Redshift Cluster

Using AWS Console:
1. Navigate to Amazon Redshift
2. Click "Create cluster"
3. Configuration:
   - Cluster identifier: `supply-chain-cluster`
   - Node type: `dc2.large`
   - Number of nodes: 1 (for MVP)
   - Database name: `supply_chain`
   - Admin username: `admin`
   - Admin password: (set securely)
4. Network settings:
   - VPC: Default or custom
   - Publicly accessible: Yes (for development) or No (for production)
5. Click "Create cluster"

### 2. Execute Schema Script

Once the cluster is available:

**Option A: Using Redshift Query Editor (Console)**
1. Navigate to Redshift Query Editor v2
2. Connect to `supply-chain-cluster`
3. Open `schema.sql`
4. Execute the script

**Option B: Using psql CLI**
```bash
psql -h <cluster-endpoint> -U admin -d supply_chain -p 5439 -f schema.sql
```

**Option C: Using Python**
```python
import psycopg2

conn = psycopg2.connect(
    host='<cluster-endpoint>',
    port=5439,
    database='supply_chain',
    user='admin',
    password='<password>'
)

with open('schema.sql', 'r') as f:
    schema_sql = f.read()

cursor = conn.cursor()
cursor.execute(schema_sql)
conn.commit()
cursor.close()
conn.close()
```

### 3. Verify Tables Created

Run this query to verify all tables exist:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected output: 13 tables

## Next Steps

After creating the schema:
1. Generate synthetic data using `scripts/generate_synthetic_data.py`
2. Upload data to S3 using `scripts/upload_to_s3.py`
3. Configure and run AWS Glue ETL job to load data into Redshift

## Schema Modifications

If you need to modify the schema:
1. Update `schema.sql`
2. Drop and recreate tables (development only):
   ```sql
   DROP TABLE IF EXISTS forecast_accuracy CASCADE;
   DROP TABLE IF EXISTS demand_forecast CASCADE;
   DROP TABLE IF EXISTS audit_log CASCADE;
   DROP TABLE IF EXISTS approval_queue CASCADE;
   DROP TABLE IF EXISTS agent_decision CASCADE;
   DROP TABLE IF EXISTS sales_order_line CASCADE;
   DROP TABLE IF EXISTS sales_order_header CASCADE;
   DROP TABLE IF EXISTS purchase_order_line CASCADE;
   DROP TABLE IF EXISTS purchase_order_header CASCADE;
   DROP TABLE IF EXISTS inventory CASCADE;
   DROP TABLE IF EXISTS supplier CASCADE;
   DROP TABLE IF EXISTS warehouse CASCADE;
   DROP TABLE IF EXISTS product CASCADE;
   ```
3. Re-execute `schema.sql`

## Notes

- Redshift uses VARCHAR(65535) for JSON columns (no native JSON type in older versions)
- All timestamps use `CURRENT_TIMESTAMP` default
- Foreign key constraints are informational only in Redshift (not enforced)
- Consider adding SORTKEY and DISTKEY for production optimization
