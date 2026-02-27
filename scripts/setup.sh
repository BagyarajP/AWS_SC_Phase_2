#!/bin/bash

# Supply Chain AI Platform - Setup Script
# This script sets up the development environment

set -e

echo "============================================================"
echo "Supply Chain AI Platform - Setup"
echo "============================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "✗ Python 3.9+ required. Found: $python_version"
    exit 1
fi
echo "✓ Python $python_version"

# Check AWS CLI
echo "Checking AWS CLI..."
if ! command -v aws &> /dev/null; then
    echo "✗ AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi
aws_version=$(aws --version 2>&1 | awk '{print $1}')
echo "✓ $aws_version"

# Check AWS credentials
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "✗ AWS credentials not configured. Run: aws configure"
    exit 1
fi
echo "✓ AWS credentials configured"

# Check region
echo "Checking AWS region..."
region=$(aws configure get region)
if [ "$region" != "us-east-1" ]; then
    echo "⚠ Warning: Region is $region, but us-east-1 is recommended"
    echo "  To change: aws configure set region us-east-1"
else
    echo "✓ Region: us-east-1"
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# Create data directories
echo ""
echo "Creating data directories..."
mkdir -p data/synthetic
mkdir -p data/raw
mkdir -p data/processed
mkdir -p logs
echo "✓ Directories created"

# Summary
echo ""
echo "============================================================"
echo "Setup Complete! ✓"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Generate synthetic data: python scripts/generate_synthetic_data.py"
echo "  3. Follow the guide in infrastructure/redshift/README.md"
echo ""
echo "To deactivate virtual environment: deactivate"
