#!/usr/bin/env python3
"""
Setup script for the Telegram MCP Server

This script helps users configure the telegram MCP server
by creating the necessary .env file and checking dependencies.
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create a .env file with user input."""
    print("🔧 Telegram MCP Server Setup")
    print("=" * 50)
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        print("⚠️ .env file already exists!")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Setup cancelled.")
            return False
    
    print("\n📝 Please provide your Telegram API credentials:")
    print("Get these from: https://my.telegram.org/auth")
    print()
    
    # Get API credentials
    api_id = input("Enter your Telegram API ID: ").strip()
    if not api_id:
        print("❌ API ID is required")
        return False
    
    api_hash = input("Enter your Telegram API Hash: ").strip()
    if not api_hash:
        print("❌ API Hash is required")
        return False
    
    phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
    if not phone:
        print("❌ Phone number is required")
        return False
    
    # Optional session file name
    session_file = input("Enter session file name (default: telegram_session): ").strip()
    if not session_file:
        session_file = "telegram_session"
    
    # Create .env content
    env_content = f"""# Telegram API Credentials
# Get these from https://my.telegram.org/auth
TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}

# Your phone number (with country code, e.g., +1234567890)
TELEGRAM_PHONE={phone}

# Optional: Custom session file name (default: telegram_session)
TELEGRAM_SESSION_FILE={session_file}
"""
    
    # Write .env file
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print(f"\n✅ Created .env file successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = ['telethon', 'mcp', 'fastmcp', 'python-dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        install = input("Do you want to install them now? (Y/n): ").lower().strip()
        if install != 'n':
            try:
                import subprocess
                subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages, check=True)
                print("✅ Dependencies installed successfully!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                return False
        else:
            print("Please install the missing packages manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    else:
        print("✅ All dependencies are installed!")
        return True

def create_directories():
    """Create necessary directories."""
    print("\n📁 Creating directories...")
    
    directories = ['logs']
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {directory}/ directory")
        else:
            print(f"✅ {directory}/ directory already exists")

def main():
    """Main setup function."""
    print("🚀 Welcome to Telegram MCP Server Setup!")
    print("This script will help you configure the server.\n")
    
    # Check if we're in the right directory
    if not Path("telegram_mcp_server.py").exists():
        print("❌ Please run this script from the telegram directory")
        print("   cd telegram")
        print("   python setup.py")
        sys.exit(1)
    
    # Run setup steps
    if not create_env_file():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    create_directories()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Test the server: python test_telegram_server.py")
    print("2. Run the server: python telegram_mcp_server.py")
    print("3. Or use the provided scripts:")
    print("   - Windows: .\\run_telegram_server.ps1")
    print("   - Unix/Linux: ./run_telegram_server.sh")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main()
