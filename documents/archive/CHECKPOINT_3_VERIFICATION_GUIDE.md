# Checkpoint 3: Data Ingestion Verification Guide

## Overview

This checkpoint ensures that the AWS Glue ETL job runs successfully and loads all synthetic data into Redshift. This guide provides step-by-step instructions for setting up the infrastructure and verifying the data ingestion.

## Prerequisites

Before starting this checkpoint, ensure you have:
- ✅ AWS Account with appropriate permissions
- ✅ AWS CLI installed and configured
- ✅ Python 3.9+ installed
- ✅ Synthetic data generated (Task 1 completed)
- ✅ Glue ETL job code implemented (Task 2 completed)

## Infrastructure Setup Steps

### Step 1: Create S3 Bucket for Data Storage

```bash
# Set your AWS region
export AWS_REGION=eu-west-2

# Create the main data bucket
aws s3 mb s3://supply-chain-data-bucket --region $AWS_REGION

# Create a bucket for Glue scripts (if not exists)
aws s3 mb s3://supply-chain-glue-scripts --region $AWS_REGION
```

**Verification:**
```bash
aws s3 ls | grep supply-chain
```

Expected output:
```
supply-chain-data-bucket
supply-chain-glue-scripts
```

### Step 2: Upload Synthetic Data to S3

```bash
# Navigate to scripts directory
cd scripts

# Set environment variable
export S3_BUCKET_NAME=supply-chain-data-bucket

# Run upload script
python upload_to_s3.py
```

**Verification:**
```bash
aws s3 ls s3://supply-chain-data-bucket/synthetic_data/
```

Expected output (8 CSV files):
```
product.csv
warehouse.csv
supplier.csv
inventory.csv
purchase_order_header.csv
purchase_order_line.csv
sales_order_header.csv
sales_order_line.csv
```

### Step 3: Create Redshift Cluster

#### Option A: Using AWS Console

1. Navigate to **Amazon Redshift** in AWS Console
2. Click **"Create cluster"**
3. Configure cluster settings:
   - **Cluster identifier:** `supply-chain-cluster`
   - **Node type:** `dc2.large`
   - **Number of nodes:** 1
   - **Database name:** `supply_chain`
   - **Admin username:** `admin`
   - **Admin password:** (create a secure password and save it)
4. **Network and security:**
   - VPC: Default VPC (or your preferred VPC)
   - Publicly accessible: Yes (for MVP testing)
   - VPC security group: Create new or use existing (ensure port 5439 is open)
5. **Additional configurations:**
   - Automated snapshots: Enabled
   - Snapshot retention: 7 days
6. Click **"Create cluster"**

**Wait time:** 5-10 minutes for cluster to become available

#### Option B: Using AWS CLI

```bash
# Create Redshift cluster
aws redshift create-cluster \
  --cluster-identifier supply-chain-cluster \
  --node-type dc2.large \
  --master-username admin \
  --master-user-password YOUR_SECURE_PASSWORD \
  --db-name supply_chain \
  --cluster-type single-node \
  --publicly-accessible \
  --region eu-west-2

# Wait for cluster to be available
aws redshift wait cluster-available \
  --cluster-identifier supply-chain-cluster \
  --region eu-west-2
```

**Get cluster endpoint:**
```bash
aws redshift describe-clusters \
  --cluster-identifier supply-chain-cluster \
  --query 'Clusters[0].Endpoint.Address' \
  --output text
```

Save this endpoint - you'll need it for database connections.

### Step 4: Create Database Schema

#### Option A: Using Redshift Query Editor v2 (Console)

1. Navigate to **Amazon Redshift** → **Query Editor v2**
2. Click **"Connect to database"**
3. Select:
   - Cluster: `supply-chain-cluster`
   - Database: `supply_chain`
   - User: `admin`
   - Password: (your admin password)
4. Click **"Create connection"**
5. Open `database/schema.sql` file
6. Copy the entire contents
7. Paste into Query Editor
8. Click **"Run"**

#### Option B: Using psql CLI

```bash
# Install psql if not already installed
# On Ubuntu/Debian: sudo apt-get install postgresql-client
# On macOS: brew install postgresql

# Get cluster endpoint
export REDSHIFT_HOST=$(aws redshift describe-clusters \
  --cluster-identifier supply-chain-cluster \
  --query 'Clusters[0].Endpoint.Address' \
  --output text)

# Connect and execute schema
psql -h $REDSHIFT_HOST \
     -U admin \
     -d supply_chain \
     -p 5439 \
     -f database/schema.sql
```

**Verification:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected output (13 tables):
```
agent_decision
approval_queue
audit_log
demand_forecast
forecast_accuracy
inventory
product
purchase_order_header
purchase_order_line
sales_order_header
sales_order_line
supplier
warehouse
```

