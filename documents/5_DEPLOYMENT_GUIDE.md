# Supply Chain AI Platform - Deployment Guide

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Target Audience**: DevOps Engineers, Cloud Architects, Technical Teams

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture Summary](#architecture-summary)
4. [Deployment Steps](#deployment-steps)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)
7. [Cost Management](#cost-management)

---

## Overview

This guide provides step-by-step instructions for deploying the Supply Chain AI Platform MVP to AWS. The platform uses a serverless architecture with AWS Bedrock Agents, Lambda tools, Redshift Serverless, Glue ETL, and Streamlit on SageMaker.

### Deployment Timeline

- **Estimated Time**: 4-6 hours for complete deployment
- **Region**: us-east-1 (N. Virginia)
- **Approach**: Console-based deployment for MVP

### Key Components

- 3 Bedrock Agents (Forecasting, Procurement, Inventory)
- 13 Lambda functions (agent tools)
- Redshift Serverless (32 RPUs)
- AWS Glue ETL job
- Streamlit dashboard on SageMaker
- EventBridge schedules
- IAM roles and policies

---

## Prerequisites

### AWS Account Requirements

- AWS Account with admin access
- Bedrock model access enabled for Claude 3.5 Sonnet in us-east-1
- Service quotas verified:
  - Lambda: 1000 concurrent executions
  - Redshift Serverless: 32 RPUs minimum
  - SageMaker: ml.t3.medium instance

### Local Development Environment

```bash
# Required software
- AWS CLI v2.x
- Python 3.9+
- Git
- jq (JSON processor)
- psql (PostgreSQL client for Redshift)

# Verify installations
aws --version
python --version
git --version
jq --version
psql --version
```

### AWS CLI Configuration

```bash
# Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output format (json)

# Verify configuration
aws sts get-caller-identity
```

### Enable Bedrock Model Access

1. Navigate to AWS Bedrock Console → Model access
2. Request access to: `anthropic.claude-3-5-sonnet-20241022-v2:0`
3. Wait for approval (typically instant for most accounts)

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  Supply Chain AI Platform                    │
│                     (us-east-1 Region)                       │
└─────────────────────────────────────────────────────────────┘

EventBridge Schedules → Bedrock Agents (3) → Lambda Tools (13)
                              ↓                      ↓
                        Claude 3.5 Sonnet    Redshift Serverless
                                                     ↑
                        Glue ETL ← S3 Buckets       │
                                                     │
                        Streamlit (SageMaker) ──────┘
```

---

## Deployment Steps

### Phase 1: Foundation Setup (60 minutes)

#### Step 1.1: Create S3 Bucket

```bash
# Set variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export S3_BUCKET="supply-chain-data-${AWS_ACCOUNT_ID}"
export AWS_REGION="us-east-1"

# Create bucket
aws s3 mb s3://${S3_BUCKET} --region ${AWS_REGION}

# Create folder structure
aws s3api put-object --bucket ${S3_BUCKET} --key synthetic_data/
aws s3api put-object --bucket ${S3_BUCKET} --key glue/
aws s3api put-object --bucket ${S3_BUCKET} --key lambda/
```

#### Step 1.2: Deploy Redshift Serverless

**Via AWS Console**:

1. Navigate to Amazon Redshift Console
2. Click "Redshift Serverless" → "Create workgroup"
3. Configure:
   - **Workgroup name**: `supply-chain-workgroup`
   - **Namespace**: Create new → `supply-chain-namespace`
   - **Database name**: `supply_chain`
   - **Admin username**: `admin`
   - **Admin password**: (set secure password - save to AWS Secrets Manager)
   - **Base capacity**: 32 RPUs
   - **VPC**: Default VPC
   - **Subnet group**: Default
   - **Security group**: Create new → `supply-chain-sg`
   - **Publicly accessible**: No (use VPC endpoints)
4. Click "Create workgroup"
5. Wait for status: "Available" (~10 minutes)

**Security Group Configuration**:

```bash
# Get security group ID
export SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=supply-chain-sg" \
  --query "SecurityGroups[0].GroupId" --output text)

# Add inbound rule for Redshift Data API (no direct connection needed)
# Lambda functions will use Redshift Data API which doesn't require security group rules
```

#### Step 1.3: Load Database Schema

```bash
# Clone repository
git clone <repository-url>
cd supply-chain-ai-platform

# Connect using Redshift Data API
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "$(cat database/schema.sql)"

# Check execution status
aws redshift-data describe-statement --id <statement-id>
```

#### Step 1.4: Generate and Upload Synthetic Data

```bash
# Generate synthetic data
cd scripts
python generate_synthetic_data.py

# Upload to S3
python upload_to_s3.py --bucket ${S3_BUCKET}

# Verify upload
aws s3 ls s3://${S3_BUCKET}/synthetic_data/
```

---

### Phase 2: IAM Configuration (30 minutes)

#### Step 2.1: Create IAM Roles

Follow instructions in `deployment/IAM_CONFIGURATION.md` to create:

1. **SupplyChainBedrockAgentRole** - For Bedrock Agents
2. **SupplyChainToolRole** - For Lambda tools
3. **SupplyChainGlueRole** - For Glue ETL
4. **SupplyChainStreamlitRole** - For SageMaker
5. **EventBridgeBedrockAgentRole** - For EventBridge

```bash
# Create all roles using provided scripts
cd deployment/iam
./create-all-roles.sh
```

---

### Phase 3: Glue ETL Deployment (30 minutes)

#### Step 3.1: Package and Upload Glue Job

```bash
cd glue

# Upload ETL script to S3
aws s3 cp etl_job.py s3://${S3_BUCKET}/glue/etl_job.py
```

#### Step 3.2: Create Glue Job via Console

1. Navigate to AWS Glue Console
2. Click "ETL jobs" → "Script editor"
3. Configure:
   - **Name**: `supply-chain-etl`
   - **IAM role**: `SupplyChainGlueRole`
   - **Type**: Python Shell
   - **Python version**: 3.9
   - **Script location**: `s3://${S3_BUCKET}/glue/etl_job.py`
   - **Max capacity**: 1 DPU
   - **Timeout**: 60 minutes
   - **Job parameters**:
     - `--S3_BUCKET`: `${S3_BUCKET}`
     - `--REDSHIFT_WORKGROUP`: `supply-chain-workgroup`
     - `--REDSHIFT_DATABASE`: `supply_chain`
4. Click "Create job"

#### Step 3.3: Run Glue Job

```bash
# Start job run
aws glue start-job-run --job-name supply-chain-etl

# Monitor execution
aws glue get-job-run --job-name supply-chain-etl --run-id <run-id>
```

---

### Phase 4: Lambda Tools Deployment (90 minutes)

#### Step 4.1: Package Lambda Functions

```bash
# Forecasting Agent Tools
cd lambda/forecasting_agent/tools

for tool in get_historical_sales calculate_forecast store_forecast calculate_accuracy; do
  cd ${tool}
  pip install -r requirements.txt -t .
  zip -r ${tool}.zip .
  aws s3 cp ${tool}.zip s3://${S3_BUCKET}/lambda/forecasting/
  cd ..
done

# Procurement Agent Tools
cd ../procurement_agent/tools

for tool in get_inventory_levels get_demand_forecast get_supplier_data calculate_eoq create_purchase_order; do
  cd ${tool}
  pip install -r requirements.txt -t .
  zip -r ${tool}.zip .
  aws s3 cp ${tool}.zip s3://${S3_BUCKET}/lambda/procurement/
  cd ..
done

# Inventory Agent Tools
cd ../inventory_agent/tools

for tool in get_warehouse_inventory get_regional_forecasts calculate_imbalance_score execute_transfer; do
  cd ${tool}
  pip install -r requirements.txt -t .
  zip -r ${tool}.zip .
  aws s3 cp ${tool}.zip s3://${S3_BUCKET}/lambda/inventory/
  cd ..
done
```

#### Step 4.2: Create Lambda Functions via Console

For each tool, create Lambda function:

1. Navigate to AWS Lambda Console
2. Click "Create function"
3. Configure:
   - **Function name**: `supply-chain-<agent>-<tool>`
   - **Runtime**: Python 3.9
   - **Architecture**: x86_64
   - **Execution role**: Use existing → `SupplyChainToolRole`
4. Upload .zip from S3
5. Set environment variables:
   ```
   REDSHIFT_WORKGROUP=supply-chain-workgroup
   REDSHIFT_DATABASE=supply_chain
   ```
6. Set timeout: 15 minutes
7. Set memory: 512 MB

**Automation Script**:

```bash
# Create all Lambda functions
cd deployment/lambda
./deploy-all-functions.sh
```

---

### Phase 5: Bedrock Agents Configuration (60 minutes)

#### Step 5.1: Create Forecasting Bedrock Agent

**Via AWS Console**:

1. Navigate to AWS Bedrock Console → Agents
2. Click "Create Agent"
3. Configure:
   - **Agent name**: `supply-chain-forecasting-agent`
   - **Agent description**: "Autonomous demand forecasting agent"
   - **IAM role**: `SupplyChainBedrockAgentRole`
   - **Foundation model**: `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - **Instructions**: (paste from `lambda/forecasting_agent/config.json`)
4. Add Action Group:
   - **Name**: `forecasting-tools`
   - **Action group type**: Define with API schemas
   - **Lambda function**: Select all forecasting tool functions
   - **API schema**: Upload OpenAPI schema from `lambda/forecasting_agent/openapi.json`
5. Click "Create Agent"
6. Create Alias: `PROD`
7. Note Agent ID and Alias ID

#### Step 5.2: Create Procurement Bedrock Agent

Repeat Step 5.1 with:
- **Agent name**: `supply-chain-procurement-agent`
- **Instructions**: From `lambda/procurement_agent/config.json`
- **Action group**: `procurement-tools`
- **Lambda functions**: All procurement tool functions
- **API schema**: `lambda/procurement_agent/openapi.json`

#### Step 5.3: Create Inventory Bedrock Agent

Repeat Step 5.1 with:
- **Agent name**: `supply-chain-inventory-agent`
- **Instructions**: From `lambda/inventory_agent/config.json`
- **Action group**: `inventory-tools`
- **Lambda functions**: All inventory tool functions
- **API schema**: `lambda/inventory_agent/openapi.json`

---

### Phase 6: EventBridge Scheduling (20 minutes)

Follow instructions in `deployment/EVENTBRIDGE_CONFIGURATION.md`:

```bash
# Set Agent IDs
export FORECASTING_AGENT_ID="<from-step-5.1>"
export PROCUREMENT_AGENT_ID="<from-step-5.2>"
export INVENTORY_AGENT_ID="<from-step-5.3>"

# Create schedules
cd deployment/eventbridge
./create-schedules.sh
```

**Schedules Created**:
- Forecasting Agent: Daily at 1:00 AM UTC
- Procurement Agent: Daily at 2:00 AM UTC
- Inventory Agent: Daily at 3:00 AM UTC

---

### Phase 7: Streamlit Dashboard Deployment (45 minutes)

#### Step 7.1: Create SageMaker Notebook Instance

1. Navigate to Amazon SageMaker Console
2. Click "Notebook instances" → "Create notebook instance"
3. Configure:
   - **Name**: `supply-chain-dashboard`
   - **Instance type**: `ml.t3.medium`
   - **IAM role**: `SupplyChainStreamlitRole`
   - **VPC**: Same as Redshift Serverless
   - **Subnet**: Private subnet with NAT gateway
   - **Direct internet access**: Enabled
4. Click "Create notebook instance"
5. Wait for status: "InService" (~5 minutes)

#### Step 7.2: Upload Streamlit App

1. Click "Open JupyterLab"
2. Upload `streamlit_app/` directory
3. Open terminal in JupyterLab

#### Step 7.3: Install Dependencies and Run

```bash
cd streamlit_app

# Install dependencies
pip install -r requirements.txt

# Create environment file
cat > .env << EOF
REDSHIFT_WORKGROUP=supply-chain-workgroup
REDSHIFT_DATABASE=supply_chain
FORECASTING_AGENT_ID=${FORECASTING_AGENT_ID}
PROCUREMENT_AGENT_ID=${PROCUREMENT_AGENT_ID}
INVENTORY_AGENT_ID=${INVENTORY_AGENT_ID}
EOF

# Run Streamlit
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# Verify running
ps aux | grep streamlit
```

#### Step 7.4: Access Dashboard

```bash
# Get presigned URL
aws sagemaker create-presigned-notebook-instance-url \
  --notebook-instance-name supply-chain-dashboard

# Open URL in browser and navigate to port 8501
```

---

## Verification & Testing

### End-to-End Workflow Test

#### Test 1: Forecasting Agent

```bash
# Manually invoke agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id ${FORECASTING_AGENT_ID} \
  --agent-alias-id PROD \
  --session-id test-session-1 \
  --input-text "Generate 7-day forecasts for all products"

# Verify forecasts in Redshift
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT COUNT(*) FROM demand_forecast WHERE forecast_date = CURRENT_DATE"
```

#### Test 2: Procurement Agent

```bash
# Invoke agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id ${PROCUREMENT_AGENT_ID} \
  --agent-alias-id PROD \
  --session-id test-session-2 \
  --input-text "Check inventory levels and create purchase orders for items below reorder point"

# Check approval queue
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT * FROM approval_queue WHERE status = 'pending'"
```

#### Test 3: Dashboard Approval Workflow

1. Open Streamlit dashboard
2. Navigate to Procurement Manager view
3. Verify pending approvals display
4. Approve one decision
5. Verify audit log entry created

#### Test 4: Property-Based Tests

```bash
# Run all property tests
cd glue
pytest test_etl_properties.py -v --hypothesis-show-statistics

cd ../lambda/forecasting_agent
pytest test_property_*.py -v

cd ../procurement_agent
pytest test_property_*.py -v

cd ../inventory_agent
pytest test_property_*.py -v
```

### Verification Checklist

- [ ] Redshift Serverless workgroup is "Available"
- [ ] All 13 Lambda functions deployed and tested
- [ ] 3 Bedrock Agents created with aliases
- [ ] EventBridge schedules enabled
- [ ] Glue ETL job completed successfully
- [ ] Synthetic data loaded into Redshift
- [ ] Streamlit dashboard accessible
- [ ] Forecasting agent generates forecasts
- [ ] Procurement agent creates purchase orders
- [ ] Inventory agent generates transfer recommendations
- [ ] High-risk decisions route to approval queue
- [ ] Approval workflow functions correctly
- [ ] Audit log records all actions
- [ ] CloudWatch logs visible for all components

---

## Troubleshooting

### Common Issues

#### Issue 1: Lambda Timeout Errors

**Symptoms**: Lambda functions timing out when querying Redshift

**Solutions**:
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name <function-name> \
  --timeout 900

# Check Redshift query performance
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT * FROM svl_qlog ORDER BY starttime DESC LIMIT 10"
```

#### Issue 2: Bedrock Agent Not Invoking Tools

**Symptoms**: Agent responds but doesn't call Lambda tools

**Solutions**:
1. Verify Lambda resource-based policy allows Bedrock invocation
2. Check OpenAPI schema matches tool signatures
3. Review agent instructions for clarity
4. Check CloudWatch logs for error messages

```bash
# Add resource-based policy to Lambda
aws lambda add-permission \
  --function-name <function-name> \
  --statement-id bedrock-agent-access \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn arn:aws:bedrock:us-east-1:${AWS_ACCOUNT_ID}:agent/*
```

#### Issue 3: Redshift Data API Connection Failures

**Symptoms**: Lambda functions can't execute Redshift queries

**Solutions**:
```bash
# Verify IAM role has Redshift Data API permissions
aws iam get-role-policy \
  --role-name SupplyChainToolRole \
  --policy-name RedshiftDataAPIAccess

# Test Redshift Data API connectivity
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT 1"
```

#### Issue 4: Streamlit Dashboard Not Accessible

**Symptoms**: Cannot access Streamlit on port 8501

**Solutions**:
1. Verify SageMaker instance is "InService"
2. Check Streamlit process is running
3. Verify security group allows inbound traffic
4. Use port forwarding if needed

```bash
# Check Streamlit process
ssh -i <key> ec2-user@<sagemaker-instance>
ps aux | grep streamlit

# Restart Streamlit
pkill streamlit
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

#### Issue 5: EventBridge Not Triggering Agents

**Symptoms**: Agents not executing on schedule

**Solutions**:
```bash
# Verify rule is enabled
aws events describe-rule --name supply-chain-forecasting-daily

# Check rule targets
aws events list-targets-by-rule --rule supply-chain-forecasting-daily

# Manually trigger rule for testing
aws events put-events \
  --entries '[{"Source": "manual.test", "DetailType": "Test", "Detail": "{}"}]'
```

### Logs and Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/supply-chain-forecasting-get-historical-sales --follow

# View Bedrock Agent logs
aws logs tail /aws/bedrock/agents/supply-chain-forecasting-agent --follow

# View Glue job logs
aws logs tail /aws-glue/jobs/supply-chain-etl --follow

# View Redshift query logs
aws redshift-data execute-statement \
  --workgroup-name supply-chain-workgroup \
  --database supply_chain \
  --sql "SELECT * FROM sys_query_history ORDER BY start_time DESC LIMIT 20"
```

---

## Cost Management

### Monthly Cost Estimate

| Component | Configuration | Monthly Cost |
|-----------|--------------|--------------|
| Redshift Serverless | 32 RPUs, auto-pause | $50-100 |
| Bedrock (Claude 3.5 Sonnet) | 60K forecasts/month | $1,260 |
| Lambda | 13 functions, 90 invocations/day | Free tier |
| S3 | 10 GB storage | $5 |
| SageMaker | ml.t3.medium, 24/7 | $36 |
| EventBridge | 90 events/month | <$1 |
| CloudWatch | Logs and metrics | $10 |
| **Total** | | **$1,361-1,411/month** |

### Cost Optimization Tips

1. **Enable Redshift Auto-Pause**:
   ```bash
   aws redshift-serverless update-workgroup \
     --workgroup-name supply-chain-workgroup \
     --config-parameters "[{\"parameterKey\":\"auto_pause\",\"parameterValue\":\"true\"}]"
   ```

2. **Stop SageMaker When Not in Use**:
   ```bash
   aws sagemaker stop-notebook-instance \
     --notebook-instance-name supply-chain-dashboard
   ```

3. **Set CloudWatch Log Retention**:
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/lambda/supply-chain-forecasting-agent \
     --retention-in-days 7
   ```

4. **Use Lambda Reserved Concurrency**:
   ```bash
   aws lambda put-function-concurrency \
     --function-name supply-chain-forecasting-agent \
     --reserved-concurrent-executions 5
   ```

---

## Next Steps

After successful deployment:

1. **Security Hardening**:
   - Move Redshift to private subnet
   - Enable VPC endpoints
   - Implement MFA for approvals
   - Enable encryption at rest

2. **Monitoring Setup**:
   - Create CloudWatch dashboards
   - Configure alarms for failures
   - Set up PagerDuty integration

3. **Production Readiness**:
   - Implement all 45 property tests
   - Conduct load testing
   - Create disaster recovery plan
   - Document runbooks

4. **User Training**:
   - Train Procurement Managers
   - Train Inventory Managers
   - Create user guides

---

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Bedrock Agents Guide**: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **Redshift Serverless Guide**: https://docs.aws.amazon.com/redshift/latest/mgmt/serverless.html
- **Project Repository**: <repository-url>
- **Technical Support**: <support-email>

---

**Document End**
