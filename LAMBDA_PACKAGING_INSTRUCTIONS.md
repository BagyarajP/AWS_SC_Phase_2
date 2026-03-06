# Lambda Packaging Instructions - Quick Start

## Step 1: Run the Packaging Script

Open PowerShell or Command Prompt in your project directory:

```bash
cd C:\0_Personal\Bagya\zz_Learning\AWS_GPL_Supply_Chain\AWS_SC_Phase_2

python package_lambdas.py
```

**What it does:**
- Creates `lambda_packages/` directory
- Packages all 11 Lambda functions with dependencies
- Creates .zip files ready for AWS Lambda

**Expected output:**
```
Supply Chain AI Platform - Lambda Function Packager
====================================================================

📁 Output directory: lambda_packages

====================================================================
🤖 Packaging FORECASTING agent functions
====================================================================

📦 Packaging get_historical_sales...
   ✓ Copied source file
   ⏳ Installing dependencies: boto3, pandas
   ✓ Dependencies installed
   ✓ Created: lambda_packages\get_historical_sales.zip (15.23 MB)

... (continues for all functions)

====================================================================
📊 PACKAGING SUMMARY
====================================================================
Total functions: 11
✅ Successfully packaged: 11
❌ Failed: 0
⚠️  Skipped (not found): 0

✅ All Lambda packages created in 'lambda_packages' directory
```

## Step 2: Verify Packages Created

Check the `lambda_packages/` directory. You should see these .zip files:

**Forecasting (4 files):**
- ✅ get_historical_sales.zip
- ✅ calculate_forecast.zip
- ✅ store_forecast.zip
- ✅ calculate_accuracy.zip

**Procurement (5 files):**
- ✅ get_inventory_levels.zip
- ✅ get_demand_forecast.zip
- ✅ get_supplier_data.zip
- ✅ calculate_eoq.zip
- ✅ create_purchase_order.zip

**Inventory (1 file):**
- ✅ lambda_function.zip (inventory agent)

**Metrics (1 file):**
- ✅ lambda_function.zip (metrics calculator)

**Note**: You'll have two files named `lambda_function.zip`. Rename them:
- Rename one to `inventory_agent.zip`
- Rename the other to `metrics_calculator.zip`

## Step 3: Upload to S3

### Option A: AWS Console (GUI)

1. Go to **S3 Console**: https://s3.console.aws.amazon.com/
2. Click on bucket: `supply-chain-data-193871648423`
3. Create folder structure:
   - Click "Create folder" → Name: `lambda`
   - Inside `lambda/`, create: `forecasting`, `procurement`, `inventory`, `metrics`

4. Upload files to respective folders:

**Upload to `lambda/forecasting/`:**
- get_historical_sales.zip
- calculate_forecast.zip
- store_forecast.zip
- calculate_accuracy.zip

**Upload to `lambda/procurement/`:**
- get_inventory_levels.zip
- get_demand_forecast.zip
- get_supplier_data.zip
- calculate_eoq.zip
- create_purchase_order.zip

**Upload to `lambda/inventory/`:**
- inventory_agent.zip

**Upload to `lambda/metrics/`:**
- metrics_calculator.zip

### Option B: AWS CLI (Faster)

```bash
# Set your bucket name
$BUCKET = "supply-chain-data-193871648423"

# Upload forecasting functions
aws s3 cp lambda_packages/get_historical_sales.zip s3://$BUCKET/lambda/forecasting/
aws s3 cp lambda_packages/calculate_forecast.zip s3://$BUCKET/lambda/forecasting/
aws s3 cp lambda_packages/store_forecast.zip s3://$BUCKET/lambda/forecasting/
aws s3 cp lambda_packages/calculate_accuracy.zip s3://$BUCKET/lambda/forecasting/

# Upload procurement functions
aws s3 cp lambda_packages/get_inventory_levels.zip s3://$BUCKET/lambda/procurement/
aws s3 cp lambda_packages/get_demand_forecast.zip s3://$BUCKET/lambda/procurement/
aws s3 cp lambda_packages/get_supplier_data.zip s3://$BUCKET/lambda/procurement/
aws s3 cp lambda_packages/calculate_eoq.zip s3://$BUCKET/lambda/procurement/
aws s3 cp lambda_packages/create_purchase_order.zip s3://$BUCKET/lambda/procurement/

# Upload inventory function
aws s3 cp lambda_packages/inventory_agent.zip s3://$BUCKET/lambda/inventory/

# Upload metrics function
aws s3 cp lambda_packages/metrics_calculator.zip s3://$BUCKET/lambda/metrics/
```

## Step 4: Create Lambda Functions in AWS Console

For each function, follow these steps:

### Quick Template

1. **Go to Lambda Console**: https://console.aws.amazon.com/lambda/
2. Click **"Create function"**
3. **Configure**:
   - Function name: (see table below)
   - Runtime: Python 3.9
   - Architecture: x86_64
   - Execution role: Use existing → **SupplyChainToolRole**
4. Click **"Create function"**
5. **Upload code**:
   - Click "Upload from" → "Amazon S3 location"
   - Enter S3 URI (see table below)
   - Click "Save"
6. **Add environment variables**:
   - Configuration → Environment variables → Edit
   - Add:
     - `REDSHIFT_WORKGROUP` = `supply-chain-workgroup`
     - `REDSHIFT_DATABASE` = `supply_chain`
     - `AWS_REGION` = `us-east-1`
7. **Configure timeout**:
   - Configuration → General configuration → Edit
   - Memory: 512 MB
   - Timeout: 15 minutes (900 seconds)

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

## Step 5: Test One Function

Let's test the first function to make sure everything works:

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
9. Check results in "Execution results" section

**Expected**: Function executes (may return empty data if Glue hasn't run yet)

## Troubleshooting

### Issue: "No module named 'pandas'"

**Cause**: Dependencies not included in zip

**Solution**: 
1. Delete the .zip file
2. Run `python package_lambdas.py` again
3. Verify the .zip file is larger (should be 10-20 MB with dependencies)

### Issue: Script fails with "pip not found"

**Cause**: pip not in PATH

**Solution**:
```bash
python -m pip install --upgrade pip
```

### Issue: "Permission denied" when creating zip

**Cause**: File is open or locked

**Solution**:
1. Close any programs that might have the file open
2. Delete `lambda_packages/` folder
3. Run script again

## Verification Checklist

Before proceeding to Phase 7 (Bedrock Agents):

- [ ] Script ran successfully (11 functions packaged)
- [ ] All .zip files exist in `lambda_packages/` directory
- [ ] All .zip files uploaded to S3
- [ ] All 11 Lambda functions created in AWS Console
- [ ] All functions use **SupplyChainToolRole**
- [ ] All functions have **3 environment variables**
- [ ] All functions have **512 MB memory** and **15 min timeout**
- [ ] At least one function tested successfully

## Next Steps

After completing Lambda deployment:

1. **Proceed to Phase 7**: Create Bedrock Agents
2. **Refer to**: `documents/8_AWS_GUI_DEPLOYMENT_GUIDE.md` - Phase 7

---

**Need Help?**
- Check `documents/PHASE_6_LAMBDA_DEPLOYMENT_CORRECTED.md` for detailed instructions
- Review CloudWatch Logs if functions fail
- Verify IAM role permissions if you get "Access Denied" errors
