# Phase 6: Lambda Functions Deployment - CORRECTED GUIDE

**Target Audience**: Users following Document 8 (AWS GUI Deployment Guide)  
**Prerequisite**: Phases 1-5 completed (IAM, Redshift, S3, Glue)

---

## Overview

We need to create **13 Lambda functions** for the three Bedrock Agents. The Lambda functions are individual Python files (not directories), so we'll package each one separately.

### Lambda Functions List

**Forecasting Agent (4 functions)**:
1. `get_historical_sales.py`
2. `calculate_forecast.py`
3. `store_forecast.py`
4. `calculate_accuracy.py`

**Procurement Agent (5 functions)**:
5. `get_inventory_levels.py`
6. `get_demand_forecast.py`
7. `get_supplier_data.py`
8. `calculate_eoq.py`
9. `create_purchase_order.py`

**Inventory Agent (1 function)**:
10. `lambda_function.py` (main inventory agent)

**Metrics Calculator (1 function)**:
11. `lambda_function.py` (metrics calculator)

**Additional (2 functions - if needed)**:
12-13. Additional inventory tools (if you create them)

---

## Step 6.1: Prepare Lambda Deployment Packages

### Understanding the Structure

Your Lambda functions are **individual Python files**, not directories. Each file needs to be packaged with its dependencies into a `.zip` file.

### Option A: Manual Packaging (Recommended for Beginners)

#### For Forecasting Agent Tools

**Step 1: Create a temporary packaging directory**

```bash
# On Windows (PowerShell)
cd C:\0_Personal\Bagya\zz_Learning\AWS_GPL_Supply_Chain\AWS_SC_Phase_2

# Create packaging directory
mkdir lambda_packages
cd lambda_packages
```

**Step 2: Package get_historical_sales**

```bash
# Create directory for this function
mkdir get_historical_sales
cd get_historical_sales

# Copy the Python file
copy ..\..\lambda\forecasting_agent\tools\get_historical_sales.py .

# Install dependencies
pip install boto3 pandas -t .

# Create zip file
# On Windows, use PowerShell:
Compress-Archive -Path * -DestinationPath ..\get_historical_sales.zip

cd ..
```

**Step 3: Repeat for other forecasting tools**

```bash
# calculate_forecast
mkdir calculate_forecast
cd calculate_forecast
copy ..\..\lambda\forecasting_agent\tools\calculate_forecast.py .
pip install boto3 pandas numpy statsmodels -t .
Compress-Archive -Path * -DestinationPath ..\calculate_forecast.zip
cd ..

# store_forecast
mkdir store_forecast
cd store_forecast
copy ..\..\lambda\forecasting_agent\tools\store_forecast.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\store_forecast.zip
cd ..

# calculate_accuracy
mkdir calculate_accuracy
cd calculate_accuracy
copy ..\..\lambda\forecasting_agent\tools\calculate_accuracy.py .
pip install boto3 pandas numpy -t .
Compress-Archive -Path * -DestinationPath ..\calculate_accuracy.zip
cd ..
```

#### For Procurement Agent Tools

```bash
# get_inventory_levels
mkdir get_inventory_levels
cd get_inventory_levels
copy ..\..\lambda\procurement_agent\tools\get_inventory_levels.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\get_inventory_levels.zip
cd ..

# get_demand_forecast
mkdir get_demand_forecast
cd get_demand_forecast
copy ..\..\lambda\procurement_agent\tools\get_demand_forecast.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\get_demand_forecast.zip
cd ..

# get_supplier_data
mkdir get_supplier_data
cd get_supplier_data
copy ..\..\lambda\procurement_agent\tools\get_supplier_data.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\get_supplier_data.zip
cd ..

# calculate_eoq
mkdir calculate_eoq
cd calculate_eoq
copy ..\..\lambda\procurement_agent\tools\calculate_eoq.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\calculate_eoq.zip
cd ..

# create_purchase_order
mkdir create_purchase_order
cd create_purchase_order
copy ..\..\lambda\procurement_agent\tools\create_purchase_order.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\create_purchase_order.zip
cd ..
```

#### For Inventory Agent

```bash
# inventory agent main function
mkdir inventory_agent
cd inventory_agent
copy ..\..\lambda\inventory_agent\lambda_function.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\inventory_agent.zip
cd ..
```

#### For Metrics Calculator

```bash
# metrics calculator
mkdir metrics_calculator
cd metrics_calculator
copy ..\..\lambda\metrics_calculator\lambda_function.py .
pip install boto3 -t .
Compress-Archive -Path * -DestinationPath ..\metrics_calculator.zip
cd ..
```

