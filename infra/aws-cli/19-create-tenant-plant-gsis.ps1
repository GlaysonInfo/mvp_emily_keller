param(
    [string]$StateTable = $env:DYNAMODB_STATE_TABLE,
    [string]$AlertsTable = $(if ($env:CONDITION_ALERTS_TABLE) { $env:CONDITION_ALERTS_TABLE } else { $env:ALERTS_TABLE }),
    [string]$IndexName = $(if ($env:STATE_TENANT_PLANT_INDEX) { $env:STATE_TENANT_PLANT_INDEX } else { "tenant_plant_index" })
)

$ErrorActionPreference = "Stop"

if (-not $StateTable) {
    $StateTable = "mvp_asset_state_dev"
}
if (-not $AlertsTable) {
    $AlertsTable = "condition_alerts"
}

function Ensure-Gsi {
    param(
        [string]$TableName,
        [string]$GsiName
    )

    $description = aws dynamodb describe-table --table-name $TableName | ConvertFrom-Json
    $existing = @($description.Table.GlobalSecondaryIndexes | Where-Object { $_.IndexName -eq $GsiName })
    if ($existing.Count -gt 0) {
        Write-Host "GSI '$GsiName' ja existe em '$TableName'."
        return
    }

    Write-Host "Criando GSI '$GsiName' em '$TableName'..."
    aws dynamodb update-table `
        --table-name $TableName `
        --attribute-definitions AttributeName=tenant_plant,AttributeType=S `
        --global-secondary-index-updates "[{`"Create`":{`"IndexName`":`"$GsiName`",`"KeySchema`":[{`"AttributeName`":`"tenant_plant`",`"KeyType`":`"HASH`"}],`"Projection`":{`"ProjectionType`":`"ALL`"}}}]" | Out-Null

    aws dynamodb wait table-exists --table-name $TableName
    Write-Host "Solicitacao enviada. Aguarde o backfill do indice ficar ACTIVE no DynamoDB."
}

Ensure-Gsi -TableName $StateTable -GsiName $IndexName
Ensure-Gsi -TableName $AlertsTable -GsiName $IndexName
