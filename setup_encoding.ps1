# Script for setting up UTF-8 encoding in PowerShell
# Usage: .\setup_encoding.ps1
# Or add these commands to your PowerShell profile

Write-Host "Setting up encoding for correct Cyrillic display..." -ForegroundColor Cyan

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Change code page to UTF-8
chcp 65001 | Out-Null

Write-Host "[OK] Encoding set to UTF-8" -ForegroundColor Green
Write-Host ""
Write-Host "Cyrillic should now display correctly!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Note: These settings apply only to the current PowerShell session." -ForegroundColor Gray
Write-Host "For permanent setup, add these commands to PowerShell profile." -ForegroundColor Gray