### Option B: Using Python Script (Automated)

Create a file called `package_lambdas.py` in your project root:

```python
import os
import shutil
import subprocess
import zipfile

# Define Lambda functions to package
LAMBDA_FUNCTIONS = {
    'forecasting': [
        ('lambda/forecasting_agent/tools/get_historical_sales.py', ['boto3', 'pandas']),
        ('lambda/forecasting_agent/tools/calculate_forecast.py', ['boto3', 'pandas', 'numpy', 'statsmodels']),
        ('lambda/forecasting_agent/tools/store_forecast.py', ['boto3']),
        ('lambda/forecasting_agent/tools/calculate_accuracy.py', ['boto3', 'pandas', 'numpy']),
    ],
    'procurement': [
        ('lambda/procurement_agent/tools/get_inventory_levels.py', ['boto3']),
        ('lambda/procurement_agent/tools/get_demand_forecast.py', ['boto3']),
        ('lambda/procurement_agent/tools/get_supplier_data.py', ['boto3']),
        ('lambda/procurement_agent/tools/calculate_eoq.py', ['boto3']),
        ('lambda/procurement_agent/tools/create_purchase_order.py', ['boto3']),
    ],
    'inventory': [
        ('lambda/inventory_agent/lambda_function.py', ['boto3']),
    ],
    'metrics': [
        ('lambda/metrics_calculator/lambda_function.py', ['boto3']),
    ]
}

def package_lambda(source_file, dependencies, output_dir='lambda_packages'):
    """Package a Lambda function with its dependencies"""
    # Get function name from file
    function_name = os.path.splitext(os.path.basename(source_file))[0]
    
    # Create temp directory
    temp_dir = os.path.join(output_dir, 'temp', function_name)
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"Packaging {function_name}...")
    
    # Copy source file
    shutil.copy(source_file, temp_dir)
    
    # Install dependencies
    if dependencies:
        print(f"  Installing dependencies: {', '.join(dependencies)}")
        subprocess.run([
            'pip', 'install', *dependencies, '-t', temp_dir
        ], check=True)
    
    # Create zip file
    zip_path = os.path.join(output_dir, f'{function_name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
    
    print(f"  Created: {zip_path}")
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)

def main():
    # Create output directory
    output_dir = 'lambda_packages'
    os.makedirs(output_dir, exist_ok=True)
    
    # Package all functions
    for agent_type, functions in LAMBDA_FUNCTIONS.items():
        print(f"\n=== Packaging {agent_type} agent functions ===")
        for source_file, dependencies in functions:
            if os.path.exists(source_file):
                package_lambda(source_file, dependencies, output_dir)
            else:
                print(f"  WARNING: {source_file} not found, skipping")
    
    print(f"\n✅ All Lambda packages created in '{output_dir}' directory")
    print(f"\nNext step: Upload these .zip files to S3")

if __name__ == '__main__':
    main()
```

Run the script:

```bash
python package_lambdas.py
```

---

## Step 6.2: Upload Lambda Packages to S3

### Upload via AWS Console

