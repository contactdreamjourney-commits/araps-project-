import sys
import os
import subprocess
import time
import urllib.request
import webbrowser

def is_server_running(url):
    try:
        # Check if the site is reachable (any status response code, even redirect or 404/302, means the server is up)
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=1) as response:
            return True
    except urllib.error.HTTPError:
        # Even if it returns 404 or 403 or 302, the server is running
        return True
    except Exception:
        return False

def main():
    url = "http://127.0.0.1:8000/"
    print("Starting Django development server...")
    
    # Run the server in a subprocess. sys.executable points to the active virtual environment's python.
    p = subprocess.Popen([sys.executable, "manage.py", "runserver", "127.0.0.1:8000"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
    
    try:
        # Poll the server until it responds
        print("Waiting for server to start...")
        success = False
        for _ in range(30):  # Poll up to 15 seconds (30 * 0.5s)
            if is_server_running(url):
                success = True
                break
            time.sleep(0.5)
            
        if not success:
            print("Warning: Server did not respond within timeout. Opening app window anyway.")
            
        print("Opening ARAPS Application...")
        
        # Try running with pywebview
        try:
            import webview
            webview.create_window("ARAPS - Academic Result Analysis & Prediction System", url, width=1280, height=800)
            webview.start()
        except Exception as e:
            print(f"pywebview failed/not installed: {e}")
            print("Falling back to opening default browser...")
            webbrowser.open(url)
            # Keep script alive so the server runs until interrupted
            print("Press Ctrl+C to terminate the server...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    finally:
        print("Terminating Django server process...")
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
        print("Server terminated successfully.")

if __name__ == "__main__":
    main()
