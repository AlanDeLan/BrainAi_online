"""
Entry point for PyInstaller (exe version).
This file is used instead of run_app.py for exe build.
"""
import os
import sys
import time
import webbrowser
import socket
import subprocess
import platform
import traceback

# Set UTF-8 encoding for stdout/stderr
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add current directory to import path
try:
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller mode
        sys.path.insert(0, sys._MEIPASS)
        # Set working directory next to exe file
        if getattr(sys, 'frozen', False):
            # Executable file
            os.chdir(os.path.dirname(sys.executable))
        else:
            # Script
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception as e:
    print(f"Error setting up paths: {e}")
    traceback.print_exc()

# Import main after setting paths
try:
    from main import app, set_server_instance
    import uvicorn
    import threading
except Exception as e:
    print(f"Error importing modules: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

def is_port_in_use(port, host='127.0.0.1'):
    """Check if port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True

def kill_process_on_port(port):
    """Kill process using the port (Windows only)."""
    try:
        if platform.system() != 'Windows':
            return False
        
        # Find PID of process using the port
        # Use netstat to find process on port
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True,
            timeout=5
        )
        
        if result.returncode != 0:
            return False
        
        pids_found = []
        for line in result.stdout.split('\n'):
            # Look for lines like: TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       12345
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    # Check if it's really a number
                    try:
                        pid_int = int(pid)
                        if pid_int > 0:
                            pids_found.append(pid)
                    except ValueError:
                        continue
        
        # Kill all found processes
        killed_any = False
        for pid in pids_found:
            try:
                # Check if process still exists
                check_result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=3
                )
                
                if pid in check_result.stdout:
                    # Kill process
                    kill_result = subprocess.run(
                        ['taskkill', '/F', '/PID', pid],
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=5
                    )
                    
                    if kill_result.returncode == 0:
                        print(f"Terminated process {pid} that was using port {port}")
                        killed_any = True
                    else:
                        # May need administrator rights
                        print(f"Failed to terminate process {pid} (may need administrator rights)")
            except Exception as e:
                print(f"Error terminating process {pid}: {e}")
        
        if killed_any:
            time.sleep(1.5)  # Give time for port to be released
            return True
        
        return False
    except Exception as e:
        print(f"Error searching for process on port {port}: {e}")
        return False

def start_server():
    """Start the server."""
    try:
        print("Starting Local Brain...")
        print(f"Working directory: {os.getcwd()}")
        print(f"Python version: {sys.version}")
        
        # Check if port is in use
        port = 8000
        if is_port_in_use(port):
            print(f"Port {port} is busy. Attempting to terminate process...")
            if kill_process_on_port(port):
                # Wait for port to be released
                for _ in range(10):
                    if not is_port_in_use(port):
                        print(f"Port {port} is now free!")
                        break
                    time.sleep(0.5)
            
            # If port is still busy after attempting to kill process
            if is_port_in_use(port):
                print(f"Error: Port {port} is still busy and could not be freed.")
                print("Please close other programs using this port, or restart your computer.")
                input("Press Enter to exit...")
                sys.exit(1)
        
        print(f"Server will be available at: http://127.0.0.1:{port}")
        
        # Start server (without --reload for exe)
        try:
            config = uvicorn.Config(
                app=app,
                host="127.0.0.1",
                port=port,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            # Register server instance for graceful shutdown
            set_server_instance(server)
            
            # Start server in separate thread
            server_thread = threading.Thread(target=server.run, daemon=False)
            server_thread.start()
            
            # Wait for server to become available
            print("Waiting for server to start...")
            for i in range(30):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1):
                        print(f"Server is ready!")
                        break
                except Exception:
                    if i % 5 == 0:
                        print(f"Waiting... ({i+1}/30)")
                    time.sleep(0.5)
            else:
                print("Error: Server did not start within 15 seconds")
                print("Check the error messages above for details.")
                input("Press Enter to exit...")
                sys.exit(1)
            
            print("Server started successfully!")
            print("Opening browser...")
            try:
                webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print(f"Please open manually: http://127.0.0.1:{port}")
            print("\nTo exit, close this window, press Ctrl+C, or use the 'End Session' button in the interface")
            
            try:
                server_thread.join()
            except KeyboardInterrupt:
                print("\nShutting down...")
                # Try graceful shutdown
                if hasattr(server, 'should_exit'):
                    server.should_exit = True
                    time.sleep(1)
                sys.exit(0)
        except Exception as e:
            print(f"Error starting server: {e}")
            traceback.print_exc()
            input("Press Enter to exit...")
            sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    start_server()

