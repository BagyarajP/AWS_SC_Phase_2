"""
Verify that synthetic data has been loaded correctly into Redshift Serverless
"""

import boto3
import time

# Configuration
REGION = 'us-east-1'
WORKGROUP_NAME = 'supply-chain-workgroup'
DATABASE_NAME = 'supply_chain'

def execute_query(redshift_data, sql):
    """Execute a query and return results"""
    response = redshift_data.execute_statement(
        WorkgroupName=WORKGROUP_NAME,
        Database=DATABASE_NAME,
        Sql=sql
    )
    
    query_id = response['Id']
    
    # Wait for query to complete
    max_wait = 60
    waited = 0
    
    while waited < max_wait:
        status_response = redshift_data.describe_statement(Id=query_id)
        status = status_response['Status']
        
        if status == 'FINISHED':
            break
        elif status in ['FAILED', 'ABORTED']:
            error = status_response.get('Error', 'Query failed')
            raise Exception(f"Query failed: {error}")
        
        time.sleep(1)
        waited += 1
    
    if waited >= max_wait:
        raise Exception(f"Query timed out after {max_wait} seconds")
    
    # Get results
    result = redshift_data.get_statement_result(Id=query_id)
    return result

def verify_data():
    """Verify data in Redshift"""
    
    print("=" * 60)
    print("Data Verification")
    print("=" * 60)
    print()
    
    redshift_data = boto3.client('redshift-data', region_name=REGION)
    
    # Test 1: Check row counts
    print("Test 1: Checking row counts...")
    print()
    
    tables = [
        ('product', 2000),
        ('warehouse', 3),
        ('supplier', 500),
        ('inventory', 6000),
        ('purchase_order_header', 100),
        ('sales_order_header', 10000)  # Approximate
    ]
    
    all_passed = True
    
    for table_name, expected_min in tables:
        try:
            result = execute_query(
                redshift_data,
                f"SELECT COUNT(*) FROM {table_name}"
            )
            
            count = result['Records'][0][0].get('longValue', 0)
            
            if count >= expected_min:
                print(f"  ✓ {table_name}: {count:,} rows (expected >= {expected_min:,})")
            else:
                print(f"  ✗ {table_name}: {count:,} rows (expected >= {expected_min:,})")
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ {table_name}: Error - {e}")
            all_passed = False
    
    # Test 2: Check for products below reorder point
    print()
    print("Test 2: Checking for products below reorder point...")
    
    try:
        result = execute_query(
            redshift_data,
            """
            SELECT COUNT(*) 
            FROM product p
            JOIN inventory i ON p.product_id = i.product_id
            WHERE i.quantity_on_hand < p.reorder_point
            """
        )
        
        count = result['Records'][0][0].get('longValue', 0)
        print(f"  ✓ Found {count:,} inventory items below reorder point")
        
        if count == 0:
            print("  ⚠ Warning: No items below reorder point (procurement agent won't have work)")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        all_passed = False
    
    # Test 3: Check sales order seasonality
    print()
    print("Test 3: Checking sales order seasonality...")
    
    try:
        result = execute_query(
            redshift_data,
            """
            SELECT 
                EXTRACT(MONTH FROM order_date) as month,
                COUNT(*) as order_count
            FROM sales_order_header
            GROUP BY month
            ORDER BY month
            """
        )
        
        print("  Month | Order Count")
        print("  ------|------------")
        
        winter_months = []
        other_months = []
        
        for record in result['Records']:
            month = record[0].get('longValue', 0)
            count = record[1].get('longValue', 0)
            print(f"  {month:5} | {count:,}")
            
            if month in [11, 12, 1, 2]:
                winter_months.append(count)
            else:
                other_months.append(count)
        
        if winter_months and other_months:
            avg_winter = sum(winter_months) / len(winter_months)
            avg_other = sum(other_months) / len(other_months)
            
            if avg_winter > avg_other * 1.2:
                print(f"  ✓ Seasonality detected (winter avg: {avg_winter:.0f}, other avg: {avg_other:.0f})")
            else:
                print(f"  ⚠ Weak seasonality (winter avg: {avg_winter:.0f}, other avg: {avg_other:.0f})")
                
    except Exception as e:
        print(f"  ✗ Error: {e}")
        all_passed = False
    
    # Test 4: Check data relationships
    print()
    print("Test 4: Checking data relationships...")
    
    relationship_tests = [
        ("Inventory → Product", "SELECT COUNT(*) FROM inventory i LEFT JOIN product p ON i.product_id = p.product_id WHERE p.product_id IS NULL"),
        ("Inventory → Warehouse", "SELECT COUNT(*) FROM inventory i LEFT JOIN warehouse w ON i.warehouse_id = w.warehouse_id WHERE w.warehouse_id IS NULL"),
        ("PO Header → Supplier", "SELECT COUNT(*) FROM purchase_order_header po LEFT JOIN supplier s ON po.supplier_id = s.supplier_id WHERE s.supplier_id IS NULL"),
        ("PO Line → PO Header", "SELECT COUNT(*) FROM purchase_order_line pol LEFT JOIN purchase_order_header po ON pol.po_id = po.po_id WHERE po.po_id IS NULL"),
        ("SO Line → SO Header", "SELECT COUNT(*) FROM sales_order_line sol LEFT JOIN sales_order_header so ON sol.so_id = so.so_id WHERE so.so_id IS NULL"),
    ]
    
    for test_name, query in relationship_tests:
        try:
            result = execute_query(redshift_data, query)
            orphans = result['Records'][0][0].get('longValue', 0)
            
            if orphans == 0:
                print(f"  ✓ {test_name}: No orphaned records")
            else:
                print(f"  ✗ {test_name}: {orphans} orphaned records found")
                all_passed = False
                
        except Exception as e:
            print(f"  ✗ {test_name}: Error - {e}")
            all_passed = False
    
    # Test 5: Check supplier performance metrics
    print()
    print("Test 5: Checking supplier performance metrics...")
    
    try:
        result = execute_query(
            redshift_data,
            """
            SELECT 
                AVG(reliability_score) as avg_reliability,
                AVG(avg_lead_time_days) as avg_lead_time,
                AVG(defect_rate) as avg_defect_rate
            FROM supplier
            """
        )
        
        record = result['Records'][0]
        avg_reliability = float(record[0].get('stringValue', '0'))
        avg_lead_time = float(record[1].get('stringValue', '0'))
        avg_defect_rate = float(record[2].get('stringValue', '0'))
        
        print(f"  Average reliability score: {avg_reliability:.2f}")
        print(f"  Average lead time: {avg_lead_time:.1f} days")
        print(f"  Average defect rate: {avg_defect_rate:.4f}")
        
        if 0.7 <= avg_reliability <= 0.99:
            print("  ✓ Supplier metrics look realistic")
        else:
            print("  ⚠ Supplier metrics may be out of expected range")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        all_passed = False
    
    # Summary
    print()
    print("=" * 60)
    if all_passed:
        print("All verification tests passed! ✓")
    else:
        print("Some verification tests failed. ✗")
    print("=" * 60)
    print()
    
    if all_passed:
        print("Data is loaded correctly and ready for use.")
        print()
        print("Next steps:")
        print("  1. Proceed to Task 2: Implement AWS Glue ETL job")
        print("  2. Start building Bedrock Agents (Tasks 4-6)")
    else:
        print("Please review the errors above and reload data if necessary.")
    
    return all_passed

if __name__ == '__main__':
    success = verify_data()
    exit(0 if success else 1)
