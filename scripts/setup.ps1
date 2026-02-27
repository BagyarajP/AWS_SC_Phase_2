# Supply Chain AI Platform - Setup Script (PowerShell)
# This script sets up the development environment on Windows

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Supply Chain AI Platform - Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1 | Select-String -Pattern "Python (\d+\.\d+)" | ForEach-Object { $_.Matches.Groups[1].Value }
    if ([version]$pythonVersion -lt [version]"3.9") {
        Write-Host "✗ Python 3.9+ required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Python $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.9+: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Check AWS CLI
Write-Host "Checking AWS CLI..." -ForegroundColor Yellow
try {
    $awsVersion = aws --version 2>&1
    Write-Host "✓ $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not found. Please install: https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

# Check AWS credentials
Write-Host "Checking AWS credentials..." -ForegroundColor Yellow
try {
    aws sts get-caller-identity | Out-Null
    Write-Host "✓ AWS credentials configured" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS credentials not configured. Run: aws configure" -ForegroundColor Red
    exit 1
}

# Check region
Write-Host "Checking AWS region..." -ForegroundColor Yellow
$region = aws configure get region
if ($region -ne "us-east-1") {
    Write-Host "⚠ Warning: Region is $region, but us-east-1 is recommended" -ForegroundColor Yellow
    Write-Host "  To change: aws configure set region us-east-1" -ForegroundColor Yellow
} else {
    Write-Host "✓ Region: us-east-1" -ForegroundColor Green
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt | Out-Null
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create data directories
Write-Host ""
Write-Host "Creating data directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "data\synthetic" | Out-Null
New-Item -ItemType Directory -Force -Path "data\raw" | Out-Null
New-Item -ItemType Directory -Force -Path "data\processed" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Setup Complete! ✓" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Virtual environment is already activated"
Write-Host "  2. Generate synthetic data: python scripts\generate_synthetic_data.py"
Write-Host "  3. Follow the guide in infrastructure\redshift\README.md"
Write-Host ""
Write-Host "To deactivate virtual environment: deactivate"
