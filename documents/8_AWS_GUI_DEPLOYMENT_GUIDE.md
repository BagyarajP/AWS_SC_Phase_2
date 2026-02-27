# Supply Chain AI Platform - AWS Console GUI Deployment Guide

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Target Audience**: DevOps Engineers, System Administrators, Technical Teams  
**Deployment Method**: AWS Console (GUI-based, no CLI required)

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Foundation Setup](#phase-1-foundation-setup)
4. [Phase 2: IAM Configuration](#phase-2-iam-configuration)
5. [Phase 3: Redshift Serverless](#phase-3-redshift-serverless)
6. [Phase 4: S3 and Data Upload](#phase-4-s3-and-data-upload)
7. [Phase 5: AWS Glue ETL](#phase-5-aws-glue-etl)
8. [Phase 6: Lambda Functions](#phase-6-lambda-functions)
9. [Phase 7: Bedrock Agents](#phase-7-bedrock-agents)
10. [Phase 8: EventBridge Schedules](#phase-8-eventbridge-schedules)
11. [Phase 9: SageMaker Dashboard](#phase-9-sagemaker-dashboard)
12. [Phase 10: Testing and Verification](#phase-10-testing-and-verification)

---

## Overview

This guide provides **detailed step-by-step instructions** for deploying the Supply Chain AI Platform using only the AWS Console GUI. No command-line experience required.

### What You'll Deploy

- 1 Redshift Serverless workgroup
- 1 S3 bucket with synthetic data
- 1 AWS Glue ETL job
- 13 Lambda functions (agent tools)
- 3 Bedrock Agents
- 3 EventBridge schedules
- 1 SageMaker notebook instance
- 5 IAM roles with policies

### Estimated Time

- **Total**: 6-8 hours
- **Can be completed over multiple sessions**
- **Save your progress at each phase**

---

## Prerequisites

### AWS Account Requirements

✅ **AWS Account** with administrator access  
✅ **Bedrock Model Access** enabled for Claude 3.5 Sonnet  
✅ **Service Quotas** verified (see below)  
✅ **Credit Card** on file for AWS billing

### Enable Bedrock Model Access

**Step 1**: Navigate to AWS Bedrock
1. Sign in to AWS Console: https://console.aws.amazon.com
2. In the search bar at top, type "Bedrock"
3. Click "Amazon Bedrock"
4. **Important**: Ensure you're in **us-east-1 (N. Virginia)** region (top-right corner)

**Step 2**: Request Model Access
1. In left sidebar, click "Model access"
2. Click orange "Manage model access" button
3. Scroll to find "Anthropic" section
4. Check the box next to "Claude 3.5 Sonnet v2"
5. Click "Request model access" button at bottom
6. Wait for status to change to "Access granted" (usually instant)

### Verify Service Quotas

**Step 1**: Open Service Quotas Console
1. In AWS Console search bar, type "Service Quotas"
2. Click "Service Quotas"

**Step 2**: Check Lambda Quotas
1. In search box, type "Lambda"
2. Click "AWS Lambda"
3. Find "Concurrent executions" - should be at least 1000
4. If lower, click quota name → "Request quota increase"

**Step 3**: Check Redshift Quotas
1. Go back to Service Quotas
2. Search for "Redshift"
3. Click "Amazon Redshift"
4. Find "Redshift Serverless RPUs" - should allow at least 32 RPUs



---

## Phase 1: Foundation Setup

### Step 1.1: Set Your AWS Region

**CRITICAL**: All resources must be in **us-east-1 (N. Virginia)**

1. Look at top-right corner of AWS Console
2. Click the region dropdown (shows current region)
3. Select "US East (N. Virginia) us-east-1"
4. **Verify** the region shows "N. Virginia" before proceeding

**Why us-east-1?**
- AWS Bedrock with Claude 3.5 Sonnet is optimized for this region
- All services are available
- Lowest latency for Bedrock Agent operations

### Step 1.2: Note Your AWS Account ID

1. Click your account name in top-right corner
2. Your 12-digit Account ID is displayed
3. **Write it down** - you'll need it multiple times
4. Example: 123456789012

---

## Phase 2: IAM Configuration

### Overview

We'll create 5 IAM roles:
1. SupplyChainBedrockAgentRole - For Bedrock Agents
2. SupplyChainToolRole - For Lambda functions
3. SupplyChainGlueRole - For Glue ETL job
4. SupplyChainStreamlitRole - For SageMaker
5. EventBridgeBedrockAgentRole - For EventBridge schedules

### Step 2.1: Create SupplyChainBedrockAgentRole

**Navigate to IAM**:
1. In AWS Console search bar, type "IAM"
2. Click "IAM" (Identity and Access Management)
3. In left sidebar, click "Roles"
4. Click orange "Create role" button

**Configure Trust Relationship**:
1. **Trusted entity type**: Select "AWS service"
2. **Use case**: Scroll down and select "Bedrock"
3. Click "Next"

**Add Permissions**:
1. Click "Create policy" (opens new tab)
2. Click "JSON" tab
3. Delete existing content and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:supply-chain-*"
      ]
    }
  ]
}
```

4. **Replace** `YOUR_ACCOUNT_ID` with your actual 12-digit account ID
5. Click "Next"
6. **Policy name**: Enter "BedrockAgentPermissions"
7. Click "Create policy"
8. Close the tab and return to role creation tab
9. Click refresh icon next to "Create policy" button
10. In search box, type "BedrockAgentPermissions"
11. Check the box next to your new policy
12. Click "Next"

**Name and Create**:
1. **Role name**: Enter "SupplyChainBedrockAgentRole"
2. **Description**: "Allows Bedrock Agents to invoke Lambda tools and use foundation models"
3. Scroll down and click "Create role"

**Update Trust Policy** (Important):
1. Find your new role in the list and click on it
2. Click "Trust relationships" tab
3. Click "Edit trust policy"
4. Replace content with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "YOUR_ACCOUNT_ID"
        }
      }
    }
  ]
}
```

5. **Replace** `YOUR_ACCOUNT_ID` with your account ID
6. Click "Update policy"

✅ **Role 1 Complete!**



### Step 2.2: Create SupplyChainToolRole

**Start Role Creation**:
1. In IAM → Roles, click "Create role"
2. **Trusted entity type**: "AWS service"
3. **Use case**: Select "Lambda"
4. Click "Next"

**Create Custom Policy**:
1. Click "Create policy" (opens new tab)
2. Click "JSON" tab
3. Paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement",
        "redshift-data:CancelStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-serverless:GetWorkgroup",
        "redshift-serverless:GetNamespace"
      ],
      "Resource": [
        "arn:aws:redshift-serverless:us-east-1:YOUR_ACCOUNT_ID:workgroup/*",
        "arn:aws:redshift-serverless:us-east-1:YOUR_ACCOUNT_ID:namespace/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/lambda/*"
    }
  ]
}
```

4. **Replace** `YOUR_ACCOUNT_ID` (appears 3 times)
5. Click "Next"
6. **Policy name**: "LambdaToolPermissions"
7. Click "Create policy"
8. Return to role creation tab, click refresh
9. Search for "LambdaToolPermissions" and check it
10. Click "Next"

**Name and Create**:
1. **Role name**: "SupplyChainToolRole"
2. **Description**: "Allows Lambda tools to access Redshift Data API and CloudWatch"
3. Click "Create role"

✅ **Role 2 Complete!**

### Step 2.3: Create SupplyChainGlueRole

**Start Role Creation**:
1. Click "Create role"
2. **Trusted entity type**: "AWS service"
3. **Use case**: Select "Glue"
4. Click "Next"

**Create Custom Policy**:
1. Click "Create policy"
2. Click "JSON" tab
3. Paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::supply-chain-data-YOUR_ACCOUNT_ID",
        "arn:aws:s3:::supply-chain-data-YOUR_ACCOUNT_ID/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws-glue/*"
    }
  ]
}
```

4. **Replace** `YOUR_ACCOUNT_ID` (appears 4 times)
5. Click "Next"
6. **Policy name**: "GlueJobPermissions"
7. Click "Create policy"
8. Return to role tab, refresh, select "GlueJobPermissions"
9. Click "Next"

**Name and Create**:
1. **Role name**: "SupplyChainGlueRole"
2. **Description**: "Allows Glue job to access S3 and Redshift Serverless"
3. Click "Create role"

✅ **Role 3 Complete!**

### Step 2.4: Create SupplyChainStreamlitRole

**Start Role Creation**:
1. Click "Create role"
2. **Trusted entity type**: "AWS service"
3. **Use case**: Select "SageMaker"
4. Click "Next"

**Create Custom Policy**:
1. Click "Create policy"
2. Click "JSON" tab
3. Paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/*",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:GetStatementResult",
        "redshift-data:DescribeStatement"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:*"
      ]
    }
  ]
}
```

4. **Replace** `YOUR_ACCOUNT_ID` (appears 3 times)
5. Click "Next"
6. **Policy name**: "StreamlitPermissions"
7. Click "Create policy"
8. Return to role tab, refresh, select "StreamlitPermissions"
9. Click "Next"

**Name and Create**:
1. **Role name**: "SupplyChainStreamlitRole"
2. **Description**: "Allows Streamlit app on SageMaker to access Redshift, Bedrock, and Lambda"
3. Click "Create role"

✅ **Role 4 Complete!**

### Step 2.5: Create EventBridgeBedrockAgentRole

**Start Role Creation**:
1. Click "Create role"
2. **Trusted entity type**: "AWS service"
3. **Use case**: Select "EventBridge"
4. Click "Next"

**Create Custom Policy**:
1. Click "Create policy"
2. Click "JSON" tab
3. Paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:agent/*"
      ]
    }
  ]
}
```

4. **Replace** `YOUR_ACCOUNT_ID`
5. Click "Next"
6. **Policy name**: "EventBridgeInvokeBedrockAgent"
7. Click "Create policy"
8. Return to role tab, refresh, select policy
9. Click "Next"

**Name and Create**:
1. **Role name**: "EventBridgeBedrockAgentRole"
2. **Description**: "Allows EventBridge to invoke Bedrock Agents"
3. Click "Create role"

✅ **All 5 IAM Roles Complete!**

**Verify Your Roles**:
1. In IAM → Roles, search for "SupplyChain"
2. You should see 5 roles:
   - SupplyChainBedrockAgentRole
   - SupplyChainToolRole
   - SupplyChainGlueRole
   - SupplyChainStreamlitRole
   - EventBridgeBedrockAgentRole



---

## Phase 3: Redshift Serverless

### Step 3.1: Create Redshift Serverless Workgroup

**Navigate to Redshift**:
1. In AWS Console search bar, type "Redshift"
2. Click "Amazon Redshift"
3. **Verify** you're in us-east-1 (top-right)
4. In left sidebar, click "Redshift Serverless"

**Start Workgroup Creation**:
1. Click orange "Create workgroup" button
2. You'll see "Create workgroup and namespace" page

**Configure Namespace** (Step 1 of 2):
1. **Namespace name**: Enter "supply-chain-namespace"
2. **Database name**: Enter "supply_chain"
3. **Admin user credentials**:
   - Select "Customize admin user credentials"
   - **Admin user name**: Enter "admin"
   - **Admin user password**: Create a strong password
   - **Confirm password**: Re-enter password
   - **⚠️ IMPORTANT**: Save this password securely - you'll need it later
4. **Permissions**: Leave default (will create new IAM role)
5. **Encryption**: Leave default (AWS owned key)
6. Click "Next"

**Configure Workgroup** (Step 2 of 2):
1. **Workgroup name**: Enter "supply-chain-workgroup"
2. **Base capacity**: Select "32 RPUs"
3. **Network and security**:
   - **VPC**: Select your default VPC
   - **VPC security groups**: Select default security group
   - **Subnet**: Select all available subnets
   - **Publicly accessible**: Select "Turn on" (for MVP only)
4. **Enhanced VPC routing**: Leave unchecked
5. **Limits**: Leave defaults
6. Click "Create workgroup"

**Wait for Creation**:
1. You'll see "Creating workgroup..." message
2. Wait 5-10 minutes for status to become "Available"
3. Refresh the page to check status
4. ☕ Take a break while it creates

**Verify Creation**:
1. Once status is "Available", click on "supply-chain-workgroup"
2. Note the **Endpoint** - you'll need this later
3. Example: supply-chain-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com

✅ **Redshift Serverless Created!**

### Step 3.2: Configure Security Group

**Find Security Group**:
1. In Redshift workgroup details, scroll to "Network and security"
2. Click on the security group ID (starts with "sg-")
3. This opens EC2 Security Groups page

**Add Inbound Rule** (Optional for MVP):
1. Click "Edit inbound rules"
2. Click "Add rule"
3. **Type**: Select "Redshift"
4. **Source**: Select "My IP" (for testing from your computer)
5. Click "Save rules"

**Note**: For production, you won't need this rule as Lambda uses Redshift Data API which doesn't require direct connection.

### Step 3.3: Load Database Schema

**Option A: Using Query Editor v2** (Recommended):

1. In Redshift console, click "Query editor v2" in left sidebar
2. Click "Connect to database"
3. **Connection**: Select "Serverless: supply-chain-workgroup"
4. **Authentication**: Select "Database user name and password"
5. **Database**: Enter "supply_chain"
6. **User name**: Enter "admin"
7. **Password**: Enter the password you created
8. Click "Connect"

**Create Tables**:
1. Click "+" to create new query tab
2. Copy the schema from `database/schema.sql` file
3. Paste into query editor
4. Click "Run" button
5. Wait for "Query completed successfully" message
6. Verify tables created: In left sidebar, expand "supply_chain" → "public" → "Tables"
7. You should see 13 tables

**Option B: Using SQL Client** (Alternative):

If you have a SQL client like DBeaver or pgAdmin:
1. Create new connection
2. **Host**: Your Redshift endpoint
3. **Port**: 5439
4. **Database**: supply_chain
5. **User**: admin
6. **Password**: Your password
7. Connect and run schema.sql

✅ **Database Schema Loaded!**

---

## Phase 4: S3 and Data Upload

### Step 4.1: Create S3 Bucket

**Navigate to S3**:
1. In AWS Console search bar, type "S3"
2. Click "S3"
3. Click orange "Create bucket" button

**Configure Bucket**:
1. **Bucket name**: Enter "supply-chain-data-YOUR_ACCOUNT_ID"
   - Replace YOUR_ACCOUNT_ID with your 12-digit account ID
   - Example: supply-chain-data-123456789012
   - **Note**: Bucket names must be globally unique
2. **AWS Region**: Select "US East (N. Virginia) us-east-1"
3. **Object Ownership**: Leave default (ACLs disabled)
4. **Block Public Access**: Leave all boxes checked (recommended)
5. **Bucket Versioning**: Leave disabled
6. **Default encryption**: Leave default (SSE-S3)
7. Click "Create bucket"

✅ **S3 Bucket Created!**

### Step 4.2: Create Folder Structure

**Create Folders**:
1. Click on your new bucket name
2. Click "Create folder" button
3. **Folder name**: Enter "synthetic_data"
4. Click "Create folder"
5. Repeat to create these folders:
   - "glue"
   - "lambda"
   - "temp"

**Verify Structure**:
Your bucket should have 4 folders:
- synthetic_data/
- glue/
- lambda/
- temp/

### Step 4.3: Generate and Upload Synthetic Data

**Generate Data Locally**:

You'll need to run the Python script locally to generate data:

1. Open terminal/command prompt on your computer
2. Navigate to project directory
3. Run:
```bash
cd scripts
python generate_synthetic_data.py
```

4. This creates CSV files in `scripts/output/` directory

**Upload to S3**:

1. In S3 console, click on your bucket
2. Click on "synthetic_data" folder
3. Click "Upload" button
4. Click "Add files"
5. Select all CSV files from `scripts/output/`:
   - product.csv
   - warehouse.csv
   - supplier.csv
   - inventory.csv
   - purchase_order_header.csv
   - purchase_order_line.csv
   - sales_order_header.csv
   - sales_order_line.csv
6. Click "Upload"
7. Wait for "Upload succeeded" message

**Verify Upload**:
1. Navigate to synthetic_data/ folder
2. You should see 8 CSV files
3. Click on one file to verify it uploaded correctly

✅ **Synthetic Data Uploaded!**



---

## Phase 5: AWS Glue ETL

### Step 5.1: Upload Glue Script to S3

**Prepare Script**:
1. Locate `glue/etl_job.py` in your project
2. Open the file and verify it's the correct ETL script

**Upload to S3**:
1. Go to S3 console
2. Navigate to your bucket → "glue" folder
3. Click "Upload"
4. Click "Add files"
5. Select `etl_job.py`
6. Click "Upload"
7. Verify file appears in glue/ folder

### Step 5.2: Create Glue Job

**Navigate to Glue**:
1. In AWS Console search bar, type "Glue"
2. Click "AWS Glue"
3. In left sidebar, expand "ETL jobs"
4. Click "Script editor"

**Configure Job**:
1. Click "Create script" button
2. **Engine**: Select "Python Shell"
3. **Options**: Select "Upload and edit an existing script"
4. Click "Create"

**Upload Script**:
1. Click "Upload script" button
2. Click "Browse S3"
3. Navigate to your bucket → glue → etl_job.py
4. Select the file and click "Choose"
5. The script content will load in the editor

**Configure Job Details**:
1. Click "Job details" tab at top
2. **Name**: Enter "supply-chain-etl"
3. **IAM Role**: Select "SupplyChainGlueRole"
4. **Type**: Python Shell
5. **Python version**: Python 3.9
6. **Data processing units**: 1 DPU
7. **Job timeout**: 60 minutes
8. **Number of retries**: 0

**Add Job Parameters**:
1. Scroll down to "Job parameters" section
2. Click "Add new parameter"
3. Add these parameters:

| Key | Value |
|-----|-------|
| --S3_BUCKET | supply-chain-data-YOUR_ACCOUNT_ID |
| --REDSHIFT_WORKGROUP | supply-chain-workgroup |
| --REDSHIFT_DATABASE | supply_chain |

4. Replace YOUR_ACCOUNT_ID with your account ID

**Save Job**:
1. Click "Save" button at top
2. Wait for "Job saved successfully" message

✅ **Glue Job Created!**

### Step 5.3: Run Glue Job

**Start Job Run**:
1. Click "Run" button at top
2. Confirm by clicking "Run" in popup
3. You'll see "Job run submitted" message

**Monitor Execution**:
1. Click "Runs" tab
2. You'll see your job run with status "Running"
3. Refresh page every 30 seconds to check progress
4. Wait for status to change to "Succeeded" (5-10 minutes)

**View Logs** (if needed):
1. Click on the run ID
2. Scroll to "Logs" section
3. Click "CloudWatch logs" link
4. View execution details and any errors

**Verify Data Loaded**:
1. Go back to Redshift Query Editor v2
2. Run this query:
```sql
SELECT 'product' as table_name, COUNT(*) as row_count FROM product
UNION ALL
SELECT 'warehouse', COUNT(*) FROM warehouse
UNION ALL
SELECT 'supplier', COUNT(*) FROM supplier
UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory;
```
3. Verify you see data in all tables

✅ **ETL Job Complete!**

---

## Phase 6: Lambda Functions

### Overview

We need to create 13 Lambda functions (agent tools). I'll show detailed steps for the first one, then provide a summary for the rest.

### Step 6.1: Prepare Lambda Deployment Packages

**On Your Local Computer**:

For each Lambda function, you need to create a .zip file:

1. Navigate to the function directory
2. Install dependencies
3. Create zip file

**Example for Forecasting Agent - Get Historical Sales**:

```bash
cd lambda/forecasting_agent/tools/get_historical_sales
pip install -r requirements.txt -t .
zip -r get_historical_sales.zip .
```

Repeat for all 13 functions. Or use the provided deployment scripts.

### Step 6.2: Upload Lambda Packages to S3

**Upload All Packages**:
1. Go to S3 console
2. Navigate to your bucket → lambda/ folder
3. Create subfolders:
   - lambda/forecasting/
   - lambda/procurement/
   - lambda/inventory/
4. Upload each .zip file to appropriate subfolder

### Step 6.3: Create Lambda Function (Detailed Example)

**Function: get_historical_sales**

**Navigate to Lambda**:
1. In AWS Console search bar, type "Lambda"
2. Click "Lambda"
3. Click "Create function" button

**Configure Function**:
1. **Function option**: Select "Author from scratch"
2. **Function name**: Enter "supply-chain-forecasting-get-historical-sales"
3. **Runtime**: Select "Python 3.9"
4. **Architecture**: Select "x86_64"
5. **Permissions**: 
   - Expand "Change default execution role"
   - Select "Use an existing role"
   - Choose "SupplyChainToolRole"
6. Click "Create function"

**Upload Code**:
1. Scroll to "Code source" section
2. Click "Upload from" dropdown
3. Select "Amazon S3 location"
4. Enter S3 URI: `s3://supply-chain-data-YOUR_ACCOUNT_ID/lambda/forecasting/get_historical_sales.zip`
5. Click "Save"
6. Wait for code to upload

**Configure Environment Variables**:
1. Click "Configuration" tab
2. Click "Environment variables" in left menu
3. Click "Edit"
4. Click "Add environment variable"
5. Add these variables:

| Key | Value |
|-----|-------|
| REDSHIFT_WORKGROUP | supply-chain-workgroup |
| REDSHIFT_DATABASE | supply_chain |
| AWS_REGION | us-east-1 |

6. Click "Save"

**Configure Timeout and Memory**:
1. Still in "Configuration" tab
2. Click "General configuration" in left menu
3. Click "Edit"
4. **Memory**: 512 MB
5. **Timeout**: 15 minutes (900 seconds)
6. Click "Save"

**Test Function**:
1. Click "Test" tab
2. **Event name**: Enter "test-event"
3. **Event JSON**: Paste:
```json
{
  "product_id": "PROD001",
  "months_back": 12
}
```
4. Click "Save"
5. Click "Test" button
6. Check results in "Execution results" section

✅ **First Lambda Function Created!**

### Step 6.4: Create Remaining Lambda Functions

**Repeat Step 6.3 for each function below**:

**Forecasting Agent Tools** (4 functions):
1. supply-chain-forecasting-get-historical-sales ✅ (done above)
2. supply-chain-forecasting-calculate-forecast
3. supply-chain-forecasting-store-forecast
4. supply-chain-forecasting-calculate-accuracy

**Procurement Agent Tools** (5 functions):
5. supply-chain-procurement-get-inventory-levels
6. supply-chain-procurement-get-demand-forecast
7. supply-chain-procurement-get-supplier-data
8. supply-chain-procurement-calculate-eoq
9. supply-chain-procurement-create-purchase-order

**Inventory Agent Tools** (4 functions):
10. supply-chain-inventory-get-warehouse-inventory
11. supply-chain-inventory-get-regional-forecasts
12. supply-chain-inventory-calculate-imbalance-score
13. supply-chain-inventory-execute-transfer

**Tips for Faster Creation**:
- Use consistent naming: supply-chain-{agent}-{tool-name}
- All use same IAM role: SupplyChainToolRole
- All use same environment variables
- All use 512 MB memory and 15 min timeout
- Upload .zip files from S3 locations

**Verify All Functions**:
1. In Lambda console, you should see 13 functions
2. All should have status "Active"
3. All should use SupplyChainToolRole

✅ **All 13 Lambda Functions Created!**



---

## Phase 7: Bedrock Agents

### Overview

We'll create 3 Bedrock Agents:
1. Forecasting Agent
2. Procurement Agent
3. Inventory Agent

Each agent will have action groups that connect to Lambda functions.

### Step 7.1: Create Forecasting Bedrock Agent

**Navigate to Bedrock**:
1. In AWS Console search bar, type "Bedrock"
2. Click "Amazon Bedrock"
3. In left sidebar, click "Agents"
4. Click "Create Agent" button

**Agent Details**:
1. **Agent name**: Enter "supply-chain-forecasting-agent"
2. **Agent description**: Enter "Autonomous demand forecasting agent for supply chain optimization"
3. **User input**: Leave "Enabled" (default)
4. Click "Next"

**Select Model**:
1. **Model**: Select "Anthropic Claude 3.5 Sonnet v2"
2. **Instructions for the Agent**: Paste this:

```
You are an autonomous demand forecasting agent for a supply chain optimization platform. Your role is to:

1. Generate demand forecasts for all 2,000 SKUs using time series analysis
2. Produce forecasts for both 7-day and 30-day horizons
3. Calculate confidence intervals at 80% and 95% levels
4. Evaluate forecast accuracy by comparing previous predictions to actual demand (MAPE metric)
5. Store all forecasts and accuracy metrics in the database
6. Achieve MAPE below 15% for the top 200 SKUs by volume

Use statistical methods (Holt-Winters, ARIMA) combined with your reasoning capabilities to generate accurate forecasts. Always explain your reasoning and provide confidence scores.
```

3. Click "Next"

**Add Action Group**:
1. Click "Add" button in Action groups section
2. **Action group name**: Enter "forecasting-tools"
3. **Action group type**: Select "Define with API schemas"
4. **Action group invocation**: Select "Select an existing Lambda function"
5. **Lambda function**: Select "supply-chain-forecasting-get-historical-sales"
6. **Action group schema**:
   - Select "Define with in-line OpenAPI schema editor"
   - Click "In-line OpenAPI schema editor"
   - Paste this schema:

```yaml
openapi: 3.0.0
info:
  title: Forecasting Agent Tools API
  version: 1.0.0
  description: Tools for demand forecasting operations
paths:
  /get_historical_sales:
    post:
      summary: Retrieve historical sales data for time series analysis
      operationId: getHistoricalSales
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: string
                  description: Product ID to get sales history for
                months_back:
                  type: integer
                  description: Number of months of historical data to retrieve
              required:
                - product_id
                - months_back
      responses:
        '200':
          description: Historical sales data
          content:
            application/json:
              schema:
                type: object
  /calculate_forecast:
    post:
      summary: Run time series forecasting algorithms
      operationId: calculateForecast
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: string
                historical_data:
                  type: array
                  items:
                    type: object
                horizon_days:
                  type: integer
              required:
                - product_id
                - historical_data
                - horizon_days
      responses:
        '200':
          description: Forecast results
  /store_forecast:
    post:
      summary: Store forecast results in database
      operationId: storeForecast
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: string
                warehouse_id:
                  type: string
                forecast_data:
                  type: object
                horizon_days:
                  type: integer
              required:
                - product_id
                - warehouse_id
                - forecast_data
                - horizon_days
      responses:
        '200':
          description: Forecast stored successfully
  /calculate_accuracy:
    post:
      summary: Calculate MAPE for previous forecasts
      operationId: calculateAccuracy
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                product_id:
                  type: string
                forecast_date:
                  type: string
              required:
                - product_id
                - forecast_date
      responses:
        '200':
          description: Accuracy metrics
```

7. Click "Add"

**Add Lambda Functions to Action Group**:
1. After creating action group, click on it to edit
2. In "Lambda functions" section, click "Add Lambda function"
3. Add all 4 forecasting Lambda functions:
   - supply-chain-forecasting-get-historical-sales
   - supply-chain-forecasting-calculate-forecast
   - supply-chain-forecasting-store-forecast
   - supply-chain-forecasting-calculate-accuracy
4. Click "Save"

**Review and Create**:
1. Click "Next" to review
2. Review all settings
3. Click "Create Agent"

**Create Alias**:
1. After agent is created, click "Create alias" button
2. **Alias name**: Enter "PROD"
3. **Description**: "Production alias"
4. Click "Create alias"
5. **Save the Agent ID and Alias ID** - you'll need these later

**Test Agent**:
1. Click "Test" button in top-right
2. In test panel, enter: "Generate 7-day forecasts for product PROD001"
3. Click "Run"
4. Verify agent responds and attempts to call tools

✅ **Forecasting Agent Created!**

### Step 7.2: Create Procurement Bedrock Agent

**Repeat Step 7.1 with these changes**:

**Agent Details**:
- **Name**: "supply-chain-procurement-agent"
- **Description**: "Autonomous procurement agent for purchase order creation"

**Instructions**:
```
You are an autonomous procurement agent for a supply chain optimization platform. Your role is to:

1. Analyze inventory levels across all warehouses and identify SKUs below reorder points
2. Review demand forecasts for the next 30 days to determine optimal order quantities
3. Evaluate suppliers based on price, reliability, and lead time using a weighted scoring system (40% price, 30% reliability, 30% lead time)
4. Generate purchase order recommendations with clear rationale
5. Calculate confidence scores based on forecast accuracy and supplier performance
6. Route high-risk decisions (PO value > £10,000 OR confidence < 0.7) to human approval queue

Always provide detailed explanations for your decisions, including the top 3 factors that influenced your recommendation.
```

**Action Group**:
- **Name**: "procurement-tools"
- **Lambda functions**: All 5 procurement functions
- **OpenAPI Schema**: Use schema from `lambda/procurement_agent/openapi.json`

**Create Alias**: "PROD"

✅ **Procurement Agent Created!**

### Step 7.3: Create Inventory Bedrock Agent

**Repeat Step 7.1 with these changes**:

**Agent Details**:
- **Name**: "supply-chain-inventory-agent"
- **Description**: "Autonomous inventory rebalancing agent"

**Instructions**:
```
You are an autonomous inventory rebalancing agent for a supply chain optimization platform. Your role is to:

1. Analyze inventory levels across all 3 warehouses (South, Midland, North)
2. Review regional demand forecasts to identify imbalances
3. Calculate inventory-to-demand ratios and identify excess vs. shortage situations
4. Generate transfer recommendations that minimize costs while meeting regional demand
5. Respect warehouse capacity constraints in all recommendations
6. Calculate confidence scores based on forecast accuracy and historical transfer success
7. Route high-risk decisions (transfer > 100 units OR confidence < 0.75) to human approval queue

Always explain your reasoning, including the imbalance score and regional demand patterns.
```

**Action Group**:
- **Name**: "inventory-tools"
- **Lambda functions**: All 4 inventory functions
- **OpenAPI Schema**: Use schema from `lambda/inventory_agent/openapi.json`

**Create Alias**: "PROD"

✅ **Inventory Agent Created!**

**Verify All Agents**:
1. In Bedrock → Agents, you should see 3 agents
2. All should have status "Prepared"
3. All should have "PROD" alias

**Save Agent IDs**:
Write down all 3 Agent IDs and Alias IDs - you'll need them for EventBridge and Streamlit.



---

## Phase 8: EventBridge Schedules

### Overview

We'll create 3 EventBridge rules to trigger agents daily:
1. Forecasting Agent - 1:00 AM UTC
2. Procurement Agent - 2:00 AM UTC
3. Inventory Agent - 3:00 AM UTC

### Step 8.1: Create Forecasting Agent Schedule

**Navigate to EventBridge**:
1. In AWS Console search bar, type "EventBridge"
2. Click "Amazon EventBridge"
3. In left sidebar, click "Rules"
4. Click "Create rule" button

**Define Rule Detail**:
1. **Name**: Enter "supply-chain-forecasting-daily"
2. **Description**: Enter "Trigger Forecasting Bedrock Agent daily at 1:00 AM UTC"
3. **Event bus**: Select "default"
4. **Rule type**: Select "Schedule"
5. Click "Next"

**Define Schedule**:
1. **Schedule pattern**: Select "A schedule that runs at a regular rate, such as every 10 minutes"
2. **Rate expression**: Select "Cron-based schedule"
3. **Cron expression**: Enter `0 1 * * ? *`
   - This means: At 1:00 AM UTC every day
4. **Flexible time window**: Select "Off"
5. Click "Next"

**Select Target**:
1. **Target types**: Select "AWS service"
2. **Select a target**: In dropdown, search for "Bedrock"
3. Select "Bedrock InvokeAgent"
4. **Agent ID**: Paste your Forecasting Agent ID
5. **Agent alias ID**: Enter "PROD"
6. **Input text**: Enter this JSON:
```json
{
  "inputText": "Generate 7-day and 30-day forecasts for all products. Calculate accuracy for previous forecasts."
}
```
7. **Execution role**: Select "Use existing role"
8. **Existing role**: Select "EventBridgeBedrockAgentRole"
9. Click "Next"

**Configure Settings**:
1. **Rule state**: Select "Enabled"
2. Click "Next"

**Review and Create**:
1. Review all settings
2. Click "Create rule"

✅ **Forecasting Schedule Created!**

### Step 8.2: Create Procurement Agent Schedule

**Repeat Step 8.1 with these changes**:

**Rule Details**:
- **Name**: "supply-chain-procurement-daily"
- **Description**: "Trigger Procurement Bedrock Agent daily at 2:00 AM UTC"

**Schedule**:
- **Cron expression**: `0 2 * * ? *` (2:00 AM UTC)

**Target**:
- **Agent ID**: Your Procurement Agent ID
- **Input text**:
```json
{
  "inputText": "Check inventory levels for all products. Create purchase orders for items below reorder point."
}
```

✅ **Procurement Schedule Created!**

### Step 8.3: Create Inventory Agent Schedule

**Repeat Step 8.1 with these changes**:

**Rule Details**:
- **Name**: "supply-chain-inventory-daily"
- **Description**: "Trigger Inventory Bedrock Agent daily at 3:00 AM UTC"

**Schedule**:
- **Cron expression**: `0 3 * * ? *` (3:00 AM UTC)

**Target**:
- **Agent ID**: Your Inventory Agent ID
- **Input text**:
```json
{
  "inputText": "Analyze inventory across all warehouses. Recommend transfers to balance inventory based on demand forecasts."
}
```

✅ **Inventory Schedule Created!**

**Verify All Schedules**:
1. In EventBridge → Rules, you should see 3 rules
2. All should have state "Enabled"
3. All should show next scheduled time

**Test Schedule** (Optional):
1. Click on a rule
2. Click "Actions" dropdown
3. Select "Disable" (to prevent automatic execution during testing)
4. You can manually test by invoking agents from Bedrock console

---

## Phase 9: SageMaker Dashboard

### Step 9.1: Create SageMaker Notebook Instance

**Navigate to SageMaker**:
1. In AWS Console search bar, type "SageMaker"
2. Click "Amazon SageMaker"
3. In left sidebar, click "Notebook instances"
4. Click "Create notebook instance" button

**Notebook Instance Settings**:
1. **Notebook instance name**: Enter "supply-chain-dashboard"
2. **Notebook instance type**: Select "ml.t3.medium"
3. **Elastic Inference**: Select "none"

**Permissions and Encryption**:
1. **IAM role**: Select "Use existing role"
2. **Existing role**: Select "SupplyChainStreamlitRole"
3. **Root access**: Select "Enabled"
4. **Encryption key**: Leave default (no custom encryption)

**Network**:
1. **VPC**: Select your default VPC (same as Redshift)
2. **Subnet**: Select a subnet
3. **Security group(s)**: Select default security group
4. **Direct internet access**: Select "Enable"

**Git Repositories** (Optional):
1. If your code is in Git, you can clone it here
2. Otherwise, you'll upload files manually

**Click "Create notebook instance"**

**Wait for Creation**:
1. Status will show "Pending" for 5-10 minutes
2. Refresh page to check status
3. Wait for status to become "InService"

✅ **SageMaker Notebook Created!**

### Step 9.2: Upload Streamlit Application

**Open JupyterLab**:
1. Once status is "InService", click "Open JupyterLab"
2. JupyterLab interface will open in new tab

**Upload Files**:
1. In left sidebar, you'll see file browser
2. Click upload icon (up arrow)
3. Upload these files from `streamlit_app/` directory:
   - app.py
   - requirements.txt
   - Any other supporting files
4. Files will appear in file browser

**Alternative - Use Terminal to Clone Git**:
1. Click "File" → "New" → "Terminal"
2. In terminal, run:
```bash
git clone <your-repository-url>
cd supply-chain-ai-platform/streamlit_app
```

### Step 9.3: Install Dependencies

**Open Terminal**:
1. In JupyterLab, click "File" → "New" → "Terminal"
2. Terminal will open at bottom

**Navigate to App Directory**:
```bash
cd streamlit_app
```

**Install Requirements**:
```bash
pip install -r requirements.txt
```

Wait for all packages to install (2-3 minutes).

### Step 9.4: Configure Environment Variables

**Create .env File**:
1. In terminal, run:
```bash
cat > .env << 'EOF'
AWS_REGION=us-east-1
REDSHIFT_WORKGROUP=supply-chain-workgroup
REDSHIFT_DATABASE=supply_chain
FORECASTING_AGENT_ID=your-forecasting-agent-id
PROCUREMENT_AGENT_ID=your-procurement-agent-id
INVENTORY_AGENT_ID=your-inventory-agent-id
EOF
```

2. **Replace** the agent IDs with your actual IDs
3. Press Ctrl+D to save

**Verify .env File**:
```bash
cat .env
```

### Step 9.5: Run Streamlit Application

**Start Streamlit**:
```bash
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

**Verify Running**:
```bash
ps aux | grep streamlit
```

You should see streamlit process running.

**View Logs**:
```bash
tail -f nohup.out
```

Press Ctrl+C to stop viewing logs.

### Step 9.6: Access Dashboard

**Option A: Port Forwarding** (Recommended):

1. In SageMaker console, click on your notebook instance
2. Click "Open JupyterLab"
3. In browser URL, you'll see something like:
   `https://supply-chain-dashboard.notebook.us-east-1.sagemaker.aws/lab`
4. Change `/lab` to `/proxy/8501/`
5. Full URL: `https://supply-chain-dashboard.notebook.us-east-1.sagemaker.aws/proxy/8501/`
6. Press Enter
7. Streamlit dashboard should load

**Option B: SSH Tunnel** (Alternative):

If Option A doesn't work, you can create SSH tunnel:
1. Get notebook instance endpoint from SageMaker console
2. Use SSH client to create tunnel
3. Access via localhost:8501

**Verify Dashboard**:
1. You should see "Supply Chain AI Platform" title
2. Sidebar should show role selection
3. Try selecting "Procurement Manager" role
4. Dashboard should display (may show "No data" until agents run)

✅ **Streamlit Dashboard Running!**



---

## Phase 10: Testing and Verification

### Step 10.1: Test Forecasting Agent

**Manual Agent Invocation**:

1. Go to Bedrock console → Agents
2. Click on "supply-chain-forecasting-agent"
3. Click "Test" button in top-right
4. In test panel, enter:
   ```
   Generate 7-day forecasts for all products
   ```
5. Click "Run"
6. Watch agent reasoning and tool calls
7. Verify agent completes successfully

**Verify Forecasts in Database**:

1. Go to Redshift Query Editor v2
2. Connect to supply_chain database
3. Run query:
```sql
SELECT 
    COUNT(*) as forecast_count,
    forecast_date,
    forecast_horizon_days
FROM demand_forecast
WHERE forecast_date = CURRENT_DATE
GROUP BY forecast_date, forecast_horizon_days;
```
4. You should see forecasts for today

✅ **Forecasting Agent Working!**

### Step 10.2: Test Procurement Agent

**Manual Agent Invocation**:

1. Go to Bedrock console → Agents
2. Click on "supply-chain-procurement-agent"
3. Click "Test"
4. Enter:
   ```
   Check inventory levels and create purchase orders for items below reorder point
   ```
5. Click "Run"
6. Verify agent analyzes inventory and makes recommendations

**Check Approval Queue**:

1. In Redshift Query Editor, run:
```sql
SELECT 
    approval_id,
    decision_id,
    assigned_role,
    status,
    created_at
FROM approval_queue
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 10;
```
2. You should see pending approvals for high-risk purchase orders

**Check Agent Decisions**:
```sql
SELECT 
    decision_id,
    agent_name,
    decision_type,
    confidence_score,
    requires_approval,
    created_at
FROM agent_decision
ORDER BY created_at DESC
LIMIT 10;
```

✅ **Procurement Agent Working!**

### Step 10.3: Test Inventory Agent

**Manual Agent Invocation**:

1. Go to Bedrock console → Agents
2. Click on "supply-chain-inventory-agent"
3. Click "Test"
4. Enter:
   ```
   Analyze inventory across all warehouses and recommend transfers
   ```
5. Click "Run"
6. Verify agent analyzes inventory distribution

**Check Transfer Recommendations**:
```sql
SELECT 
    decision_id,
    decision_type,
    decision_data,
    confidence_score,
    created_at
FROM agent_decision
WHERE decision_type = 'TRANSFER_INVENTORY'
ORDER BY created_at DESC
LIMIT 10;
```

✅ **Inventory Agent Working!**

### Step 10.4: Test Dashboard Approval Workflow

**Access Dashboard**:
1. Open Streamlit dashboard (from Phase 9)
2. Select "Procurement Manager" role

**View Pending Approvals**:
1. Scroll to "Pending Approvals" section
2. You should see decisions from procurement agent
3. Each approval should show:
   - Decision ID
   - Confidence score
   - PO value
   - AI-generated rationale
   - Key factors

**Approve a Decision**:
1. Click "Approve" button on one decision
2. Verify success message appears
3. Decision should disappear from pending list

**Verify in Database**:
```sql
SELECT 
    approval_id,
    decision_id,
    status,
    approved_by,
    approved_at
FROM approval_queue
WHERE status = 'approved'
ORDER BY approved_at DESC
LIMIT 5;
```

**Check Audit Log**:
```sql
SELECT 
    event_id,
    timestamp,
    agent_name,
    user_name,
    action_type,
    rationale
FROM audit_log
ORDER BY timestamp DESC
LIMIT 10;
```

✅ **Dashboard Approval Workflow Working!**

### Step 10.5: Test EventBridge Schedules

**Option A: Wait for Scheduled Time**:
1. Wait until 1:00 AM UTC next day
2. Check CloudWatch Logs for agent execution
3. Verify forecasts generated

**Option B: Manually Trigger** (Recommended for testing):

1. Go to EventBridge console → Rules
2. Click on "supply-chain-forecasting-daily"
3. Click "Actions" dropdown
4. Select "Disable" (to prevent automatic execution)
5. Go to Bedrock console and manually invoke agent
6. Re-enable rule after testing

**Verify Scheduled Execution**:

1. Go to CloudWatch console
2. Click "Log groups" in left sidebar
3. Find log group: `/aws/bedrock/agents/supply-chain-forecasting-agent`
4. Click on log group
5. View recent log streams
6. Verify agent executed successfully

✅ **EventBridge Schedules Working!**

### Step 10.6: End-to-End Workflow Test

**Complete Workflow**:

1. **Forecasting Agent runs** (1:00 AM UTC)
   - Generates forecasts for all SKUs
   - Stores in demand_forecast table
   - Calculates accuracy metrics

2. **Procurement Agent runs** (2:00 AM UTC)
   - Reads forecasts
   - Checks inventory levels
   - Creates purchase orders
   - Routes high-risk to approval queue

3. **Inventory Agent runs** (3:00 AM UTC)
   - Reads forecasts
   - Analyzes inventory distribution
   - Recommends transfers
   - Routes high-risk to approval queue

4. **Manager reviews approvals** (during business hours)
   - Opens Streamlit dashboard
   - Reviews pending approvals
   - Approves or rejects decisions
   - System executes approved actions

5. **Audit trail maintained**
   - All decisions logged
   - All approvals logged
   - Complete transparency

**Verify Complete Workflow**:

Run this comprehensive query:
```sql
-- Summary of all agent activity
SELECT 
    'Forecasts Generated' as metric,
    COUNT(*) as count
FROM demand_forecast
WHERE forecast_date = CURRENT_DATE

UNION ALL

SELECT 
    'Purchase Orders Created',
    COUNT(*)
FROM purchase_order_header
WHERE order_date = CURRENT_DATE

UNION ALL

SELECT 
    'Pending Approvals',
    COUNT(*)
FROM approval_queue
WHERE status = 'pending'

UNION ALL

SELECT 
    'Audit Log Entries',
    COUNT(*)
FROM audit_log
WHERE DATE(timestamp) = CURRENT_DATE;
```

✅ **End-to-End Workflow Verified!**

---

## Verification Checklist

Use this checklist to verify your deployment:

### Infrastructure
- [ ] AWS Region set to us-east-1
- [ ] 5 IAM roles created
- [ ] Redshift Serverless workgroup "Available"
- [ ] S3 bucket created with folders
- [ ] Synthetic data uploaded to S3

### Data Layer
- [ ] Database schema loaded (13 tables)
- [ ] Glue ETL job created
- [ ] Glue job executed successfully
- [ ] Data loaded into Redshift tables

### Lambda Functions
- [ ] 13 Lambda functions created
- [ ] All functions use SupplyChainToolRole
- [ ] Environment variables configured
- [ ] Timeout set to 15 minutes
- [ ] Memory set to 512 MB

### Bedrock Agents
- [ ] 3 Bedrock Agents created
- [ ] All agents use Claude 3.5 Sonnet v2
- [ ] Action groups configured
- [ ] Lambda functions connected
- [ ] PROD aliases created
- [ ] Agent IDs saved

### Automation
- [ ] 3 EventBridge rules created
- [ ] Rules enabled
- [ ] Schedules configured (1 AM, 2 AM, 3 AM UTC)
- [ ] EventBridgeBedrockAgentRole assigned

### Dashboard
- [ ] SageMaker notebook instance created
- [ ] Streamlit app uploaded
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Streamlit running on port 8501
- [ ] Dashboard accessible

### Testing
- [ ] Forecasting agent tested manually
- [ ] Procurement agent tested manually
- [ ] Inventory agent tested manually
- [ ] Forecasts visible in database
- [ ] Purchase orders created
- [ ] Approval queue populated
- [ ] Dashboard displays data
- [ ] Approval workflow tested
- [ ] Audit log populated

---

## Troubleshooting Common Issues

### Issue 1: "Access Denied" Errors

**Symptom**: Lambda functions or agents can't access resources

**Solution**:
1. Verify IAM roles have correct policies
2. Check trust relationships are configured
3. Ensure resource ARNs include correct account ID
4. Wait 1-2 minutes for IAM changes to propagate

### Issue 2: Bedrock Agent Not Calling Tools

**Symptom**: Agent responds but doesn't invoke Lambda functions

**Solution**:
1. Verify Lambda functions have resource-based policy allowing Bedrock
2. Check OpenAPI schema matches function signatures
3. Ensure action group is properly configured
4. Test Lambda functions independently first

**Add Resource Policy to Lambda**:
1. Go to Lambda console
2. Click on function
3. Click "Configuration" → "Permissions"
4. Scroll to "Resource-based policy statements"
5. Click "Add permissions"
6. **Service**: Bedrock
7. **Source ARN**: Your agent ARN
8. **Action**: lambda:InvokeFunction
9. Click "Save"

### Issue 3: Redshift Connection Timeout

**Symptom**: Lambda functions timeout when querying Redshift

**Solution**:
1. Verify Redshift workgroup is "Available"
2. Check Lambda has SupplyChainToolRole
3. Ensure Redshift Data API permissions in role
4. Increase Lambda timeout to 15 minutes
5. Check CloudWatch logs for specific errors

### Issue 4: Streamlit Not Accessible

**Symptom**: Can't access dashboard on port 8501

**Solution**:
1. Verify SageMaker instance is "InService"
2. Check Streamlit process is running: `ps aux | grep streamlit`
3. Restart Streamlit if needed:
   ```bash
   pkill streamlit
   nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
   ```
4. Try accessing via `/proxy/8501/` URL path
5. Check nohup.out for errors: `tail -f nohup.out`

### Issue 5: No Data in Dashboard

**Symptom**: Dashboard loads but shows "No data"

**Solution**:
1. Verify agents have run at least once
2. Check data exists in Redshift tables
3. Verify dashboard environment variables are correct
4. Check CloudWatch logs for dashboard errors
5. Manually invoke agents to generate data

### Issue 6: EventBridge Not Triggering

**Symptom**: Agents don't run on schedule

**Solution**:
1. Verify rules are "Enabled"
2. Check cron expression is correct
3. Verify EventBridgeBedrockAgentRole has permissions
4. Check CloudWatch Logs for execution attempts
5. Manually test agent invocation first

---

## Cost Monitoring

### View Current Costs

**AWS Cost Explorer**:
1. In AWS Console, search for "Cost Explorer"
2. Click "AWS Cost Explorer"
3. Click "Launch Cost Explorer" (if first time)
4. View costs by service:
   - Bedrock
   - Lambda
   - Redshift
   - SageMaker
   - S3

**Set Up Billing Alerts**:
1. Go to AWS Billing console
2. Click "Budgets" in left sidebar
3. Click "Create budget"
4. **Budget type**: Cost budget
5. **Budget amount**: Enter your monthly limit (e.g., $2000)
6. **Alert threshold**: 80% of budget
7. **Email**: Your email address
8. Click "Create budget"

### Cost Optimization Tips

**Reduce Costs During Testing**:
1. **Stop SageMaker** when not in use:
   - SageMaker console → Notebook instances
   - Select instance → Actions → Stop
   - Saves ~$36/month

2. **Pause Redshift** when not in use:
   - Redshift console → Workgroups
   - Select workgroup → Actions → Pause
   - Saves ~$50-100/month

3. **Disable EventBridge rules** during testing:
   - EventBridge console → Rules
   - Select rule → Disable
   - Prevents unnecessary agent invocations

4. **Set CloudWatch log retention**:
   - CloudWatch console → Log groups
   - Select log group → Actions → Edit retention
   - Set to 7 days for non-critical logs

---

## Next Steps

### Production Readiness

Before going to production:

1. **Security Hardening**:
   - Move Redshift to private subnet
   - Remove public access
   - Enable VPC endpoints
   - Implement MFA for approvals
   - Enable encryption at rest

2. **Monitoring Setup**:
   - Create CloudWatch dashboards
   - Configure alarms for failures
   - Set up SNS notifications
   - Implement PagerDuty integration

3. **Testing**:
   - Run all 45 property-based tests
   - Conduct load testing
   - Test disaster recovery
   - Validate backup/restore

4. **Documentation**:
   - Create runbooks for operations
   - Document troubleshooting procedures
   - Create user guides
   - Train end users

5. **Governance**:
   - Establish approval SLAs
   - Define escalation procedures
   - Set up regular reviews
   - Create change management process

### Scaling Considerations

When scaling beyond MVP:

1. **Increase Redshift capacity**: 32 → 64+ RPUs
2. **Add Lambda concurrency**: Reserved concurrency for predictable performance
3. **Multi-region deployment**: For disaster recovery
4. **Caching layer**: Add ElastiCache for frequently accessed data
5. **CDN**: Add CloudFront for dashboard assets

---

## Support and Resources

### AWS Documentation

- [Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Redshift Serverless Guide](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless.html)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/)
- [EventBridge User Guide](https://docs.aws.amazon.com/eventbridge/latest/userguide/)

### Project Documentation

- **Requirements**: See `documents/1_REQUIREMENTS.md`
- **Design**: See `documents/2_DESIGN.md`
- **Tasks**: See `documents/3_TASKS.md`
- **Processes**: See `documents/4_END_TO_END_PROCESS.md`
- **CLI Deployment**: See `documents/5_DEPLOYMENT_GUIDE.md`
- **Setup Guide**: See `documents/6_SETUP_GUIDE.md`
- **Leadership Presentation**: See `documents/7_LEADERSHIP_PRESENTATION.md`

### Getting Help

- **AWS Support**: Use AWS Support Center
- **Technical Issues**: Create GitHub issue
- **Questions**: Contact project team

---

## Congratulations! 🎉

You've successfully deployed the Supply Chain AI Platform using AWS Console!

Your platform now includes:
- ✅ 3 autonomous AI agents
- ✅ 13 Lambda tools
- ✅ Redshift Serverless data warehouse
- ✅ Automated ETL pipeline
- ✅ Streamlit dashboard
- ✅ Daily automated schedules
- ✅ Complete audit trail

**Next**: Test the system thoroughly, then proceed with production hardening.

---

**Document End**
