# PowerShell script for building exe file
# Usage: .\build_exe.ps1

Write-Host "=== Building Local Brain exe file ===" -ForegroundColor Green

# Check for PyInstaller
Write-Host "`n[1/5] Checking PyInstaller..." -ForegroundColor Yellow
try {
    $pyinstallerVersion = pyinstaller --version
    Write-Host "PyInstaller installed: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error installing PyInstaller!" -ForegroundColor Red
        exit 1
    }
}

# Clean previous builds
Write-Host "`n[2/5] Cleaning previous builds..." -ForegroundColor Yellow
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "Build folder deleted" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "Dist folder deleted" -ForegroundColor Green
}

# Check for required files
Write-Host "`n[3/5] Checking files..." -ForegroundColor Yellow
if (-not (Test-Path "run_app_exe.py")) {
    Write-Host "Error: run_app_exe.py not found!" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "run_app.spec")) {
    Write-Host "Error: run_app.spec not found!" -ForegroundColor Red
    exit 1
}
Write-Host "All required files found" -ForegroundColor Green

# Build exe
Write-Host "`n[4/5] Building exe file (this may take a few minutes)..." -ForegroundColor Yellow
pyinstaller run_app.spec --clean --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build error!" -ForegroundColor Red
    exit 1
}

# Check result
Write-Host "`n[5/5] Checking result..." -ForegroundColor Yellow
$exePath = "dist\LocalBrain.exe"
if (Test-Path $exePath) {
    $fileSize = (Get-Item $exePath).Length / 1MB
    Write-Host "`n=== Success! ===" -ForegroundColor Green
    Write-Host "Exe file created: $exePath" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Copy dist\LocalBrain.exe to a separate folder" -ForegroundColor White
    Write-Host "2. Create .env file with AI_PROVIDER=google_ai (or openai) and API keys" -ForegroundColor White
    Write-Host "3. Run LocalBrain.exe" -ForegroundColor White
} else {
    Write-Host "Error: exe file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "`nDone!" -ForegroundColor Green