### Step 5: Create IAM Role for Glue

#### Create IAM Policy for S3 and Redshift Access

Create a file `glue-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::supply-chain-data-bucket",
        "arn:aws:s3:::supply-chain-data-bucket/*",
        "arn:aws:s3:::supply-chain-glue-scripts",
        "arn:aws:s3:::supply-chain-glue-scripts/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::supply-chain-data-bucket/temp/*",
        "arn:aws:s3:::supply-chain-data-bucket/spark-logs/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift:GetClusterCredentials",
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "arn:aws:redshift:eu-west-2:*:cluster:supply-chain-cluster"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:eu-west-2:*:log-group:/aws-glue/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "cloudwatch:namespace": "SupplyChainAI/ETL"
        }
      }
    }
  ]
}
```

#### Create IAM Role

```bash
# Create the policy
aws iam create-policy \
  --policy-name SupplyChainGluePolicy \
  --policy-document file://glue-policy.json

# Get your AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create trust policy for Glue
cat > glue-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "glue.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name SupplyChainGlueRole \
  --assume-role-policy-document file://glue-trust-policy.json

# Attach AWS managed policy for Glue
aws iam attach-role-policy \
  --role-name SupplyChainGlueRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

# Attach custom policy
aws iam attach-role-policy \
  --role-name SupplyChainGlueRole \
  --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/SupplyChainGluePolicy
```

### Step 6: Create Glue Connection to Redshift

#### Option A: Using AWS Console

1. Navigate to **AWS Glue** → **Data Catalog** → **Connections**
2. Click **"Add connection"**
3. Configure connection:
   - **Connection name:** `supply-chain-redshift`
   - **Connection type:** Amazon Redshift
   - **Cluster:** Select `supply-chain-cluster`
   - **Database name:** `supply_chain`
   - **Username:** `admin`
   - **Password:** (your Redshift admin password)
4. Click **"Create connection"**
5. **Test connection** to verify it works

#### Option B: Using AWS CLI

```bash
# Get Redshift cluster details
export REDSHIFT_HOST=$(aws redshift describe-clusters \
  --cluster-identifier supply-chain-cluster \
  --query 'Clusters[0].Endpoint.Address' \
  --output text)

export REDSHIFT_PORT=5439
export REDSHIFT_DB=supply_chain

# Create connection
aws glue create-connection \
  --connection-input "{
    \"Name\": \"supply-chain-redshift\",
    \"ConnectionType\": \"JDBC\",
    \"ConnectionProperties\": {
      \"JDBC_CONNECTION_URL\": \"jdbc:redshift://${REDSHIFT_HOST}:${REDSHIFT_PORT}/${REDSHIFT_DB}\",
      \"USERNAME\": \"admin\",
      \"PASSWORD\": \"YOUR_REDSHIFT_PASSWORD\"
    }
  }"
```

### Step 7: Deploy Glue ETL Job

```bash
# Navigate to glue directory
cd glue

# Upload Glue script to S3
aws s3 cp etl_job.py s3://supply-chain-glue-scripts/supply-chain-ai/etl_job.py

# Set environment variables for deployment
export S3_SCRIPTS_BUCKET=supply-chain-glue-scripts
export S3_DATA_BUCKET=supply-chain-data-bucket
export IAM_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/SupplyChainGlueRole

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

**Verification:**
```bash
# Check if job was created
aws glue get-job --job-name supply-chain-etl-job
```

### Step 8: Run Glue ETL Job

```bash
# Start the job
aws glue start-job-run --job-name supply-chain-etl-job

# Get the job run ID from the output
export JOB_RUN_ID=<job-run-id-from-output>

# Monitor job status
aws glue get-job-run \
  --job-name supply-chain-etl-job \
  --run-id $JOB_RUN_ID \
  --query 'JobRun.JobRunState' \
  --output text
```

**Job states:**
- `STARTING` - Job is initializing
- `RUNNING` - Job is executing
- `SUCCEEDED` - Job completed successfully ✅
- `FAILED` - Job failed ❌

**Monitor in real-time:**
```bash
# Watch job status (updates every 30 seconds)
watch -n 30 "aws glue get-job-run \
  --job-name supply-chain-etl-job \
  --run-id $JOB_RUN_ID \
  --query 'JobRun.JobRunState' \
  --output text"
