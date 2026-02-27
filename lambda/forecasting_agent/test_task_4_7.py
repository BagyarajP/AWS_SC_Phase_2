"""
Test for Task 4.7: Store forecasts in Redshift and calculate accuracy

This test verifies:
1. Forecasts are stored in demand_forecast table
2. MAPE is calculated for previous forecasts
3. Accuracy metrics are stored in forecast_accuracy table

Note: These are integration tests that require a Redshift database connection.
Set environment variables before running:
  export REDSHIFT_HOST=your-cluster.redshift.amazonaws.com
  export REDSHIFT_DATABASE=supply_chain
  export REDSHIFT_USER=admin
  export REDSHIFT_PASSWORD=YourPassword
"""

import pytest
import psycopg2
import os
import sys
from datetime import datetime, timedelta
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import (
    store_forecast,
    calculate_forecast_accuracy,
    connect_with_retry
)


@pytest.fixture
def db_connection():
    """Fixture for database connection - skip if env vars not set"""
    required_vars = ['REDSHIFT_HOST', 'REDSHIFT_DATABASE', 'REDSHIFT_USER', 'REDSHIFT_PASSWORD']
    missing_vars = [var for var in required_vars if var not in os.environ]
    
    if missing_vars:
        pytest.skip(f"Skipping integration test - missing environment variables: {', '.join(missing_vars)}")
    
    conn = connect_with_retry(max_retries=3)
    yield conn
    conn.close()


def test_store_forecast(db_connection):
    """Test that forecasts are stored correctly in demand_forecast table"""
    # Arrange
    test_product_id = 'PROD-00001'  # Use existing product from synthetic data
    horizon = 7
    forecast = 150
    intervals_80 = {'lower': 120, 'upper': 180}
    intervals_95 = {'lower': 100, 'upper': 200}
    
    # Act
    forecast_id = store_forecast(
        conn=db_connection,
        product_id=test_product_id,
        horizon=horizon,
        forecast=forecast,
        intervals_80=intervals_80,
        intervals_95=intervals_95
    )
    
    # Assert
    cursor = db_connection.cursor()
    
    # Check that both confidence level records were created
    query = """
        SELECT 
            forecast_id,
            product_id,
            forecast_horizon_days,
            predicted_demand,
            confidence_interval_lower,
            confidence_interval_upper,
            confidence_level
        FROM demand_forecast
        WHERE forecast_id LIKE %s
        ORDER BY confidence_level
    """
    
    cursor.execute(query, (f"{forecast_id}%",))
    results = cursor.fetchall()
    
    assert len(results) == 2, "Should have 2 records (80% and 95% confidence)"
    
    # Check 80% confidence record
    record_80 = results[0]
    assert record_80[1] == test_product_id
    assert record_80[2] == horizon
    assert record_80[3] == forecast
    assert record_80[4] == intervals_80['lower']
    assert record_80[5] == intervals_80['upper']
    assert float(record_80[6]) == 0.80
    
    # Check 95% confidence record
    record_95 = results[1]
    assert record_95[1] == test_product_id
    assert record_95[2] == horizon
    assert record_95[3] == forecast
    assert record_95[4] == intervals_95['lower']
    assert record_95[5] == intervals_95['upper']
    assert float(record_95[6]) == 0.95
    
    cursor.close()
    print(f"✓ Forecast stored successfully with ID: {forecast_id}")


