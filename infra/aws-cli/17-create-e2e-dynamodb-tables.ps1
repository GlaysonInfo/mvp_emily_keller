param(
    [string]$HistoryTable = $(if ($env:CONDITION_HISTORY_TABLE) { $env:CONDITION_HISTORY_TABLE } else { "condition_history" }),
    [string]$AlertsTable = $(if ($env:CONDITION_ALERTS_TABLE) { $env:CONDITION_ALERTS_TABLE } else { "condition_alerts" }),
    [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
    [string]$Profile = $env:AWS_PROFILE
)

function Invoke-Aws {
    param([string[]]$Arguments)

    if ($Profile) {
        & aws @Arguments --region $Region --profile $Profile
    }
    else {
        & aws @Arguments --region $Region
    }
}

function Test-TableExists {
    param([string]$TableName)

    Invoke-Aws @("dynamodb", "describe-table", "--table-name", $TableName) *> $null
    return $LASTEXITCODE -eq 0
}

Write-Host "Região AWS: $Region"
if ($Profile) { Write-Host "Profile AWS: $Profile" }

if (Test-TableExists -TableName $HistoryTable) {
    Write-Host "Tabela de histórico já existe: $HistoryTable"
}
else {
    Write-Host "Criando tabela de histórico: $HistoryTable"
    Invoke-Aws @(
        "dynamodb", "create-table",
        "--table-name", $HistoryTable,
        "--attribute-definitions",
        "AttributeName=tenant_asset,AttributeType=S",
        "AttributeName=ts_utc_minute,AttributeType=S",
        "--key-schema",
        "AttributeName=tenant_asset,KeyType=HASH",
        "AttributeName=ts_utc_minute,KeyType=RANGE",
        "--billing-mode", "PAY_PER_REQUEST"
    )
}

if (Test-TableExists -TableName $AlertsTable) {
    Write-Host "Tabela de alertas já existe: $AlertsTable"
}
else {
    Write-Host "Criando tabela de alertas: $AlertsTable"
    Invoke-Aws @(
        "dynamodb", "create-table",
        "--table-name", $AlertsTable,
        "--attribute-definitions",
        "AttributeName=tenant_asset,AttributeType=S",
        "AttributeName=alert_key,AttributeType=S",
        "--key-schema",
        "AttributeName=tenant_asset,KeyType=HASH",
        "AttributeName=alert_key,KeyType=RANGE",
        "--billing-mode", "PAY_PER_REQUEST"
    )
}