```

## Data Verification Queries

Once the Glue job completes successfully, run these verification queries in Redshift.

### 1. Verify All Tables Are Populated

```sql
-- Check record counts for all tables
SELECT 'product' as table_name, COUNT(*) as record_count FROM product
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
```

**Expected Results:**
| table_name | record_count |
|-----------|--------------|
| inventory | ~4,200 |
| product | 2,000 |
| purchase_order_header | ~1,000-1,500 |
| purchase_order_line | ~2,000-3,000 |
| sales_order_header | ~4,000-5,000 |
| sales_order_line | ~15,000-20,000 |
| supplier | 500 |
| warehouse | 3 |

### 2. Verify Data Quality - Products

```sql
-- Check product data quality
SELECT 
    COUNT(*) as total_products,
    COUNT(DISTINCT sku) as unique_skus,
    COUNT(DISTINCT category) as categories,
    MIN(unit_cost) as min_cost,
    MAX(unit_cost) as max_cost,
    AVG(unit_cost) as avg_cost,
    MIN(reorder_point) as min_reorder,
    MAX(reorder_point) as max_reorder
FROM product;
```

**Expected:**
- total_products: 2,000
- unique_skus: 2,000
- categories: 5 (Electrical, Plumbing, HVAC, Safety, Tools)
- min_cost: ~5.00
- max_cost: ~500.00
- avg_cost: ~250.00

### 3. Verify Data Quality - Warehouses

```sql
-- Check warehouse data
SELECT 
    warehouse_id,
    warehouse_name,
    location,
    capacity
FROM warehouse
ORDER BY warehouse_id;
```

**Expected:**
| warehouse_id | warehouse_name | location | capacity |
|-------------|----------------|----------|----------|
| WH1_South | South Warehouse | London | 50,000 |
| WH_Midland | Midland Warehouse | Birmingham | 40,000 |
| WH_North | North Warehouse | Manchester | 35,000 |

### 4. Verify Data Quality - Suppliers

```sql
-- Check supplier data quality
SELECT 
    COUNT(*) as total_suppliers,
    MIN(reliability_score) as min_reliability,
    MAX(reliability_score) as max_reliability,
    AVG(reliability_score) as avg_reliability,
    MIN(avg_lead_time_days) as min_lead_time,
    MAX(avg_lead_time_days) as max_lead_time,
    AVG(avg_lead_time_days) as avg_lead_time,
    MIN(defect_rate) as min_defect_rate,
    MAX(defect_rate) as max_defect_rate
FROM supplier;
```

**Expected:**
- total_suppliers: 500
- reliability_score: 0.70 - 0.99
- avg_lead_time_days: 3 - 21 days
- defect_rate: 0.001 - 0.05

### 5. Verify Data Quality - Inventory

```sql
-- Check inventory distribution
SELECT 
    w.warehouse_name,
    COUNT(DISTINCT i.product_id) as unique_products,
    SUM(i.quantity_on_hand) as total_units,
    AVG(i.quantity_on_hand) as avg_units_per_product
FROM inventory i
JOIN warehouse w ON i.warehouse_id = w.warehouse_id
GROUP BY w.warehouse_name
ORDER BY w.warehouse_name;
```

**Expected:**
- Each warehouse should have ~1,400 products (70% of 2,000 SKUs)
- Total units should be reasonable for warehouse capacity

### 6. Verify Data Quality - Sales Orders

```sql
-- Check sales order date range and volume
SELECT 
    MIN(order_date) as earliest_order,
    MAX(order_date) as latest_order,
    COUNT(*) as total_orders,
    COUNT(DISTINCT warehouse_id) as warehouses_used,
    AVG(lines_per_order) as avg_lines_per_order
FROM sales_order_header soh
LEFT JOIN (
    SELECT so_id, COUNT(*) as lines_per_order
    FROM sales_order_line
    GROUP BY so_id
) sol ON soh.so_id = sol.so_id;
```

**Expected:**
- Date range: ~12 months of data
- total_orders: 4,000-5,000
- warehouses_used: 3
- avg_lines_per_order: 3-4

### 7. Verify Referential Integrity

```sql
-- Check for orphaned records (should return 0 for all)
SELECT 'Inventory without Product' as check_name, COUNT(*) as orphaned_records
FROM inventory i
LEFT JOIN product p ON i.product_id = p.product_id
WHERE p.product_id IS NULL

UNION ALL

SELECT 'Inventory without Warehouse', COUNT(*)
FROM inventory i
LEFT JOIN warehouse w ON i.warehouse_id = w.warehouse_id
WHERE w.warehouse_id IS NULL

UNION ALL

SELECT 'PO Line without PO Header', COUNT(*)
FROM purchase_order_line pol
LEFT JOIN purchase_order_header poh ON pol.po_id = poh.po_id
WHERE poh.po_id IS NULL

UNION ALL

