param(
    [string]$HostAddress = $env:CONDITION_API_HOST,
    [int]$Port = 0,
    [switch]$Reload
)

if (-not $HostAddress) { $HostAddress = "127.0.0.1" }
if (-not $Port) {
    if ($env:CONDITION_API_PORT) { $Port = [int]$env:CONDITION_API_PORT }
    else { $Port = 8001 }
}

$env:AWS_DEFAULT_REGION = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }

if (-not $env:DYNAMODB_STATE_TABLE) { $env:DYNAMODB_STATE_TABLE = "mvp_asset_state_dev" }
if (-not $env:CONDITION_HISTORY_TABLE) { $env:CONDITION_HISTORY_TABLE = "condition_history" }
if (-not $env:CONDITION_ALERTS_TABLE) { $env:CONDITION_ALERTS_TABLE = "condition_alerts" }

Write-Host "Regiao AWS:" $env:AWS_DEFAULT_REGION
Write-Host "DYNAMODB_STATE_TABLE:" $env:DYNAMODB_STATE_TABLE
Write-Host "CONDITION_HISTORY_TABLE:" $env:CONDITION_HISTORY_TABLE
Write-Host "CONDITION_ALERTS_TABLE:" $env:CONDITION_ALERTS_TABLE
Write-Host "API:" "http://$HostAddress`:$Port"

$Args = @("src.api.condition_ingest_api:app", "--host", $HostAddress, "--port", "$Port")
if ($Reload) {
    $Args += "--reload"
}

python -m uvicorn @Args
