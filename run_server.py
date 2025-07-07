#!/usr/bin/env python3
"""
Fire Detection System Server
Run this file to start the server
"""

import uvicorn
import webbrowser
import time
import threading
import os

def open_browser():
    """Open browser after server starts"""
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://localhost:8000")

def main():
    print("🔥 Fire Detection System Starting...")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ["app.py", "model.py", "templates/index.html"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Error: Required file '{file}' not found!")
            return
    
    print("✅ All required files found")
    
    # Check if model file exists
    if os.path.exists("best.pt"):
        print("✅ Fire detection model found")
    else:
        print("⚠️  Model file 'best.pt' not found - running without fire detection")
    
    print("\n🚀 Starting server...")
    print("📱 Server will be available at: http://localhost:8000")
    print("🌐 Browser will open automatically")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        # Start the server
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")

if __name__ == "__main__":
    main()