SELECT 'SO Line without SO Header', COUNT(*)
FROM sales_order_line sol
LEFT JOIN sales_order_header soh ON sol.so_id = soh.so_id
WHERE soh.so_id IS NULL;
```

**Expected:** All counts should be 0 (no orphaned records)

### 8. Verify NULL Handling

```sql
-- Check for NULL values in critical fields
SELECT 
    'product.product_id' as field_name,
    COUNT(*) as null_count
FROM product
WHERE product_id IS NULL

UNION ALL

SELECT 'product.sku', COUNT(*)
FROM product
WHERE sku IS NULL

UNION ALL

SELECT 'warehouse.warehouse_id', COUNT(*)
FROM warehouse
WHERE warehouse_id IS NULL

UNION ALL

SELECT 'supplier.supplier_id', COUNT(*)
FROM supplier
WHERE supplier_id IS NULL

UNION ALL

SELECT 'inventory.inventory_id', COUNT(*)
FROM inventory
WHERE inventory_id IS NULL;
```

**Expected:** All counts should be 0 (no NULL primary keys)

## CloudWatch Monitoring

### View Glue Job Logs

```bash
# Get log group name
aws logs describe-log-groups \
  --log-group-name-prefix /aws-glue/jobs \
  --query 'logGroups[*].logGroupName'

# Get latest log stream
aws logs describe-log-streams \
  --log-group-name /aws-glue/jobs/output \
  --order-by LastEventTime \
  --descending \
  --max-items 1 \
  --query 'logStreams[0].logStreamName' \
  --output text

# View logs
aws logs tail /aws-glue/jobs/output --follow
```

### View ETL Metrics

```bash
# Get metrics from CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace SupplyChainAI/ETL \
  --metric-name RecordsWritten \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

**Key Metrics to Check:**
- `TablesProcessed`: Should be 8
- `RecordsRead`: Total records extracted from S3
- `RecordsWritten`: Total records loaded to Redshift
- `RecordsFailed`: Should be 0 or minimal
- `SuccessRate`: Should be close to 100%
- `ErrorCount`: Should be 0

## Checkpoint Success Criteria

✅ **Checkpoint 3 is COMPLETE when:**

1. ✅ Glue job runs successfully (status: SUCCEEDED)
2. ✅ All 8 tables are populated with data
3. ✅ Record counts match expected ranges
4. ✅ No orphaned records (referential integrity maintained)
5. ✅ No NULL values in primary key fields
6. ✅ Data quality checks pass (valid ranges, distributions)
7. ✅ CloudWatch metrics show high success rate (>95%)
8. ✅ No critical errors in CloudWatch logs

## Troubleshooting

### Issue: Glue Job Fails with "Connection Timeout"

**Solution:**
1. Check Redshift security group allows inbound traffic on port 5439
2. Verify Glue connection is in same VPC as Redshift
3. Test Glue connection in AWS Console

### Issue: "Access Denied" on S3

**Solution:**
1. Verify IAM role has correct S3 permissions
2. Check bucket names match in job parameters
3. Ensure files exist in S3: `aws s3 ls s3://supply-chain-data-bucket/synthetic_data/`

### Issue: Schema Validation Errors

**Solution:**
1. Check CSV files have headers
2. Verify column names match schema in `etl_job.py`
3. Review CloudWatch logs for specific validation errors

### Issue: Low Success Rate (<95%)

**Solution:**
1. Review CloudWatch logs for specific record failures
2. Check for data quality issues in source CSV files
3. Verify data types match Redshift schema

### Issue: Missing Tables in Redshift

**Solution:**
1. Verify schema.sql was executed successfully
2. Check you're connected to correct database (`supply_chain`)
3. Run: `\dt` in psql to list all tables

## Next Steps

After successfully completing this checkpoint:

1. ✅ Mark Task 3 as complete in tasks.md
2. 📋 Document any issues encountered and resolutions
3. 📊 Save verification query results for audit trail
4. ➡️ Proceed to Task 4: Implement Forecasting Agent Lambda function

## Questions to Ask User

If any issues arise during verification:

1. **Did the Glue job complete successfully?**
   - Check job status in AWS Console or CLI
   - Review CloudWatch logs for errors

2. **Are all tables populated?**
   - Run verification query #1
   - Compare counts to expected ranges

3. **Are there any data quality issues?**
   - Run verification queries #2-8
   - Check for NULL values, orphaned records, invalid ranges

4. **Do CloudWatch metrics look healthy?**
   - Check SuccessRate metric
   - Review ErrorCount metric
   - Verify RecordsWritten matches expectations

## Summary

This checkpoint ensures the data pipeline is working correctly:
- **S3** → Synthetic data uploaded
- **Glue** → ETL job transforms and loads data
- **Redshift** → All tables populated with valid data

Once verified, the platform has a solid data foundation for implementing the AI agents in subsequent tasks.
