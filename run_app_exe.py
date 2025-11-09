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

# Import port management utilities
try:
    from core.port_manager import ensure_port_free, is_port_in_use, kill_process_on_port
except ImportError:
    # Fallback if port_manager is not available
    print("Warning: core.port_manager not available, using basic port check")
    
    def is_port_in_use(port, host='127.0.0.1'):
        """Check if port is in use (fallback)."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return False
            except OSError:
                return True
    
    def kill_process_on_port(port):
        """Kill process using the port (fallback, Windows only)."""
        try:
            if platform.system() != 'Windows':
                return False
            
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
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        try:
                            pid_int = int(pid)
                            if pid_int > 0:
                                pids_found.append(pid)
                        except ValueError:
                            continue
            
            killed_any = False
            for pid in pids_found:
                try:
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
                except Exception as e:
                    print(f"Error terminating process {pid}: {e}")
            
            if killed_any:
                time.sleep(2)
                return True
            
            return False
        except Exception as e:
            print(f"Error searching for process on port {port}: {e}")
            return False
    
    def ensure_port_free(port, host='127.0.0.1', max_wait=15):
        """Ensure port is free (fallback)."""
        if not is_port_in_use(port, host):
            return True
        
        if kill_process_on_port(port):
            for _ in range(max_wait * 2):
                if not is_port_in_use(port, host):
                    return True
                time.sleep(0.5)
        
        return False

def start_server():
    """Start the server."""
    try:
        print("Starting Local Brain...")
        print(f"Working directory: {os.getcwd()}")
        print(f"Python version: {sys.version}")
        
        # Check and ensure port is free
        port = 8000
        print(f"Checking port {port}...")
        
        if not ensure_port_free(port, host='127.0.0.1', max_wait=15):
            print(f"Error: Port {port} could not be freed.")
            print("Possible reasons:")
            print("  1. Another application is using the port")
            print("  2. Port is in TIME_WAIT state (wait a few seconds and try again)")
            print("  3. Process requires administrator rights to terminate")
            print("\nPlease close other programs using this port, or restart your computer.")
            input("Press Enter to exit...")
            sys.exit(1)
        
        print(f"Port {port} is free and ready to use.")
        
        print(f"Server will be available at: http://127.0.0.1:{port}")
        
        # Start server (without --reload for exe)
        try:
            # Configure uvicorn with settings that help with port reuse
            config = uvicorn.Config(
                app=app,
                host="127.0.0.1",
                port=port,
                log_level="info",
                server_header=False,
                date_header=False,
                # Note: uvicorn doesn't directly expose SO_REUSEADDR,
                # but we handle port checking before startup
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