1. Go to **S3 Console**
2. Navigate to your bucket: `supply-chain-data-193871648423`
3. Click on `lambda/` folder (create if doesn't exist)
4. Create subfolders:
   - `lambda/forecasting/`
   - `lambda/procurement/`
   - `lambda/inventory/`
   - `lambda/metrics/`

5. Upload zip files to appropriate folders:

**Forecasting folder**:
- `get_historical_sales.zip`
- `calculate_forecast.zip`
- `store_forecast.zip`
- `calculate_accuracy.zip`

**Procurement folder**:
- `get_inventory_levels.zip`
- `get_demand_forecast.zip`
- `get_supplier_data.zip`
- `calculate_eoq.zip`
- `create_purchase_order.zip`

**Inventory folder**:
- `inventory_agent.zip` (or `lambda_function.zip`)

**Metrics folder**:
- `metrics_calculator.zip` (or `lambda_function.zip`)

---

## Step 6.3: Create Lambda Functions in AWS Console

### Template for All Functions

For each Lambda function, follow these steps:

**Step 1: Navigate to Lambda**
1. Go to **AWS Lambda Console**
2. Click **"Create function"**

**Step 2: Configure Function**
1. **Function option**: "Author from scratch"
2. **Function name**: Use naming convention below
3. **Runtime**: Python 3.9
4. **Architecture**: x86_64
5. **Permissions**: 
   - Expand "Change default execution role"
   - Select "Use an existing role"
   - Choose **"SupplyChainToolRole"**
6. Click **"Create function"**

**Step 3: Upload Code**
1. In "Code source" section, click **"Upload from"** dropdown
2. Select **"Amazon S3 location"**
3. Enter S3 URI (see table below)
4. Click **"Save"**

**Step 4: Configure Environment Variables**
1. Click **"Configuration"** tab
2. Click **"Environment variables"**
3. Click **"Edit"** → **"Add environment variable"**
4. Add these variables:

| Key | Value |
|-----|-------|
| REDSHIFT_WORKGROUP | supply-chain-workgroup |
| REDSHIFT_DATABASE | supply_chain |
| AWS_REGION | us-east-1 |

5. Click **"Save"**

**Step 5: Configure Timeout and Memory**
1. Still in "Configuration" tab
2. Click **"General configuration"**
3. Click **"Edit"**
4. **Memory**: 512 MB
5. **Timeout**: 15 minutes (900 seconds)
6. Click **"Save"**

### Function Names and S3 URIs

| # | Function Name | S3 URI |
|---|---------------|--------|
| 1 | supply-chain-forecasting-get-historical-sales | s3://supply-chain-data-193871648423/lambda/forecasting/get_historical_sales.zip |
| 2 | supply-chain-forecasting-calculate-forecast | s3://supply-chain-data-193871648423/lambda/forecasting/calculate_forecast.zip |
| 3 | supply-chain-forecasting-store-forecast | s3://supply-chain-data-193871648423/lambda/forecasting/store_forecast.zip |
| 4 | supply-chain-forecasting-calculate-accuracy | s3://supply-chain-data-193871648423/lambda/forecasting/calculate_accuracy.zip |
| 5 | supply-chain-procurement-get-inventory-levels | s3://supply-chain-data-193871648423/lambda/procurement/get_inventory_levels.zip |
| 6 | supply-chain-procurement-get-demand-forecast | s3://supply-chain-data-193871648423/lambda/procurement/get_demand_forecast.zip |
| 7 | supply-chain-procurement-get-supplier-data | s3://supply-chain-data-193871648423/lambda/procurement/get_supplier_data.zip |
| 8 | supply-chain-procurement-calculate-eoq | s3://supply-chain-data-193871648423/lambda/procurement/calculate_eoq.zip |
| 9 | supply-chain-procurement-create-purchase-order | s3://supply-chain-data-193871648423/lambda/procurement/create_purchase_order.zip |
| 10 | supply-chain-inventory-agent | s3://supply-chain-data-193871648423/lambda/inventory/inventory_agent.zip |
| 11 | supply-chain-metrics-calculator | s3://supply-chain-data-193871648423/lambda/metrics/metrics_calculator.zip |

---

## Step 6.4: Test Lambda Functions

### Test One Function

Let's test `get_historical_sales`:

1. Go to Lambda Console
2. Click on `supply-chain-forecasting-get-historical-sales`
3. Click **"Test"** tab
4. Click **"Create new event"**
5. **Event name**: test-event
6. **Event JSON**:
```json
{
  "product_id": "PROD001",
  "months_back": 12
}
```
7. Click **"Save"**
8. Click **"Test"** button
9. Check **"Execution results"** section

**Expected Result**: Should return historical sales data or an error message (data might not exist yet until Glue job runs)

---

## Step 6.5: Verification Checklist

After creating all functions, verify:

- [ ] 11 Lambda functions created (minimum)
- [ ] All functions use **SupplyChainToolRole**
- [ ] All functions have **3 environment variables** set
- [ ] All functions have **512 MB memory**
- [ ] All functions have **15 minute timeout**
- [ ] All functions show **"Active"** status
- [ ] At least one function tested successfully

---

## Troubleshooting

### Issue: "Unable to import module"

**Cause**: Dependencies not included in zip file

**Solution**: 
1. Make sure you ran `pip install -t .` in the function directory
2. Verify the zip file contains both the .py file and dependency folders
3. Re-create the zip file

### Issue: "Task timed out after 3.00 seconds"

**Cause**: Default timeout is too short

**Solution**: Increase timeout to 15 minutes (900 seconds) in Configuration → General configuration

### Issue: "Access Denied" when accessing Redshift

**Cause**: IAM role doesn't have Redshift Data API permissions

**Solution**: Verify SupplyChainToolRole has the policy from Phase 2

---

## Next Steps

After completing Phase 6, proceed to:
- **Phase 7**: Create Bedrock Agents
- **Phase 8**: Configure EventBridge Schedules
- **Phase 9**: Deploy SageMaker Dashboard

---

**✅ Phase 6 Complete!** You now have all Lambda functions deployed and ready to be connected to Bedrock Agents.
