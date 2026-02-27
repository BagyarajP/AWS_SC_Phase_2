"""
Test Redshift Data API connectivity
This script verifies that the Redshift Serverless workgroup is accessible via the Data API
"""

import boto3
import time
import json

# Configuration
REGION = 'us-east-1'
WORKGROUP_NAME = 'supply-chain-workgroup'
DATABASE_NAME = 'supply_chain'

def test_redshift_connection():
    """Test Redshift Data API connectivity"""
    
    print("=" * 60)
    print("Redshift Data API Connection Test")
    print("=" * 60)
    print()
    print(f"Region: {REGION}")
    print(f"Workgroup: {WORKGROUP_NAME}")
    print(f"Database: {DATABASE_NAME}")
    print()
    
    # Initialize Redshift Data API client
    try:
        redshift_data = boto3.client('redshift-data', region_name=REGION)
        print("✓ Redshift Data API client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize client: {e}")
        return False
    
    # Test 1: Execute a simple query
    print()
    print("Test 1: Executing simple query (SELECT 1)...")
    
    try:
        response = redshift_data.execute_statement(
            WorkgroupName=WORKGROUP_NAME,
            Database=DATABASE_NAME,
            Sql='SELECT 1 as test_value'
        )
        
        query_id = response['Id']
        print(f"✓ Query submitted (ID: {query_id})")
        
        # Wait for query to complete
        print("  Waiting for query to complete...", end=' ')
        max_wait = 30  # seconds
        waited = 0
        
        while waited < max_wait:
            status_response = redshift_data.describe_statement(Id=query_id)
            status = status_response['Status']
            
            if status == 'FINISHED':
                print("✓")
                break
            elif status == 'FAILED':
                error = status_response.get('Error', 'Unknown error')
                print(f"✗ Query failed: {error}")
                return False
            elif status == 'ABORTED':
                print("✗ Query aborted")
                return False
            
            time.sleep(1)
            waited += 1
        
        if waited >= max_wait:
            print(f"✗ Query timed out after {max_wait} seconds")
            return False
        
        # Get results
        result = redshift_data.get_statement_result(Id=query_id)
        records = result.get('Records', [])
        
        if records and len(records) > 0:
            test_value = records[0][0].get('longValue', None)
            if test_value == 1:
                print(f"✓ Query result verified: {test_value}")
            else:
                print(f"✗ Unexpected result: {test_value}")
                return False
        else:
            print("✗ No results returned")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Test 2: List tables
    print()
    print("Test 2: Listing tables in database...")
    
    try:
        response = redshift_data.execute_statement(
            WorkgroupName=WORKGROUP_NAME,
            Database=DATABASE_NAME,
            Sql="""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """
        )
        
        query_id = response['Id']
        
        # Wait for query to complete
        max_wait = 30
        waited = 0
        
        while waited < max_wait:
            status_response = redshift_data.describe_statement(Id=query_id)
            status = status_response['Status']
            
            if status == 'FINISHED':
                break
            elif status in ['FAILED', 'ABORTED']:
                error = status_response.get('Error', 'Query failed')
                print(f"✗ {error}")
                return False
            
            time.sleep(1)
            waited += 1
        
        # Get results
        result = redshift_data.get_statement_result(Id=query_id)
        records = result.get('Records', [])
        
        if records:
            print(f"✓ Found {len(records)} tables:")
            for record in records:
                table_name = record[0].get('stringValue', 'unknown')
                print(f"    - {table_name}")
        else:
            print("  No tables found (this is expected if schema hasn't been created yet)")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Test 3: Check workgroup status
    print()
    print("Test 3: Checking workgroup status...")
    
    try:
        redshift_serverless = boto3.client('redshift-serverless', region_name=REGION)
        response = redshift_serverless.get_workgroup(workgroupName=WORKGROUP_NAME)
        
        workgroup = response['workgroup']
        status = workgroup['status']
        base_capacity = workgroup['baseCapacity']
        
        print(f"✓ Workgroup status: {status}")
        print(f"✓ Base capacity: {base_capacity} RPUs")
        
        if status != 'AVAILABLE':
            print(f"  Warning: Workgroup is not in AVAILABLE state")
            
    except Exception as e:
        print(f"✗ Error checking workgroup: {e}")
        return False
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print()
    print("Redshift Data API is working correctly.")
    print()
    print("Next steps:")
    print("  1. Run schema.sql to create tables if not already done")
    print("  2. Load synthetic data using AWS Glue or COPY commands")
    print("  3. Verify data with: python scripts/verify_data.py")
    
    return True

if __name__ == '__main__':
    success = test_redshift_connection()
    exit(0 if success else 1)
