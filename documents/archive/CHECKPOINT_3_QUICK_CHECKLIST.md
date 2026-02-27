# Checkpoint 3: Quick Verification Checklist

## Pre-Flight Checklist

- [ ] AWS CLI installed and configured
- [ ] Python 3.9+ installed
- [ ] Synthetic data generated (Task 1)
- [ ] Glue ETL code implemented (Task 2)

## Infrastructure Setup Checklist

### S3 Setup
- [ ] Created S3 bucket: `supply-chain-data-bucket`
- [ ] Created S3 bucket: `supply-chain-glue-scripts`
- [ ] Uploaded 8 CSV files to `s3://supply-chain-data-bucket/synthetic_data/`
  - [ ] product.csv
  - [ ] warehouse.csv
  - [ ] supplier.csv
  - [ ] inventory.csv
  - [ ] purchase_order_header.csv
  - [ ] purchase_order_line.csv
  - [ ] sales_order_header.csv
  - [ ] sales_order_line.csv

### Redshift Setup
- [ ] Created Redshift cluster: `supply-chain-cluster`
  - [ ] Node type: dc2.large
  - [ ] Database: supply_chain
  - [ ] Region: eu-west-2
  - [ ] Publicly accessible: Yes (for MVP)
- [ ] Cluster status: Available
- [ ] Executed schema.sql (13 tables created)
- [ ] Verified tables exist in database

### IAM Setup
- [ ] Created IAM policy: `SupplyChainGluePolicy`
- [ ] Created IAM role: `SupplyChainGlueRole`
- [ ] Attached AWS managed policy: `AWSGlueServiceRole`
- [ ] Attached custom policy to role

### Glue Setup
- [ ] Created Glue connection: `supply-chain-redshift`
- [ ] Tested connection successfully
- [ ] Uploaded etl_job.py to S3
- [ ] Created Glue job: `supply-chain-etl-job`
- [ ] Configured job parameters correctly

## Glue Job Execution Checklist

- [ ] Started Glue job run
- [ ] Job status: SUCCEEDED
- [ ] Execution time: < 60 minutes
- [ ] No critical errors in CloudWatch logs

## Data Verification Checklist

### Record Counts
- [ ] product: 2,000 records
- [ ] warehouse: 3 records
- [ ] supplier: 500 records
- [ ] inventory: ~4,200 records
- [ ] purchase_order_header: ~1,000-1,500 records
- [ ] purchase_order_line: ~2,000-3,000 records
- [ ] sales_order_header: ~4,000-5,000 records
- [ ] sales_order_line: ~15,000-20,000 records

### Data Quality
- [ ] No NULL primary keys
- [ ] No orphaned records (referential integrity)
- [ ] Product SKUs are unique
- [ ] Warehouse data matches expected (3 warehouses)
- [ ] Supplier reliability scores: 0.70-0.99
- [ ] Sales orders span ~12 months
- [ ] Inventory distributed across 3 warehouses

### CloudWatch Metrics
- [ ] TablesProcessed: 8
- [ ] SuccessRate: >95%
- [ ] ErrorCount: 0 or minimal
- [ ] RecordsWritten matches expected totals

## Quick Verification Commands

### Check S3 Files
```bash
aws s3 ls s3://supply-chain-data-bucket/synthetic_data/
```

### Check Redshift Cluster Status
```bash
aws redshift describe-clusters \
  --cluster-identifier supply-chain-cluster \
  --query 'Clusters[0].ClusterStatus' \
  --output text
```

### Check Glue Job Status
```bash
aws glue get-job --job-name supply-chain-etl-job
```

### Start Glue Job
```bash
aws glue start-job-run --job-name supply-chain-etl-job
```

### Check Job Run Status
```bash
aws glue get-job-runs \
  --job-name supply-chain-etl-job \
  --max-results 1 \
  --query 'JobRuns[0].JobRunState' \
  --output text
```

## Quick Verification SQL

### Count All Tables
```sql
SELECT 'product' as table_name, COUNT(*) as count FROM product
UNION ALL SELECT 'warehouse', COUNT(*) FROM warehouse
UNION ALL SELECT 'supplier', COUNT(*) FROM supplier
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'purchase_order_header', COUNT(*) FROM purchase_order_header
UNION ALL SELECT 'purchase_order_line', COUNT(*) FROM purchase_order_line
UNION ALL SELECT 'sales_order_header', COUNT(*) FROM sales_order_header
UNION ALL SELECT 'sales_order_line', COUNT(*) FROM sales_order_line;
```

### Check for NULL Primary Keys (should return 0)
```sql
SELECT COUNT(*) FROM product WHERE product_id IS NULL
UNION ALL SELECT COUNT(*) FROM warehouse WHERE warehouse_id IS NULL
UNION ALL SELECT COUNT(*) FROM supplier WHERE supplier_id IS NULL
UNION ALL SELECT COUNT(*) FROM inventory WHERE inventory_id IS NULL;
```

### Check Referential Integrity (should return 0)
```sql
SELECT COUNT(*) FROM inventory i
LEFT JOIN product p ON i.product_id = p.product_id
WHERE p.product_id IS NULL;
```

## Success Criteria

✅ **Checkpoint 3 PASSES if:**
1. All infrastructure setup items checked
2. Glue job completed successfully
3. All 8 tables populated with expected record counts
4. All data quality checks pass
5. CloudWatch metrics show >95% success rate

❌ **Checkpoint 3 FAILS if:**
1. Glue job status: FAILED
2. Any table has 0 records
3. Record counts significantly below expected ranges
4. Referential integrity violations found
5. Success rate <95%

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Glue job timeout | Check Redshift security group (port 5439) |
| Access Denied on S3 | Verify IAM role permissions |
| Connection timeout | Test Glue connection in Console |
| Missing tables | Re-run schema.sql |
| Low record counts | Check source CSV files in S3 |
| NULL primary keys | Review data transformation logic |

## Next Steps After Checkpoint

1. ✅ Mark Task 3 complete in tasks.md
2. 📸 Take screenshots of verification results
3. 📝 Document any issues and resolutions
4. ➡️ Proceed to Task 4: Forecasting Agent Lambda

## Time Estimates

- Infrastructure setup: 30-45 minutes
- Glue job execution: 10-20 minutes
- Data verification: 10-15 minutes
- **Total: ~1-1.5 hours**

## Support Resources

- Full guide: `CHECKPOINT_3_VERIFICATION_GUIDE.md`
- Setup guide: `SETUP_GUIDE.md`
- Glue documentation: `glue/README.md`
- Database schema: `database/schema.sql`
- Design document: `.kiro/specs/supply-chain-ai-platform/design.md`
