# ============================================
# Full server startup automation script
# Usage: .\start_server.ps1
# ============================================

param(
    [switch]$SkipEnvCheck,
    [switch]$SkipDeps
)

$ErrorActionPreference = "Stop"

# Налаштування кодування для коректного відображення кирилиці
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

function Write-Step {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "`n=== $Message ===" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Local Gemini Brain Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Step "Checking Python"
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python found: $pythonVersion"
    } else {
        throw "Python not found"
    }
} catch {
    Write-ErrorMsg "Python is not installed or not in PATH"
    Write-Host "Install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$VENV_DIR = ".venv"
$VENV_ACTIVATE = Join-Path $VENV_DIR "Scripts\Activate.ps1"
$VENV_PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"

Write-Step "Checking virtual environment"

if (-not (Test-Path $VENV_DIR)) {
    Write-Warning "Virtual environment not found. Creating..."
    python -m venv $VENV_DIR
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Failed to create virtual environment"
        exit 1
    }
    Write-Success "Virtual environment created: $VENV_DIR"
} else {
    Write-Success "Virtual environment found: $VENV_DIR"
}

Write-Step "Activating virtual environment"

if (-not (Test-Path $VENV_ACTIVATE)) {
    Write-ErrorMsg "Activation file not found: $VENV_ACTIVATE"
    exit 1
}

try {
    . $VENV_ACTIVATE
    Write-Success "Virtual environment activated"
} catch {
    Write-ErrorMsg "Failed to activate virtual environment: $_"
    exit 1
}

$currentPython = (Get-Command python).Source
if ($currentPython -notlike "*$VENV_DIR*") {
    Write-Warning "Warning: activation may have failed. Continuing..."
}

Write-Step "Updating pip"
& $VENV_PYTHON -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Success "pip updated"
} else {
    Write-Warning "Failed to update pip, continuing..."
}

if (-not $SkipDeps) {
    Write-Step "Checking dependencies"
    
    if (-not (Test-Path "requirements.txt")) {
        Write-ErrorMsg "requirements.txt file not found"
        exit 1
    }
    
    Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    & $VENV_PYTHON -m pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "All dependencies installed"
    } else {
        Write-ErrorMsg "Error installing dependencies"
        exit 1
    }
} else {
    Write-Warning "Skipping dependency installation (flag -SkipDeps)"
}

if (-not $SkipEnvCheck) {
    Write-Step "Checking configuration"
    
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found"
        Write-Host "Create .env file with GOOGLE_API_KEY variable" -ForegroundColor Yellow
        Write-Host "Example: GOOGLE_API_KEY=your_api_key_here" -ForegroundColor Gray
        
        $createEnv = Read-Host "Create empty .env file? (y/n)"
        if ($createEnv -eq 'y' -or $createEnv -eq 'Y') {
            "GOOGLE_API_KEY=" | Out-File -FilePath ".env" -Encoding UTF8
            Write-Success "Created .env file. Fill GOOGLE_API_KEY manually."
        }
    } else {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -match "GOOGLE_API_KEY\s*=") {
            Write-Success ".env file found and contains GOOGLE_API_KEY"
        } else {
            Write-Warning ".env file found, but GOOGLE_API_KEY is missing or empty"
        }
    }
}

Write-Step "Checking project files"

$requiredFiles = @("main.py", "archetypes.yaml")
$allFilesExist = $true

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Success "Found: $file"
    } else {
        Write-ErrorMsg "Not found: $file"
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-ErrorMsg "Required project files are missing"
    exit 1
}

Write-Step "Checking port 8000"

$portInUse = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Warning "Port 8000 is already in use"
    $portInUse | ForEach-Object {
        $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "  Process: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Yellow
        }
    }
    $continue = Read-Host "Continue? Server may not start (y/n)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        exit 0
    }
} else {
    Write-Success "Port 8000 is free"
}

Write-Step "Starting server"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Server starting..." -ForegroundColor Green
Write-Host "  Address: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

try {
    & $VENV_PYTHON -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
} catch {
    Write-ErrorMsg "Error starting server: $_"
    exit 1
}
