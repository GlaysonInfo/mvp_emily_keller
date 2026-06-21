param(
  [string]$OutputDir = "build/greengrass/component",
  [string]$ConfigPath = "config/ethernet_apl_greengrass_condition_config.example.json"
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path "."
$stage = Join-Path $OutputDir "sentinela-condition-apl"
$zip = Join-Path $OutputDir "sentinela-condition-apl.zip"

if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force $stage | Out-Null
New-Item -ItemType Directory -Force (Join-Path $stage "config") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $stage "src\edge\condition_bridge_field") | Out-Null

Copy-Item $ConfigPath (Join-Path $stage "config\ethernet_apl_greengrass_condition_config.json")
Copy-Item "src\edge\condition_bridge_field\*.py" (Join-Path $stage "src\edge\condition_bridge_field")
Copy-Item "src\edge\condition_bridge_field\sample_ethernet_apl_response.json" (Join-Path $stage "src\edge\condition_bridge_field")

if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $stage -DestinationPath $zip
Write-Host "Pacote criado: $zip"
Write-Host "Receita: deploy/greengrass/sentinela-condition-apl/recipe.yaml"
