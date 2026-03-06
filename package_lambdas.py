"""
Automated Lambda Function Packaging Script
Supply Chain AI Platform

This script packages all Lambda functions with their dependencies into .zip files
ready for deployment to AWS Lambda.

Usage:
    python package_lambdas.py
"""

import os
import shutil
import subprocess
import zipfile
import sys

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
    """
    Package a Lambda function with its dependencies
    
    Args:
        source_file: Path to the Python source file
        dependencies: List of pip packages to install
        output_dir: Output directory for zip files
    """
    # Get function name from file
    function_name = os.path.splitext(os.path.basename(source_file))[0]
    
    # Create temp directory
    temp_dir = os.path.join(output_dir, 'temp', function_name)
    os.makedirs(temp_dir, exist_ok=True)
    
    print(f"\n📦 Packaging {function_name}...")
    
    try:
        # Copy source file
        dest_file = os.path.join(temp_dir, os.path.basename(source_file))
        shutil.copy(source_file, dest_file)
        print(f"   ✓ Copied source file")
        
        # Install dependencies for Linux (Lambda runtime)
        if dependencies:
            print(f"   ⏳ Installing dependencies: {', '.join(dependencies)}")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', *dependencies, '-t', temp_dir, 
                 '--platform', 'manylinux2014_x86_64', '--only-binary=:all:', '--quiet'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"   ⚠️  Warning: Some dependencies may have failed to install")
                print(f"   Error: {result.stderr}")
                print(f"   ℹ️  Retrying without platform-specific flags...")
                # Fallback: try without platform flags
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', *dependencies, '-t', temp_dir, '--quiet'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"   ✓ Dependencies installed (fallback method)")
            else:
                print(f"   ✓ Dependencies installed (Linux-compatible)")
        
        # Create zip file
        zip_path = os.path.join(output_dir, f'{function_name}.zip')
        
        # Remove existing zip if it exists
        if os.path.exists(zip_path):
            os.remove(zip_path)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                # Skip __pycache__ and .pyc files
                dirs[:] = [d for d in dirs if d != '__pycache__']
                
                for file in files:
                    if not file.endswith('.pyc'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
        
        # Get zip file size
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)  # Convert to MB
        print(f"   ✓ Created: {zip_path} ({zip_size:.2f} MB)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error packaging {function_name}: {str(e)}")
        return False
    
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    """Main packaging function"""
    print("=" * 70)
    print("Supply Chain AI Platform - Lambda Function Packager")
    print("=" * 70)
    
    # Create output directory
    output_dir = 'lambda_packages'
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📁 Output directory: {output_dir}")
    
    # Track statistics
    total_functions = 0
    successful = 0
    failed = 0
    skipped = 0
    
    # Package all functions
    for agent_type, functions in LAMBDA_FUNCTIONS.items():
        print(f"\n{'=' * 70}")
        print(f"🤖 Packaging {agent_type.upper()} agent functions")
        print(f"{'=' * 70}")
        
        for source_file, dependencies in functions:
            total_functions += 1
            
            if not os.path.exists(source_file):
                print(f"\n⚠️  WARNING: {source_file} not found, skipping")
                skipped += 1
                continue
            
            if package_lambda(source_file, dependencies, output_dir):
                successful += 1
            else:
                failed += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 PACKAGING SUMMARY")
    print("=" * 70)
    print(f"Total functions: {total_functions}")
    print(f"✅ Successfully packaged: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Skipped (not found): {skipped}")
    
    if successful > 0:
        print(f"\n✅ All Lambda packages created in '{output_dir}' directory")
        print("\n📋 Next Steps:")
        print("1. Upload .zip files to S3:")
        print(f"   - Forecasting: s3://supply-chain-data-YOUR_ACCOUNT_ID/lambda/forecasting/")
        print(f"   - Procurement: s3://supply-chain-data-YOUR_ACCOUNT_ID/lambda/procurement/")
        print(f"   - Inventory: s3://supply-chain-data-YOUR_ACCOUNT_ID/lambda/inventory/")
        print(f"   - Metrics: s3://supply-chain-data-YOUR_ACCOUNT_ID/lambda/metrics/")
        print("\n2. Create Lambda functions in AWS Console")
        print("3. Refer to documents/PHASE_6_LAMBDA_DEPLOYMENT_CORRECTED.md for details")
    
    if failed > 0:
        print(f"\n⚠️  {failed} function(s) failed to package. Check errors above.")
        return 1
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Packaging interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
