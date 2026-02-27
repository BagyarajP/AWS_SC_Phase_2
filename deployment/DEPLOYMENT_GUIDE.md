# Supply Chain AI Platform - Deployment Guide

Complete deployment guide for the MVP supply chain AI platform on AWS.

## Prerequisites

- AWS Account with admin access
- AWS CLI configured
- Python 3.9+ installed locally
- Git repository cloned

## Deployment Overview

The deployment consists of 6 main steps:

1. **Redshift Setup** - Create data warehouse and load schema
2. **S3 Setup** - Create buckets and upload synthetic data
3. **Glue Setup** - Deploy ETL job
4. **Lambda Deployment** - Deploy all agent functions
5. **SageMaker Setup** - Deploy Streamlit dashboard
6. **EventBridge Configuration** - Schedule agent execution

---

## Step 1: Redshift Setup

### 1.1 Create Redshift Cluster

1. Navigate to Amazon Redshift Console
2. Click "Create cluster"
3. Configure cluster:
   - **Cluster identifier**: `supply-chain-cluster`
   - **Node type**: `dc2.large`
   - **Number of nodes**: 1 (single-node for MVP)
   - **Database name**: `supply_chain`
   - **Master username**: `admin`
   - **Master password**: (set secure password)
   - **VPC**: Default VPC
   - **Publicly accessible**: Yes (for MVP only)

4. Click "Create cluster"
5. Wait for cluster status: "Available" (~10 minutes)

### 1.2 Configure Security Group

1. Select your cluster
2. Go to "Properties" → "Network and security"
3. Click on security group
4. Add inbound rule:
   - **Type**: Redshift
   - **Port**: 5439
   - **Source**: Your IP address (for testing)
   - **Source**: Lambda security group (for production)

### 1.3 Load Database Schema

```bash
# Connect to Redshift using psql or SQL client
psql -h supply-chain-cluster.xxxxx.eu-west-2.redshift.amazonaws.com \
     -U admin -d supply_chain -p 5439

# Run schema creation script
\i database/schema.sql
```

### 1.4 Create Database Users

```sql
-- Create users for different services
CREATE USER lambda_user WITH PASSWORD 'secure_password_1';
CREATE USER glue_user WITH PASSWORD 'secure_password_2';
CREATE USER streamlit_user WITH PASSWORD 'secure_password_3';

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO lambda_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO glue_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO streamlit_user;
```

---

## Step 2: S3 Setup

### 2.1 Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://supply-chain-data-bucket-<account-id> --region eu-west-2

# Create folder structure
aws s3api put-object --bucket supply-chain-data-bucket-<account-id> \
    --key synthetic_data/ --region eu-west-2
aws s3api put-object --bucket supply-chain-data-bucket-<account-id> \
    --key temp/ --region eu-west-2
```

### 2.2 Generate and Upload Synthetic Data

```bash
# Generate synthetic data
cd scripts
python generate_synthetic_data.py

# Upload to S3
python upload_to_s3.py --bucket supply-chain-data-bucket-<account-id>
```

### 2.3 Verify Upload

```bash
aws s3 ls s3://supply-chain-data-bucket-<account-id>/synthetic_data/
```

Expected files:
- product.csv
- warehouse.csv
- supplier.csv
- inventory.csv
- purchase_order_header.csv
- purchase_order_line.csv
- sales_order_header.csv
- sales_order_line.csv

---

## Step 3: Glue Setup

### 3.1 Create Glue Connection

1. Navigate to AWS Glue Console
2. Click "Connections" → "Add connection"
3. Configure connection:
   - **Name**: `supply-chain-redshift`
   - **Connection type**: JDBC
   - **JDBC URL**: `jdbc:redshift://supply-chain-cluster.xxxxx.eu-west-2.redshift.amazonaws.com:5439/supply_chain`
   - **Username**: `glue_user`
   - **Password**: (from Step 1.4)
   - **VPC**: Same as Redshift cluster

4. Test connection

### 3.2 Deploy Glue Job

```bash
# Package Glue job
cd glue
zip -r glue_job.zip etl_job.py

# Upload to S3
aws s3 cp glue_job.zip s3://supply-chain-data-bucket-<account-id>/glue/

# Create Glue job via Console
# - Name: supply-chain-etl
# - IAM role: SupplyChainGlueRole (from IAM_CONFIGURATION.md)
# - Type: Python Shell
# - Python version: 3.9
# - Script location: s3://supply-chain-data-bucket-<account-id>/glue/etl_job.py
# - Max capacity: 1 DPU
# - Timeout: 60 minutes
```

