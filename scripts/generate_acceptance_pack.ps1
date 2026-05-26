
if (-not (Test-Path "reports\acceptance")) {
  New-Item -ItemType Directory -Path "reports\acceptance" | Out-Null
}

python scripts\validate_acceptance_config.py
python scripts\export_lubrication_acceptance_report.py

Write-Host "Pacote de aceite gerado em reports\acceptance"
