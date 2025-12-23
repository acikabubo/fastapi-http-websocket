"""
Wrapper script for running the server with profiling support.

This script is used by Scalene to profile the application.
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000)
