"""
Simple startup script for the MCP HTTP Server
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY environment variable is required")
        print("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Get configuration
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    print("🚀 Starting MCP HTTP Server...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    print(f"❤️  Health Check: http://{host}:{port}/health")
    print("\n🔧 Available Endpoints:")
    print(f"  POST http://{host}:{port}/query")
    print(f"  GET  http://{host}:{port}/query?query=your-query&user_id=your-user-id")
    print(f"  GET  http://{host}:{port}/query/stream?query=your-query&user_id=your-user-id")
    print("\n⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        uvicorn.run(
            "mcp_http_server:app",
            host=host,
            port=port,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