### 3.3 Run Glue Job

1. Navigate to Glue Console
2. Select `supply-chain-etl` job
3. Click "Run job"
4. Monitor execution in "Run history"
5. Verify data loaded in Redshift

---

## Step 4: Lambda Deployment

### 4.1 Package Lambda Functions

```bash
# Forecasting Agent
cd lambda/forecasting_agent
pip install -r requirements.txt -t .
zip -r forecasting_agent.zip .

# Procurement Agent
cd ../procurement_agent
pip install -r requirements.txt -t .
zip -r procurement_agent.zip .

# Inventory Agent
cd ../inventory_agent
pip install -r requirements.txt -t .
zip -r inventory_agent.zip .

# Metrics Calculator
cd ../metrics_calculator
pip install -r requirements.txt -t .
zip -r metrics_calculator.zip .
```

### 4.2 Create Lambda Functions

For each agent, create Lambda function via Console:

1. Navigate to AWS Lambda Console
2. Click "Create function"
3. Configure:
   - **Function name**: `supply-chain-<agent-name>`
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64
   - **Execution role**: SupplyChainAgentRole (from IAM_CONFIGURATION.md)

4. Upload .zip file
5. Configure environment variables:
   ```
   REDSHIFT_HOST=supply-chain-cluster.xxxxx.eu-west-2.redshift.amazonaws.com
   REDSHIFT_PORT=5439
   REDSHIFT_DATABASE=supply_chain
   REDSHIFT_USER=lambda_user
   REDSHIFT_PASSWORD=<password>
   ```

6. Set timeout to 15 minutes
7. Set memory to 512 MB

### 4.3 Test Lambda Functions

Test each function manually:

```bash
# Test Forecasting Agent
aws lambda invoke --function-name supply-chain-forecasting-agent \
    --payload '{}' response.json

# Check response
cat response.json

# Verify CloudWatch logs
aws logs tail /aws/lambda/supply-chain-forecasting-agent --follow
```

Repeat for all agents.

---

## Step 5: SageMaker Setup

### 5.1 Create SageMaker Notebook Instance

1. Navigate to Amazon SageMaker Console
2. Click "Notebook instances" → "Create notebook instance"
3. Configure:
   - **Name**: `supply-chain-dashboard`
   - **Instance type**: `ml.t3.medium`
   - **IAM role**: SupplyChainStreamlitRole (from IAM_CONFIGURATION.md)
   - **VPC**: Same as Redshift cluster
   - **Direct internet access**: Enabled

4. Click "Create notebook instance"
5. Wait for status: "InService" (~5 minutes)

### 5.2 Upload Streamlit App

1. Click "Open JupyterLab"
2. Upload `streamlit_app/` directory
3. Open terminal in JupyterLab

### 5.3 Install Dependencies

```bash
cd streamlit_app
pip install -r requirements.txt
```

### 5.4 Configure Environment Variables

Create `.env` file:

```bash
cat > .env << EOF
REDSHIFT_HOST=supply-chain-cluster.xxxxx.eu-west-2.redshift.amazonaws.com
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=supply_chain
REDSHIFT_USER=streamlit_user
REDSHIFT_PASSWORD=<password>
EOF
```

### 5.5 Run Streamlit App

```bash
# Run in background
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# Check if running
ps aux | grep streamlit
```

### 5.6 Access Dashboard

1. Get SageMaker presigned URL:
   ```bash
   aws sagemaker create-presigned-notebook-instance-url \
       --notebook-instance-name supply-chain-dashboard
   ```

2. Open URL in browser
3. Navigate to port 8501 (may require port forwarding)

---

## Step 6: EventBridge Configuration

Follow instructions in `EVENTBRIDGE_CONFIGURATION.md`:

1. Create rule for Forecasting Agent (1:00 AM UTC)
2. Create rule for Procurement Agent (2:00 AM UTC)
3. Create rule for Inventory Agent (3:00 AM UTC)
4. Create rule for Metrics Calculator (4:00 AM UTC)

---

## Step 7: Integration Testing

### 7.1 End-to-End Workflow Test

1. **Trigger Forecasting Agent**:
   ```bash
   aws lambda invoke --function-name supply-chain-forecasting-agent \
       --payload '{}' response.json
   ```

2. **Verify forecasts in Redshift**:
   ```sql
   SELECT COUNT(*) FROM demand_forecast WHERE forecast_date = CURRENT_DATE;
   ```

3. **Trigger Procurement Agent**:
   ```bash
   aws lambda invoke --function-name supply-chain-procurement-agent \
       --payload '{}' response.json
   ```

