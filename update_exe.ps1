# PowerShell script for safe EXE update
# Usage: .\update_exe.ps1 -NewExePath "C:\path\to\new\LocalBrain.exe"

param(
    [Parameter(Mandatory=$true)]
    [string]$NewExePath,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBackup
)

Write-Host "=== Оновлення LocalBrain EXE ===" -ForegroundColor Green
Write-Host ""

# Перевірка, чи існує новий EXE
if (-not (Test-Path $NewExePath)) {
    Write-Host "Помилка: Новий EXE файл не знайдено: $NewExePath" -ForegroundColor Red
    exit 1
}

# Перевірка, чи запущений старий EXE
Write-Host "[1/5] Перевірка поточного процесу..." -ForegroundColor Yellow
$process = Get-Process -Name "LocalBrain" -ErrorAction SilentlyContinue
if ($process) {
    Write-Host "  Зупинка поточного процесу..." -ForegroundColor Yellow
    Stop-Process -Name "LocalBrain" -Force
    Start-Sleep -Seconds 2
    Write-Host "  Процес зупинено" -ForegroundColor Green
} else {
    Write-Host "  Процес не запущений" -ForegroundColor Green
}

# Створення резервної копії
if (-not $SkipBackup) {
    Write-Host ""
    Write-Host "[2/5] Створення резервної копії..." -ForegroundColor Yellow
    $backupDir = "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Host "  Резервна копія: $backupDir" -ForegroundColor Cyan
    
    # Копіювання папок з даними
    $dataFolders = @("history", "vector_db_storage", "prompts", "logs")
    foreach ($folder in $dataFolders) {
        if (Test-Path $folder) {
            Copy-Item -Path $folder -Destination "$backupDir\$folder" -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  - Скопійовано: $folder" -ForegroundColor Gray
        }
    }
    
    # Копіювання файлів з даними
    $dataFiles = @(".env", "archetypes.yaml", "config.yaml")
    foreach ($file in $dataFiles) {
        if (Test-Path $file) {
            Copy-Item -Path $file -Destination "$backupDir\$file" -Force -ErrorAction SilentlyContinue
            Write-Host "  - Скопійовано: $file" -ForegroundColor Gray
        }
    }
    
    Write-Host "  Резервна копія створена успішно" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[2/5] Пропущено створення резервної копії (--SkipBackup)" -ForegroundColor Yellow
}

# Перевірка поточного EXE
Write-Host ""
Write-Host "[3/5] Перевірка поточного EXE..." -ForegroundColor Yellow
if (Test-Path "LocalBrain.exe") {
    $oldSize = (Get-Item "LocalBrain.exe").Length / 1MB
    Write-Host "  Поточний EXE: $([math]::Round($oldSize, 2)) MB" -ForegroundColor Gray
} else {
    Write-Host "  Поточний EXE не знайдено (перша установка)" -ForegroundColor Gray
}

# Перевірка нового EXE
$newSize = (Get-Item $NewExePath).Length / 1MB
Write-Host "  Новий EXE: $([math]::Round($newSize, 2)) MB" -ForegroundColor Gray

# Заміна EXE
Write-Host ""
Write-Host "[4/5] Заміна EXE файлу..." -ForegroundColor Yellow
if (Test-Path "LocalBrain.exe") {
    Remove-Item "LocalBrain.exe" -Force
    Write-Host "  Старий EXE видалено" -ForegroundColor Gray
}
Copy-Item -Path $NewExePath -Destination "LocalBrain.exe" -Force
Write-Host "  Новий EXE скопійовано" -ForegroundColor Green

# Перевірка даних
Write-Host ""
Write-Host "[5/5] Перевірка даних..." -ForegroundColor Yellow
$dataExists = $false
if (Test-Path "history") {
    $historyCount = (Get-ChildItem -Path "history" -Filter "*.json" -ErrorAction SilentlyContinue).Count
    Write-Host "  Історія: $historyCount файлів" -ForegroundColor Gray
    $dataExists = $true
}
if (Test-Path "vector_db_storage") {
    Write-Host "  Векторна база: існує" -ForegroundColor Gray
    $dataExists = $true
}
if (Test-Path ".env") {
    Write-Host "  Налаштування: існує" -ForegroundColor Gray
    $dataExists = $true
}
if (Test-Path "archetypes.yaml") {
    Write-Host "  Архетипи: існує" -ForegroundColor Gray
    $dataExists = $true
}

if (-not $dataExists) {
    Write-Host "  Попередження: Дані не знайдено (можливо, перша установка)" -ForegroundColor Yellow
}

# Підсумок
Write-Host ""
Write-Host "=== Оновлення завершено! ===" -ForegroundColor Green
if (-not $SkipBackup) {
    Write-Host "Резервна копія створена в: $backupDir" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "Наступні кроки:" -ForegroundColor Cyan
Write-Host "1. Запустіть LocalBrain.exe" -ForegroundColor White
Write-Host "2. Перевірте історію чатів" -ForegroundColor White
Write-Host "3. Перевірте векторну базу даних" -ForegroundColor White
Write-Host "4. Перевірте налаштування" -ForegroundColor White
Write-Host ""




