import os
import sys
from pathlib import Path
import threading
import webbrowser
import time

def setup_environment():
    # Ensure dependencies and ffmpeg warnings are handled if necessary
    pass

def start_browser():
    # Wait a second for the Flask server to start, then open the browser
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

def main():
    print("Starting Velo Content Engine...")
    print("The Web Dashboard is booting up. Please wait...")
    
    setup_environment()
    
    # Start the browser thread
    threading.Thread(target=start_browser, daemon=True).start()
    
    # Start the Flask app
    try:
        from app import app
        app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    except ImportError as e:
        print(f"Error starting server: {e}")
        print("Did you forget to install the new web requirements? Run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
