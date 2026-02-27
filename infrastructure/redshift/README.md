# Redshift Serverless Setup Guide

This guide walks through setting up Redshift Serverless for the Supply Chain AI Platform.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Python 3.9+ installed
- boto3 library installed (`pip install boto3 pandas numpy`)

## Step 1: Create Redshift Serverless Workgroup

### Using AWS Console

1. Navigate to Amazon Redshift in the AWS Console
2. Select **us-east-1 (N. Virginia)** region
3. Click **Redshift Serverless** in the left navigation
4. Click **Create workgroup**

**Workgroup Configuration:**
- **Workgroup name:** `supply-chain-workgroup`
- **Namespace:** Create new namespace `supply-chain-platform`
- **Database name:** `supply_chain`
- **Admin user:** `admin` (set a secure password)
- **Base capacity:** 32 RPUs
- **VPC:** Default VPC (or your preferred VPC)
- **Security group:** Create or select a security group that allows access
- **Publicly accessible:** Enable if accessing from outside VPC
- **Enhanced VPC routing:** Disabled (for MVP)

**Advanced settings:**
- **Auto-pause:** Enabled (pause after 30 minutes of inactivity)
- **Snapshot retention:** 7 days
- **Encryption:** AWS-managed key

5. Click **Create workgroup**
6. Wait for the workgroup to become **Available** (takes 2-3 minutes)

### Using AWS CLI

```bash
# Create namespace
aws redshift-serverless create-namespace \
    --namespace-name supply-chain-platform \
    --db-name supply_chain \
    --admin-username admin \
    --admin-user-password <YOUR_SECURE_PASSWORD> \
    --region us-east-1

# Create workgroup
aws redshift-serverless create-workgroup \
    --workgroup-name supply-chain-workgroup \
    --namespace-name supply-chain-platform \
    --base-capacity 32 \
    --publicly-accessible \
    --region us-east-1
```

## Step 2: Create Database Schema

### Option A: Using Query Editor v2 (Recommended)

1. In AWS Console, navigate to **Redshift Query Editor v2**
2. Connect to `supply-chain-workgroup`
3. Open `infrastructure/redshift/schema.sql`
4. Copy and paste the entire SQL script
5. Click **Run** to execute
6. Verify all 13 tables are created

### Option B: Using AWS CLI

```bash
# Read the schema file and execute
aws redshift-data execute-statement \
    --workgroup-name supply-chain-workgroup \
    --database supply_chain \
    --sql file://infrastructure/redshift/schema.sql \
    --region us-east-1
```

## Step 3: Generate Synthetic Data

Run the data generation script:

```bash
python scripts/generate_synthetic_data.py
```

This will create CSV files in `data/synthetic/` directory:
- `product.csv` (2,000 SKUs)
- `warehouse.csv` (3 warehouses)
- `supplier.csv` (500 suppliers)
- `sales_order_header.csv` (12 months of orders)
- `sales_order_line.csv` (order line items)
- `inventory.csv` (inventory levels)
- `purchase_order_header.csv` (sample POs)
- `purchase_order_line.csv` (PO line items)

## Step 4: Upload Data to S3

1. Update the bucket name in `scripts/upload_to_s3.py`:
   ```python
   BUCKET_NAME = 'your-bucket-name'  # Change this
   ```

2. Run the upload script:
   ```bash
   python scripts/upload_to_s3.py
   ```

This will:
- Create the S3 bucket if it doesn't exist
- Upload all CSV files to `s3://your-bucket-name/synthetic_data/`

## Step 5: Load Data into Redshift

### Option A: Using COPY Command (Recommended for Production)

1. Create an IAM role for Redshift to access S3:
   - Role name: `RedshiftS3AccessRole`
   - Attach policy: `AmazonS3ReadOnlyAccess`
   - Trust relationship: Redshift service

2. Associate the role with your Redshift workgroup

3. Run COPY commands in Query Editor v2:

```sql
-- Copy products
COPY product
FROM 's3://your-bucket-name/synthetic_data/product.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy warehouses
COPY warehouse
FROM 's3://your-bucket-name/synthetic_data/warehouse.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy suppliers
COPY supplier
FROM 's3://your-bucket-name/synthetic_data/supplier.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy inventory
COPY inventory
FROM 's3://your-bucket-name/synthetic_data/inventory.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy purchase order headers
COPY purchase_order_header
FROM 's3://your-bucket-name/synthetic_data/purchase_order_header.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy purchase order lines
COPY purchase_order_line
FROM 's3://your-bucket-name/synthetic_data/purchase_order_line.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy sales order headers
COPY sales_order_header
FROM 's3://your-bucket-name/synthetic_data/sales_order_header.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';

-- Copy sales order lines
COPY sales_order_line
FROM 's3://your-bucket-name/synthetic_data/sales_order_line.csv'
IAM_ROLE 'arn:aws:iam::YOUR_ACCOUNT_ID:role/RedshiftS3AccessRole'
CSV
IGNOREHEADER 1
REGION 'us-east-1';
```

