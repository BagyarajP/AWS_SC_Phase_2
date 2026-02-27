# Supply Chain AI Platform - Setup Guide

This guide walks through the complete setup process for the Supply Chain AI Platform MVP.

## Prerequisites

### Required Software
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **AWS CLI** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **AWS Account** with appropriate permissions

### Required AWS Services
- Amazon Redshift
- Amazon S3
- AWS Glue
- AWS Lambda
- Amazon SageMaker
- AWS IAM
- Amazon EventBridge
- Amazon CloudWatch

## Setup Steps

### Phase 1: Database Setup (Task 1 - CURRENT)

#### 1.1 Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 1.2 Generate Synthetic Data
```bash
cd scripts
python generate_synthetic_data.py
```

This creates a `synthetic_data/` directory with 8 CSV files:
- product.csv (2,000 SKUs)
- warehouse.csv (3 warehouses)
- supplier.csv (500 suppliers)
- inventory.csv (current stock levels)
- sales_order_header.csv (12 months of orders)
- sales_order_line.csv (order line items)
- purchase_order_header.csv (historical POs)
- purchase_order_line.csv (PO line items)

#### 1.3 Create S3 Bucket
```bash
aws s3 mb s3://supply-chain-data-bucket --region eu-west-2
```

#### 1.4 Upload Data to S3
```bash
export S3_BUCKET_NAME=supply-chain-data-bucket
python upload_to_s3.py
```

#### 1.5 Create Redshift Cluster

**Using AWS Console:**
1. Navigate to Amazon Redshift
2. Click "Create cluster"
3. Settings:
   - Cluster identifier: `supply-chain-cluster`
   - Node type: `dc2.large`
   - Nodes: 1
   - Database: `supply_chain`
   - Admin username: `admin`
   - Admin password: (set securely)
   - Region: `eu-west-2` (London)
4. Create cluster (takes 5-10 minutes)

#### 1.6 Execute Schema DDL
Once cluster is available:

**Option A: Redshift Query Editor v2 (Console)**
1. Open Redshift Query Editor v2
2. Connect to `supply-chain-cluster`
3. Copy contents of `database/schema.sql`
4. Execute

**Option B: psql CLI**
```bash
psql -h <cluster-endpoint> -U admin -d supply_chain -p 5439 -f database/schema.sql
```

#### 1.7 Verify Tables Created
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

Expected: 13 tables

### Phase 2: Data Ingestion (Task 2 - COMPLETED)

#### 2.1 Create IAM Role for Glue
Create role `SupplyChainGlueRole` with permissions:
- `AWSGlueServiceRole` (managed policy)
- Custom policy for S3 and Redshift access:

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
        "arn:aws:s3:::supply-chain-data-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::supply-chain-data-bucket/temp/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift:GetClusterCredentials",
        "redshift-data:ExecuteStatement"
      ],
      "Resource": "arn:aws:redshift:eu-west-2:*:cluster:supply-chain-cluster"
    }
  ]
}
```

#### 2.2 Create Glue Connection to Redshift
1. Navigate to AWS Glue Console → Connections
2. Click "Add connection"
3. Configure:
   - Connection name: `supply-chain-redshift`
   - Connection type: Amazon Redshift
   - Cluster: `supply-chain-cluster`
   - Database name: `supply_chain`
   - Username: `admin`
   - Password: (your Redshift password)
4. Test connection

#### 2.3 Deploy Glue ETL Job

**Option A: Using Deployment Script (Recommended)**
```bash
cd glue

# Set environment variables
export S3_SCRIPTS_BUCKET=your-glue-scripts-bucket
export S3_DATA_BUCKET=supply-chain-data-bucket
export IAM_ROLE_ARN=arn:aws:iam::ACCOUNT_ID:role/SupplyChainGlueRole

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

**Option B: Manual Deployment via AWS Console**
1. Upload `glue/etl_job.py` to S3 scripts bucket
2. Navigate to AWS Glue → ETL Jobs
3. Click "Create job"
4. Configure:
   - Name: `supply-chain-etl-job`
   - IAM Role: `SupplyChainGlueRole`
   - Type: Spark
   - Glue version: 4.0
   - Language: Python 3
   - Script location: `s3://your-scripts-bucket/supply-chain-ai/etl_job.py`
5. Add job parameters:
   - `--S3_BUCKET`: `supply-chain-data-bucket`
   - `--S3_PREFIX`: `synthetic_data/`
   - `--REDSHIFT_CONNECTION`: `supply-chain-redshift`
   - `--REDSHIFT_DATABASE`: `supply_chain`
   - `--REDSHIFT_TEMP_DIR`: `s3://supply-chain-data-bucket/temp/`
6. Set Max capacity: 2 DPU
7. Set Timeout: 60 minutes

#### 2.4 Run Glue ETL Job

**Via AWS Console:**
1. Go to AWS Glue → ETL Jobs
2. Select `supply-chain-etl-job`
3. Click "Run job"

**Via AWS CLI:**
```bash
aws glue start-job-run --job-name supply-chain-etl-job
```

#### 2.5 Monitor Job Execution
1. View progress in Glue Console
2. Check CloudWatch Logs for detailed execution logs
3. View custom metrics in CloudWatch:
   - Namespace: `SupplyChainAI/ETL`
   - Metrics: TablesProcessed, RecordsRead, RecordsWritten, SuccessRate

