param(
    [string]$HostAddress = $env:GREASE_API_HOST,
    [int]$Port = 0,
    [switch]$Reload
)

if (-not $HostAddress) { $HostAddress = "127.0.0.1" }
if (-not $Port) {
    if ($env:GREASE_API_PORT) { $Port = [int]$env:GREASE_API_PORT }
    else { $Port = 8000 }
}

$env:AWS_DEFAULT_REGION = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }

if (-not $env:GREASE_STATE_TABLE) { $env:GREASE_STATE_TABLE = "grease_lubrication_state" }
if (-not $env:GREASE_CYCLES_TABLE) { $env:GREASE_CYCLES_TABLE = "grease_lubrication_cycles" }
if (-not $env:CONDITION_ALERTS_TABLE) { $env:CONDITION_ALERTS_TABLE = "condition_alerts" }
if (-not $env:LUBRICATION_CONFIG_PATH) { $env:LUBRICATION_CONFIG_PATH = "config/lubrication_pilot_config.json" }

Write-Host "Regiao AWS:" $env:AWS_DEFAULT_REGION
Write-Host "GREASE_STATE_TABLE:" $env:GREASE_STATE_TABLE
Write-Host "GREASE_CYCLES_TABLE:" $env:GREASE_CYCLES_TABLE
Write-Host "CONDITION_ALERTS_TABLE:" $env:CONDITION_ALERTS_TABLE
Write-Host "LUBRICATION_CONFIG_PATH:" $env:LUBRICATION_CONFIG_PATH
Write-Host "API:" "http://$HostAddress`:$Port"

$Args = @("src.api.grease_ingest_api:app", "--host", $HostAddress, "--port", "$Port")
if ($Reload) {
    $Args += "--reload"
}

python -m uvicorn @Args
