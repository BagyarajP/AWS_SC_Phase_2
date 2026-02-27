# Data Generation and Loading Scripts

This directory contains Python scripts for generating synthetic data and uploading it to S3.

## Scripts Overview

### 1. generate_synthetic_data.py
Generates realistic operational data for testing and development.

**Output:**
- 2,000 products across 5 categories (Electrical, Plumbing, HVAC, Safety, Tools)
- 500 suppliers with performance metrics
- 3 warehouses (WH1_South, WH_Midland, WH_North)
- 12 months of sales orders with seasonality
- Historical purchase orders
- Current inventory levels

**Usage:**
```bash
python generate_synthetic_data.py
```

**Output Directory:** `synthetic_data/`

**Generated Files:**
- `product.csv` - 2,000 SKUs
- `warehouse.csv` - 3 warehouses
- `supplier.csv` - 500 suppliers
- `inventory.csv` - Current stock levels
- `sales_order_header.csv` - Sales order headers
- `sales_order_line.csv` - Sales order line items
- `purchase_order_header.csv` - Purchase order headers
- `purchase_order_line.csv` - Purchase order line items

### 2. upload_to_s3.py
Uploads generated CSV files to S3 bucket for Glue ETL processing.

**Prerequisites:**
- AWS credentials configured (via AWS CLI or environment variables)
- S3 bucket created
- IAM permissions: `s3:PutObject`, `s3:ListBucket`

**Usage:**
```bash
# Set S3 bucket name (or use default)
export S3_BUCKET_NAME=supply-chain-data-bucket

# Upload files
python upload_to_s3.py
```

**Environment Variables:**
- `S3_BUCKET_NAME` - Target S3 bucket (default: `supply-chain-data-bucket`)

## Complete Workflow

### Step 1: Install Dependencies
```bash
pip install pandas numpy boto3
```

### Step 2: Generate Synthetic Data
```bash
cd scripts
python generate_synthetic_data.py
```

Expected output:
```
Starting synthetic data generation...
Output directory: synthetic_data
============================================================
Generated 2000 products
Generated 3 warehouses
Generated 500 suppliers
Generated 4200 inventory records
Generated 5475 sales order headers
Generated 16425 sales order lines
Generated 3650 purchase order headers
Generated 7300 purchase order lines
============================================================
Synthetic data generation complete!
```

### Step 3: Create S3 Bucket
Using AWS Console or CLI:
```bash
aws s3 mb s3://supply-chain-data-bucket --region eu-west-2
```

### Step 4: Upload to S3
```bash
export S3_BUCKET_NAME=supply-chain-data-bucket
python upload_to_s3.py
```

Expected output:
```
Supply Chain AI Platform - S3 Data Uploader
============================================================
✓ S3 bucket "supply-chain-data-bucket" is accessible

Uploading files to S3 bucket: supply-chain-data-bucket
S3 prefix: synthetic_data/
============================================================
Uploading product.csv (0.15 MB)... ✓
Uploading warehouse.csv (0.00 MB)... ✓
Uploading supplier.csv (0.03 MB)... ✓
Uploading inventory.csv (0.12 MB)... ✓
Uploading purchase_order_header.csv (0.25 MB)... ✓
Uploading purchase_order_line.csv (0.35 MB)... ✓
Uploading sales_order_header.csv (0.30 MB)... ✓
Uploading sales_order_line.csv (0.45 MB)... ✓
============================================================
Upload complete!
  Successful: 8
  Failed: 0
```

### Step 5: Verify in S3
Check files in AWS Console:
```
s3://supply-chain-data-bucket/synthetic_data/
  ├── product.csv
  ├── warehouse.csv
  ├── supplier.csv
  ├── inventory.csv
  ├── purchase_order_header.csv
  ├── purchase_order_line.csv
  ├── sales_order_header.csv
  └── sales_order_line.csv
```

## Data Characteristics

### Seasonality
Sales orders include realistic seasonality:
- **Q4 (Oct-Dec):** 15-30 orders/day (peak season)
- **Q1 (Jan-Feb):** 5-12 orders/day (low season)
- **Q2-Q3:** 8-18 orders/day (normal season)

### Supplier Performance
Suppliers have varied performance metrics:
- **Reliability score:** 0.70 - 0.99
- **Lead time:** 3 - 21 days
- **Defect rate:** 0.001 - 0.05 (0.1% - 5%)

### Inventory Distribution
- Not all products stocked in all warehouses (70% coverage)
- Quantity ranges: 0 - 500 units per SKU per warehouse
- Some SKUs intentionally below reorder point for testing

## Troubleshooting

### Error: "Data directory not found"
Run `generate_synthetic_data.py` first to create the CSV files.

### Error: "Bucket does not exist"
Create the S3 bucket:
```bash
aws s3 mb s3://supply-chain-data-bucket --region eu-west-2
```

### Error: "Access Denied"
Ensure your IAM user/role has these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::supply-chain-data-bucket",
        "arn:aws:s3:::supply-chain-data-bucket/*"
      ]
    }
  ]
}
```

### AWS Credentials Not Configured
Configure AWS CLI:
```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=eu-west-2
```

## Next Steps

After uploading data to S3:
1. Create Redshift cluster (see `database/README.md`)
2. Execute schema DDL scripts
3. Configure AWS Glue ETL job to load data from S3 to Redshift
4. Verify data loaded successfully in Redshift Query Editor
