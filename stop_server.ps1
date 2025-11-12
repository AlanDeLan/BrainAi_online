# PowerShell script to stop the Local Brain server
# Usage: .\stop_server.ps1

Write-Host "=== Stopping Local Brain Server ===" -ForegroundColor Yellow

# Find processes using port 8000
$portProcesses = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique

if ($portProcesses) {
    foreach ($pid in $portProcesses) {
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Found process: $($process.ProcessName) (PID: $pid)" -ForegroundColor Cyan
            Stop-Process -Id $pid -Force
            Write-Host "Process stopped successfully" -ForegroundColor Green
        }
    }
} else {
    Write-Host "No process found on port 8000. Server may already be stopped." -ForegroundColor Green
}

# Also check for Python processes running run_app_exe.py
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "`nFound Python processes. Checking for Local Brain server..." -ForegroundColor Cyan
    # Note: We can't easily check command line args in PowerShell without admin rights
    # So we'll just inform the user
    Write-Host "If server is still running, stop it manually with Ctrl+C in the terminal." -ForegroundColor Yellow
} else {
    Write-Host "`nNo Python processes found." -ForegroundColor Green
}

Write-Host "`nDone!" -ForegroundColor Green