def test_calculate_forecast_accuracy_with_actual_data(db_connection):
    """Test MAPE calculation with actual sales data"""
    # Arrange - Create a test forecast in the past
    cursor = db_connection.cursor()
    
    # Find a product with historical sales data
    cursor.execute("""
        SELECT DISTINCT sol.product_id
        FROM sales_order_line sol
        JOIN sales_order_header soh ON sol.so_id = soh.so_id
        WHERE soh.order_date >= CURRENT_DATE - INTERVAL '60 days'
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if not result:
        pytest.skip("No historical sales data available for testing")
    
    test_product_id = result[0]
    
    # Get actual sales for a past period (30 days ago, 7-day horizon)
    forecast_date = datetime.now().date() - timedelta(days=30)
    horizon_days = 7
    
    cursor.execute("""
        SELECT SUM(sol.quantity) as actual_demand
        FROM sales_order_line sol
        JOIN sales_order_header soh ON sol.so_id = soh.so_id
        WHERE sol.product_id = %s
        AND soh.order_date >= %s
        AND soh.order_date < %s + INTERVAL '7 days'
    """, (test_product_id, forecast_date, forecast_date))
    
    actual_result = cursor.fetchone()
    actual_demand = int(actual_result[0]) if actual_result and actual_result[0] else 0
    
    if actual_demand == 0:
        pytest.skip("No actual demand in test period")
    
    # Create a test forecast with a known prediction
    predicted_demand = int(actual_demand * 1.2)  # 20% over-prediction
    
    forecast_id = f"TEST-{uuid.uuid4().hex[:12]}"
    
    cursor.execute("""
        INSERT INTO demand_forecast (
            forecast_id,
            product_id,
            warehouse_id,
            forecast_date,
            forecast_horizon_days,
            predicted_demand,
            confidence_interval_lower,
            confidence_interval_upper,
            confidence_level,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        forecast_id,
        test_product_id,
        None,
        forecast_date,
        horizon_days,
        predicted_demand,
        int(predicted_demand * 0.8),
        int(predicted_demand * 1.2),
        0.80,
        datetime.now()
    ))
    
    db_connection.commit()
    
    # Act - Calculate accuracy
    results = calculate_forecast_accuracy(db_connection)
    
    # Assert
    assert results['successful'] > 0, "Should have calculated at least one accuracy metric"
    
    # Verify the accuracy record was created
    cursor.execute("""
        SELECT 
            accuracy_id,
            product_id,
            forecast_date,
            actual_demand,
            predicted_demand,
            mape
        FROM forecast_accuracy
        WHERE product_id = %s
        AND forecast_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (test_product_id, forecast_date))
    
    accuracy_record = cursor.fetchone()
    
    assert accuracy_record is not None, "Accuracy record should be created"
    assert accuracy_record[1] == test_product_id
    assert accuracy_record[2] == forecast_date
    assert accuracy_record[3] == actual_demand
    assert accuracy_record[4] == predicted_demand
    
    # Verify MAPE calculation
    expected_mape = abs(actual_demand - predicted_demand) / actual_demand * 100
    actual_mape = float(accuracy_record[5])
    
    assert abs(actual_mape - expected_mape) < 0.1, f"MAPE should be {expected_mape:.2f}, got {actual_mape:.2f}"
    
    cursor.close()
    print(f"✓ Accuracy calculated: MAPE={actual_mape:.2f}%, Predicted={predicted_demand}, Actual={actual_demand}")


def test_calculate_forecast_accuracy_zero_actual_demand(db_connection):
    """Test MAPE calculation when actual demand is zero"""
    # Arrange - Create a test forecast with zero actual demand
    cursor = db_connection.cursor()
    
    # Find a product
    cursor.execute("SELECT product_id FROM product LIMIT 1")
    test_product_id = cursor.fetchone()[0]
    
    # Use a date far in the past where there's likely no sales
    forecast_date = datetime.now().date() - timedelta(days=365)
    horizon_days = 7
    predicted_demand = 100
    
    forecast_id = f"TEST-ZERO-{uuid.uuid4().hex[:12]}"
    
    cursor.execute("""
        INSERT INTO demand_forecast (
            forecast_id,
            product_id,
            warehouse_id,
            forecast_date,
            forecast_horizon_days,
            predicted_demand,
            confidence_interval_lower,
            confidence_interval_upper,
            confidence_level,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        forecast_id,
        test_product_id,
        None,
        forecast_date,
        horizon_days,
        predicted_demand,
        80,
        120,
        0.80,
        datetime.now()
    ))
    
    db_connection.commit()
    
    # Act
    results = calculate_forecast_accuracy(db_connection)
    
    # Assert
    assert results['successful'] > 0, "Should handle zero actual demand case"
    
    # Verify MAPE is 100 when actual is 0 but predicted is not
    cursor.execute("""
        SELECT mape, actual_demand, predicted_demand
        FROM forecast_accuracy
        WHERE product_id = %s
        AND forecast_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (test_product_id, forecast_date))
    
    accuracy_record = cursor.fetchone()
    
    if accuracy_record:
        mape = float(accuracy_record[0])
        actual = accuracy_record[1]
        predicted = accuracy_record[2]
        
        if actual == 0 and predicted > 0:
            assert mape == 100.0, "MAPE should be 100 when actual is 0 and predicted is not"
        
        print(f"✓ Zero demand case handled: MAPE={mape:.2f}%, Predicted={predicted}, Actual={actual}")
    
    cursor.close()


def test_forecast_accuracy_not_duplicated(db_connection):
    """Test that accuracy is not calculated twice for the same forecast"""
    # Arrange - Create a test forecast
    cursor = db_connection.cursor()
    
    cursor.execute("SELECT product_id FROM product LIMIT 1")
    test_product_id = cursor.fetchone()[0]
    
    forecast_date = datetime.now().date() - timedelta(days=20)
    horizon_days = 7
    predicted_demand = 50
    
    forecast_id = f"TEST-DUP-{uuid.uuid4().hex[:12]}"
    
    cursor.execute("""
        INSERT INTO demand_forecast (
            forecast_id,
            product_id,
            warehouse_id,
            forecast_date,
            forecast_horizon_days,
            predicted_demand,
            confidence_interval_lower,
            confidence_interval_upper,
            confidence_level,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        forecast_id,
        test_product_id,
        None,
        forecast_date,
        horizon_days,
        predicted_demand,
        40,
        60,
        0.80,
        datetime.now()
    ))
    
    db_connection.commit()
    
    # Act - Calculate accuracy twice
    results1 = calculate_forecast_accuracy(db_connection)
    results2 = calculate_forecast_accuracy(db_connection)
    
    # Assert - Second run should not create duplicate records
    cursor.execute("""
        SELECT COUNT(*) 
        FROM forecast_accuracy
        WHERE product_id = %s
        AND forecast_date = %s
    """, (test_product_id, forecast_date))
    
    count = cursor.fetchone()[0]
    
    assert count == 1, "Should not create duplicate accuracy records"
    
    cursor.close()
    print(f"✓ Duplicate prevention working: {count} record(s) created")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
