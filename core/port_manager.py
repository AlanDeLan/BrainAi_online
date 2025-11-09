"""
Port management utilities for Local Brain.
Handles port checking and freeing on Windows and other platforms.
"""
import socket
import time
import subprocess
import platform
import os
from typing import Optional, List

# Try to import logger, fallback to basic logging
try:
    from core.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger("local_brain")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

def is_port_in_use(port: int, host: str = '127.0.0.1', check_time_wait: bool = True) -> bool:
    """
    Check if port is in use.
    
    Args:
        port: Port number to check
        host: Host address (default: 127.0.0.1)
        check_time_wait: If True, also check for TIME_WAIT state
    
    Returns:
        True if port is in use, False otherwise
    """
    # First, try to bind to the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Set SO_REUSEADDR to allow binding even if port is in TIME_WAIT
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(1)
            return False
        except OSError as e:
            # Port is in use
            if e.errno == 10048 or e.errno == 98:  # Windows: Address already in use, Linux: Address already in use
                if check_time_wait:
                    # Check if it's in TIME_WAIT state (will be released soon)
                    return check_port_time_wait(port, host)
                return True
            return True

def check_port_time_wait(port: int, host: str = '127.0.0.1') -> bool:
    """
    Check if port is in TIME_WAIT state (temporary state after connection close).
    TIME_WAIT ports will be released automatically after a timeout.
    
    Args:
        port: Port number to check
        host: Host address
    
    Returns:
        True if port is in TIME_WAIT (will be released), False if truly in use
    """
    if platform.system() != 'Windows':
        # On Linux/Mac, TIME_WAIT connections show up in netstat
        try:
            result = subprocess.run(
                ['netstat', '-an'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'TIME_WAIT' in line:
                        logger.debug(f"Port {port} is in TIME_WAIT state, will be released soon")
                        return False  # Not truly in use, just waiting
        except Exception:
            pass
    else:
        # On Windows, check netstat output
        try:
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                shell=True,
                timeout=3
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{port}' in line:
                        # Check if it's in TIME_WAIT or CLOSE_WAIT state
                        if 'TIME_WAIT' in line or 'CLOSE_WAIT' in line:
                            logger.debug(f"Port {port} is in TIME_WAIT/CLOSE_WAIT state, will be released soon")
                            return False  # Not truly in use, just waiting
        except Exception:
            pass
    
    return True  # Port is truly in use

def get_processes_on_port(port: int) -> List[dict]:
    """
    Get list of processes using the port.
    
    Args:
        port: Port number
    
    Returns:
        List of dictionaries with process info: [{"pid": int, "name": str}, ...]
    """
    processes = []
    
    try:
        if platform.system() == 'Windows':
            # Windows: use netstat and tasklist
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                shell=True,
                timeout=5
            )
            
            if result.returncode == 0:
                pids_found = set()
                for line in result.stdout.split('\n'):
                    # Look for lines like: TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       12345
                    if f':{port}' in line and ('LISTENING' in line or 'ESTABLISHED' in line):
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                pid_int = int(pid)
                                if pid_int > 0:
                                    pids_found.add(pid_int)
                            except ValueError:
                                continue
                
                # Get process names
                for pid in pids_found:
                    try:
                        check_result = subprocess.run(
                            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                            capture_output=True,
                            text=True,
                            shell=True,
                            timeout=3
                        )
                        
                        if pid in check_result.stdout:
                            # Parse CSV output
                            lines = check_result.stdout.strip().split('\n')
                            if len(lines) > 1:  # Skip header
                                parts = lines[1].split(',')
                                if len(parts) > 0:
                                    name = parts[0].strip('"')
                                    processes.append({"pid": pid, "name": name})
                    except Exception as e:
                        logger.debug(f"Error getting process info for PID {pid}: {e}")
                        processes.append({"pid": pid, "name": "unknown"})
        else:
            # Linux/Mac: use lsof or netstat
            try:
                result = subprocess.run(
                    ['lsof', '-i', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        for line in lines[1:]:
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1])
                                    name = parts[0]
                                    processes.append({"pid": pid, "name": name})
                                except (ValueError, IndexError):
                                    continue
            except FileNotFoundError:
                # Fallback to netstat on Linux
                try:
                    result = subprocess.run(
                        ['netstat', '-tlnp'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if f':{port}' in line and 'LISTEN' in line:
                                parts = line.split()
                                if len(parts) >= 7:
                                    pid_part = parts[-1]
                                    if '/' in pid_part:
                                        pid, name = pid_part.split('/', 1)
                                        try:
                                            processes.append({"pid": int(pid), "name": name})
                                        except ValueError:
                                            continue
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error getting processes on port {port}: {e}", exc_info=True)
    
    return processes

def kill_process_on_port(port: int, force: bool = True, wait_timeout: int = 10) -> bool:
    """
    Kill process using the port.
    
    Args:
        port: Port number
        force: If True, force kill (SIGKILL / taskkill /F)
        wait_timeout: Maximum time to wait for port to be released (seconds)
    
    Returns:
        True if process was killed and port is free, False otherwise
    """
    processes = get_processes_on_port(port)
    
    if not processes:
        logger.debug(f"No processes found on port {port}")
        return False
    
    killed_any = False
    
    for proc in processes:
        pid = proc["pid"]
        name = proc.get("name", "unknown")
        
        try:
            if platform.system() == 'Windows':
                # Windows: use taskkill
                cmd = ['taskkill']
                if force:
                    cmd.append('/F')
                cmd.extend(['/PID', str(pid)])
                
                kill_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=5
                )
                
                if kill_result.returncode == 0:
                    logger.info(f"Terminated process {name} (PID: {pid}) that was using port {port}")
                    killed_any = True
                else:
                    # May need administrator rights
                    error_msg = kill_result.stderr.strip() if kill_result.stderr else "Unknown error"
                    if "access is denied" in error_msg.lower() or "not found" not in error_msg.lower():
                        logger.warning(f"Failed to terminate process {name} (PID: {pid}): {error_msg}")
                        logger.warning("May need administrator rights")
            else:
                # Linux/Mac: use kill
                signal = 'SIGKILL' if force else 'SIGTERM'
                kill_result = subprocess.run(
                    ['kill', f'-{signal}', str(pid)] if force else ['kill', str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if kill_result.returncode == 0:
                    logger.info(f"Terminated process {name} (PID: {pid}) that was using port {port}")
                    killed_any = True
                else:
                    error_msg = kill_result.stderr.strip() if kill_result.stderr else "Unknown error"
                    logger.warning(f"Failed to terminate process {name} (PID: {pid}): {error_msg}")
        except Exception as e:
            logger.error(f"Error terminating process {name} (PID: {pid}): {e}", exc_info=True)
    
    if killed_any:
        # Wait for port to be released
        logger.debug(f"Waiting for port {port} to be released...")
        for i in range(wait_timeout * 2):  # Check every 0.5 seconds
            if not is_port_in_use(port, check_time_wait=False):
                logger.info(f"Port {port} is now free!")
                return True
            time.sleep(0.5)
        
        # Check if port is in TIME_WAIT (will be released automatically)
        if not check_port_time_wait(port):
            logger.info(f"Port {port} is in TIME_WAIT state, will be released automatically")
            return True
        
        logger.warning(f"Port {port} is still in use after {wait_timeout} seconds")
        return False
    
    return False

def ensure_port_free(port: int, host: str = '127.0.0.1', max_wait: int = 15) -> bool:
    """
    Ensure port is free, killing processes if necessary.
    
    Args:
        port: Port number
        host: Host address
        max_wait: Maximum time to wait for port to be free (seconds)
    
    Returns:
        True if port is free, False otherwise
    """
    if not is_port_in_use(port, host):
        logger.debug(f"Port {port} is already free")
        return True
    
    logger.info(f"Port {port} is busy. Attempting to free it...")
    
    # Try to kill processes on the port
    if kill_process_on_port(port, force=True, wait_timeout=max_wait):
        return True
    
    # If still in use, wait a bit more (might be in TIME_WAIT)
    logger.info(f"Waiting for port {port} to be released...")
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if not is_port_in_use(port, host, check_time_wait=True):
            logger.info(f"Port {port} is now free!")
            return True
        time.sleep(0.5)
    
    logger.error(f"Port {port} could not be freed after {max_wait} seconds")
    return False