#### 2.6 Verify Data Loaded
Connect to Redshift and verify record counts:

```sql
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
SELECT 'sales_order_line', COUNT(*) FROM sales_order_line;
```

Expected results:
- product: 2,000 records
- warehouse: 3 records
- supplier: 500 records
- inventory: ~4,200 records (70% of products × 3 warehouses)
- sales_order_header: ~4,000-5,000 records (12 months of daily orders)
- sales_order_line: ~15,000-20,000 records
- purchase_order_header: ~1,000-1,500 records
- purchase_order_line: ~2,000-3,000 records

### Phase 3: Lambda Agents (Tasks 4-6)

#### 3.1 Create IAM Role for Lambda
Create role `SupplyChainAgentRole` with permissions:
- `redshift-data:ExecuteStatement`
- `redshift-data:GetStatementResult`
- CloudWatch Logs access

#### 3.2 Deploy Lambda Functions
- Forecasting Agent
- Procurement Agent
- Inventory Rebalancing Agent

#### 3.3 Configure EventBridge Rules
Schedule daily triggers for each agent

### Phase 4: Streamlit Dashboard (Tasks 8-11)

#### 4.1 Create SageMaker Notebook Instance
1. Instance type: `ml.t3.medium`
2. Attach IAM role with Redshift and Lambda access
3. Install Streamlit

#### 4.2 Deploy Dashboard
Upload Streamlit app code and run

### Phase 5: Testing and Validation (Task 15)

#### 5.1 End-to-End Testing
- Verify data flow from S3 → Glue → Redshift
- Test agent execution
- Verify approval workflow
- Check audit logging

#### 5.2 Property-Based Testing
Run all 45 property tests (optional tasks marked with *)

## Project Structure

```
supply-chain-ai-platform/
├── database/
│   ├── schema.sql              # Redshift DDL scripts
│   └── README.md               # Database setup guide
├── scripts/
│   ├── generate_synthetic_data.py  # Data generation
│   ├── upload_to_s3.py            # S3 uploader
│   └── README.md                  # Scripts documentation
├── glue/                       # Glue ETL job (Task 2 - COMPLETED)
│   ├── etl_job.py             # Main ETL script
│   ├── deploy.sh              # Deployment script
│   ├── requirements.txt       # Dependencies
│   └── README.md              # Glue job documentation
├── lambda/                     # Lambda function code (Task 4-6)
├── streamlit/                  # Dashboard code (Task 8-11)
├── tests/                      # Property-based tests
├── requirements.txt            # Python dependencies
├── SETUP_GUIDE.md             # This file
└── .kiro/specs/supply-chain-ai-platform/
    ├── requirements.md         # Business requirements
    ├── design.md              # Technical design
    └── tasks.md               # Implementation tasks
```

## AWS Resource Naming Convention

- **S3 Bucket:** `supply-chain-data-bucket`
- **Redshift Cluster:** `supply-chain-cluster`
- **Database:** `supply_chain`
- **IAM Roles:**
  - `SupplyChainAgentRole` (Lambda)
  - `SupplyChainGlueRole` (Glue)
  - `SupplyChainStreamlitRole` (SageMaker)
- **Lambda Functions:**
  - `supply-chain-forecasting-agent`
  - `supply-chain-procurement-agent`
  - `supply-chain-inventory-agent`

## Cost Estimates (MVP)

- **Redshift dc2.large:** ~£0.25/hour (~£180/month)
- **S3 Storage:** ~£0.02/month (minimal data)
- **Lambda:** Free tier covers MVP usage
- **Glue:** ~£0.44/DPU-hour (one-time load)
- **SageMaker ml.t3.medium:** ~£0.05/hour (~£36/month)

**Total Monthly Cost:** ~£220/month for MVP

## Security Considerations

1. **Network:** Deploy Redshift in private subnet for production
2. **Encryption:** Enable encryption at rest for Redshift and S3
3. **IAM:** Use least-privilege access policies
4. **Secrets:** Store database credentials in AWS Secrets Manager
5. **Audit:** Enable CloudTrail for all API calls

## Troubleshooting

### Python Not Found
Install Python 3.9+ from [python.org](https://www.python.org/downloads/)

### AWS CLI Not Configured
```bash
aws configure
```

### Redshift Connection Timeout
Check security group allows inbound on port 5439

### Glue Job Fails
- Verify IAM role permissions
- Check S3 bucket and file paths
- Review CloudWatch logs

## Next Steps

After completing Tasks 1-2:
1. ✅ Task 1: Database setup and synthetic data generation - COMPLETE
2. ✅ Task 2: AWS Glue ETL job implementation - COMPLETE
3. Verify data loaded successfully in Redshift (see Phase 2.6)
4. Proceed to Task 3: Checkpoint - Verify data ingestion
5. Continue with Task 4: Implement Forecasting Agent Lambda function

## Support

For issues or questions:
1. Check AWS service documentation
2. Review CloudWatch logs
3. Verify IAM permissions
4. Consult the design document (`.kiro/specs/supply-chain-ai-platform/design.md`)
