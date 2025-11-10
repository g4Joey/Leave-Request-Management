#!/bin/bash
# Setup script for Leave Request Management System
# This creates a virtual environment and installs all dependencies
# Requires Python 3.13+

set -e  # Exit on error

echo "=========================================="
echo "Setting up Leave Management System"
echo "=========================================="
echo ""

# Check if Python 3.13 is installed
if ! command -v python3.13 &> /dev/null; then
    echo "❌ Error: Python 3.13 is not installed"
    echo ""
    echo "This project requires Python 3.13+. Your current version:"
    python3 --version 2>&1 || echo "Python 3 not found"
    echo ""
    echo "📖 Please see INSTALL_PYTHON.md for installation instructions"
    echo ""
    echo "Quick install with Homebrew:"
    echo "  brew install python@3.13"
    echo ""
    exit 1
fi

echo "✅ Python 3.13 found: $(python3.13 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment with Python 3.13..."
if [ -d ".venv" ]; then
    echo "⚠️  .venv directory already exists. Removing it..."
    rm -rf .venv
fi

python3.13 -m venv .venv
echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip
echo ""

# Install dependencies
echo "📦 Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "To use the system:"
echo "1. Activate the virtual environment:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Run Django commands:"
echo "   python manage.py migrate"
echo "   python manage.py runserver"
echo ""
echo "3. To deactivate when done:"
echo "   deactivate"
echo ""
