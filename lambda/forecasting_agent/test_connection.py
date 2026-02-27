"""
Test script to verify Redshift connection and Lambda function structure

This script tests the connection logic without deploying to AWS.
Run this locally to verify your Redshift credentials and connection.
"""

import os
import sys
import json

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from lambda_function import (
    connect_with_retry,
    get_all_products,
    validate_environment_variables
)


def test_environment_variables():
    """Test that environment variables are configured"""
    print("=" * 60)
    print("Testing Environment Variables")
    print("=" * 60)
    
    if validate_environment_variables():
        print("✓ All required environment variables are set")
        print(f"  - REDSHIFT_HOST: {os.environ.get('REDSHIFT_HOST', 'NOT SET')}")
        print(f"  - REDSHIFT_DATABASE: {os.environ.get('REDSHIFT_DATABASE', 'NOT SET')}")
        print(f"  - REDSHIFT_USER: {os.environ.get('REDSHIFT_USER', 'NOT SET')}")
        print(f"  - REDSHIFT_PASSWORD: {'*' * len(os.environ.get('REDSHIFT_PASSWORD', ''))}")
        return True
    else:
        print("✗ Missing required environment variables")
        return False


def test_connection():
    """Test Redshift connection with retry logic"""
    print("\n" + "=" * 60)
    print("Testing Redshift Connection")
    print("=" * 60)
    
    try:
        conn = connect_with_retry(max_retries=3)
        print("✓ Successfully connected to Redshift")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✓ Redshift version: {version[:50]}...")
        cursor.close()
        
        conn.close()
        print("✓ Connection closed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {str(e)}")
        return False


def test_get_products():
    """Test retrieving products from database"""
    print("\n" + "=" * 60)
    print("Testing Product Retrieval")
    print("=" * 60)
    
    try:
        conn = connect_with_retry(max_retries=3)
        products = get_all_products(conn)
        
        print(f"✓ Retrieved {len(products)} products from database")
        
        if len(products) > 0:
            print(f"✓ Sample product: {products[0]}")
        else:
            print("⚠ Warning: No products found in database")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Product retrieval failed: {str(e)}")
        return False


def test_lambda_handler():
    """Test the Lambda handler function"""
    print("\n" + "=" * 60)
    print("Testing Lambda Handler")
    print("=" * 60)
    
    try:
        from lambda_function import lambda_handler
        
        # Mock event and context
        event = {
            'source': 'aws.events',
            'detail-type': 'Scheduled Event'
        }
        
        class MockContext:
            function_name = 'forecasting-agent-test'
            memory_limit_in_mb = 512
            invoked_function_arn = 'arn:aws:lambda:eu-west-2:123456789012:function:forecasting-agent-test'
            aws_request_id = 'test-request-id'
        
        result = lambda_handler(event, MockContext())
        
        print(f"✓ Lambda handler executed")
        print(f"✓ Status code: {result['statusCode']}")
        
        body = json.loads(result['body'])
        print(f"✓ Result: {json.dumps(body, indent=2)}")
        
        return result['statusCode'] == 200
        
    except Exception as e:
        print(f"✗ Lambda handler failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Forecasting Agent Lambda - Connection Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Environment variables
    results.append(("Environment Variables", test_environment_variables()))
    
    if not results[0][1]:
        print("\n" + "=" * 60)
        print("FAILED: Cannot proceed without environment variables")
        print("=" * 60)
        print("\nPlease set the following environment variables:")
        print("  export REDSHIFT_HOST=your-cluster.redshift.amazonaws.com")
        print("  export REDSHIFT_DATABASE=supply_chain")
        print("  export REDSHIFT_USER=admin")
        print("  export REDSHIFT_PASSWORD=YourPassword")
        return 1
    
    # Test 2: Connection
    results.append(("Redshift Connection", test_connection()))
    
    if not results[1][1]:
        print("\n" + "=" * 60)
        print("FAILED: Cannot proceed without database connection")
        print("=" * 60)
        return 1
    
    # Test 3: Product retrieval
    results.append(("Product Retrieval", test_get_products()))
    
    # Test 4: Lambda handler
    results.append(("Lambda Handler", test_lambda_handler()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("SUCCESS: All tests passed!")
    else:
        print("FAILED: Some tests failed")
    print("=" * 60)
    print()
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