### Option B: Using AWS Glue (Covered in Task 2)

AWS Glue ETL job will be created in Task 2 to automate data loading.

## Step 6: Test Redshift Data API Connectivity

Run the connection test script:

```bash
python scripts/test_redshift_connection.py
```

This will:
- Test basic connectivity to Redshift Data API
- Execute a simple query
- List all tables in the database
- Check workgroup status

Expected output:
```
============================================================
Redshift Data API Connection Test
============================================================

Region: us-east-1
Workgroup: supply-chain-workgroup
Database: supply_chain

✓ Redshift Data API client initialized

Test 1: Executing simple query (SELECT 1)...
✓ Query submitted (ID: ...)
  Waiting for query to complete... ✓
✓ Query result verified: 1

Test 2: Listing tables in database...
✓ Found 13 tables:
    - agent_decision
    - approval_queue
    - audit_log
    - demand_forecast
    - forecast_accuracy
    - inventory
    - product
    - purchase_order_header
    - purchase_order_line
    - sales_order_header
    - sales_order_line
    - supplier
    - warehouse

Test 3: Checking workgroup status...
✓ Workgroup status: AVAILABLE
✓ Base capacity: 32 RPUs

============================================================
All tests passed! ✓
============================================================
```

## Step 7: Verify Data

Run verification queries in Query Editor v2:

```sql
-- Check row counts
SELECT 'product' as table_name, COUNT(*) as row_count FROM product
UNION ALL
SELECT 'warehouse', COUNT(*) FROM warehouse
UNION ALL
SELECT 'supplier', COUNT(*) FROM supplier
UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL
SELECT 'purchase_order_header', COUNT(*) FROM purchase_order_header
UNION ALL
SELECT 'purchase_order_line', COUNT(*) FROM purchase_order_line
UNION ALL
SELECT 'sales_order_header', COUNT(*) FROM sales_order_header
UNION ALL
SELECT 'sales_order_line', COUNT(*) FROM sales_order_line
ORDER BY table_name;

-- Check for products below reorder point
SELECT 
    p.sku,
    p.product_name,
    p.reorder_point,
    i.quantity_on_hand,
    w.warehouse_name
FROM product p
JOIN inventory i ON p.product_id = i.product_id
JOIN warehouse w ON i.warehouse_id = w.warehouse_id
WHERE i.quantity_on_hand < p.reorder_point
ORDER BY i.quantity_on_hand
LIMIT 10;

-- Check sales order seasonality
SELECT 
    EXTRACT(MONTH FROM order_date) as month,
    COUNT(*) as order_count
FROM sales_order_header
GROUP BY month
ORDER BY month;
```

Expected results:
- 2,000 products
- 3 warehouses
- 500 suppliers
- 6,000 inventory records (2,000 SKUs × 3 warehouses)
- ~100 purchase orders
- ~13,000 sales orders (with seasonal variation)
- Higher order counts in months 11, 12, 1, 2 (winter seasonality)

## Troubleshooting

### Connection Issues

If you get connection errors:
1. Check that the workgroup is in **AVAILABLE** state
2. Verify security group allows inbound traffic
3. Ensure IAM user/role has `redshift-data:*` permissions
4. Check VPC and subnet configuration

### Query Timeout

If queries timeout:
1. Increase base capacity (32 → 64 RPUs)
2. Check for long-running queries in Query Editor v2
3. Verify network connectivity

### Data Loading Errors

If COPY commands fail:
1. Verify S3 bucket and file paths
2. Check IAM role has S3 read permissions
3. Ensure CSV format matches table schema
4. Check CloudWatch logs for detailed errors

## Cost Optimization

Redshift Serverless pricing:
- **Base capacity:** 32 RPUs = ~$0.36/hour when active
- **Auto-pause:** Automatically pauses after 30 minutes of inactivity
- **Storage:** $0.024/GB-month

For MVP development:
- Enable auto-pause to minimize costs
- Use Query Editor v2 (no additional cost)
- Monitor usage in AWS Cost Explorer

## Security Best Practices

1. **Network Security:**
   - Use VPC with private subnets for production
   - Restrict security group to specific IP ranges
   - Enable VPC flow logs

2. **Access Control:**
   - Use IAM roles instead of passwords where possible
   - Enable MFA for admin users
   - Follow principle of least privilege

3. **Data Protection:**
   - Enable encryption at rest (AWS-managed keys)
   - Enable encryption in transit (SSL/TLS)
   - Configure automated snapshots

4. **Monitoring:**
   - Enable CloudWatch logging
   - Set up CloudWatch alarms for errors
   - Monitor query performance

## Next Steps

After completing this setup:
1. ✓ Redshift Serverless workgroup created
2. ✓ Database schema created
3. ✓ Synthetic data generated and loaded
4. ✓ Data API connectivity tested
5. → Proceed to Task 2: Implement AWS Glue ETL job