4. **Check approval queue**:
   ```sql
   SELECT * FROM approval_queue WHERE status = 'pending';
   ```

5. **Test dashboard approval workflow**:
   - Open Streamlit dashboard
   - Navigate to Procurement Manager view
   - Approve/reject pending decisions
   - Verify audit log entries

6. **Trigger Inventory Agent**:
   ```bash
   aws lambda invoke --function-name supply-chain-inventory-agent \
       --payload '{}' response.json
   ```

7. **Verify transfers**:
   ```sql
   SELECT * FROM agent_decision WHERE decision_type = 'TRANSFER_INVENTORY';
   ```

### 7.2 Property-Based Tests

Run all property tests:

```bash
# Glue ETL tests
cd glue
pytest test_etl_properties.py -v --hypothesis-show-statistics

# Forecasting Agent tests
cd ../lambda/forecasting_agent
pytest test_property_*.py -v --hypothesis-show-statistics

# Procurement Agent tests
cd ../procurement_agent
pytest test_property_*.py -v --hypothesis-show-statistics

# Inventory Agent tests
cd ../inventory_agent
pytest test_property_*.py -v --hypothesis-show-statistics
```

### 7.3 Dashboard Testing

1. Test Procurement Manager dashboard:
   - Pending approvals display
   - Recent purchase orders
   - Supplier performance

2. Test Inventory Manager dashboard:
   - Pending transfer approvals
   - Inventory levels heatmap
   - Inventory metrics
   - Forecast accuracy

3. Test audit log viewer:
   - Search and filter
   - CSV export
   - Audit statistics

---

## Verification Checklist

### Infrastructure
- [ ] Redshift cluster created and accessible
- [ ] S3 bucket created with synthetic data
- [ ] Glue job created and executed successfully
- [ ] All Lambda functions deployed and tested
- [ ] SageMaker notebook instance running
- [ ] EventBridge rules created and enabled

### Data
- [ ] Database schema loaded
- [ ] Synthetic data loaded into all tables
- [ ] Database users created with correct permissions
- [ ] Sample forecasts generated
- [ ] Sample purchase orders created

### Security
- [ ] IAM roles configured (SupplyChainAgentRole, SupplyChainGlueRole, SupplyChainStreamlitRole)
- [ ] Security groups configured
- [ ] Passwords stored securely
- [ ] CloudWatch log groups created

### Functionality
- [ ] Forecasting Agent generates forecasts
- [ ] Procurement Agent creates purchase orders
- [ ] Inventory Agent generates transfer recommendations
- [ ] High-risk decisions route to approval queue
- [ ] Dashboard displays pending approvals
- [ ] Approval/rejection workflow works
- [ ] Audit log records all actions

### Monitoring
- [ ] CloudWatch alarms configured
- [ ] Log retention set to 30 days
- [ ] EventBridge execution metrics visible

---

## Troubleshooting

### Common Issues

1. **Lambda timeout errors**
   - Increase timeout to 15 minutes
   - Check Redshift query performance
   - Verify network connectivity

2. **Redshift connection failures**
   - Check security group rules
   - Verify VPC configuration
   - Test connection from Lambda

3. **Streamlit app not accessible**
   - Check SageMaker instance status
   - Verify port 8501 is open
   - Check environment variables

4. **EventBridge not triggering**
   - Verify rule is enabled
   - Check cron expression
   - Verify Lambda permissions

---

## Cost Estimate (Monthly)

- **Redshift**: dc2.large single-node = ~$180
- **Lambda**: 4 functions × 30 executions × 5 min = ~$5
- **SageMaker**: ml.t3.medium notebook = ~$50
- **S3**: 10 GB storage + requests = ~$1
- **Glue**: 1 DPU × 1 hour/month = ~$0.44
- **EventBridge**: 120 invocations = ~$0.00

**Total**: ~$236/month

---

## Next Steps

1. Configure production security (VPC, private subnets, no public access)
2. Set up automated backups
3. Implement monitoring dashboards
4. Configure alerting for failures
5. Document operational procedures
6. Train users on dashboard
7. Plan for scaling (multi-node Redshift, Lambda concurrency)

---

## References

- [AWS Redshift Getting Started](https://docs.aws.amazon.com/redshift/latest/gsg/getting-started.html)
- [AWS Lambda Deployment](https://docs.aws.amazon.com/lambda/latest/dg/lambda-deploy-functions.html)
- [SageMaker Notebook Instances](https://docs.aws.amazon.com/sagemaker/latest/dg/nbi.html)
- [EventBridge Rules](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html)
