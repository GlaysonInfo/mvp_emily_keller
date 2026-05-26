param(
    [string]$Region = $env:AWS_DEFAULT_REGION
)

if (-not $Region) {
    $Region = $env:AWS_REGION
}

if (-not $Region) {
    $Region = "us-east-1"
}

function Ensure-DynamoTable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$TableName,

        [Parameter(Mandatory = $true)]
        [string[]]$AttributeDefinitions,

        [Parameter(Mandatory = $true)]
        [string[]]$KeySchema
    )

    $null = aws dynamodb describe-table --table-name $TableName --region $Region 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tabela ja existe: $TableName"
        return
    }

    Write-Host "Criando tabela: $TableName"
    aws dynamodb create-table `
        --table-name $TableName `
        --attribute-definitions $AttributeDefinitions `
        --key-schema $KeySchema `
        --billing-mode PAY_PER_REQUEST `
        --region $Region

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar a tabela $TableName na regiao $Region."
    }

    aws dynamodb wait table-exists --table-name $TableName --region $Region

    if ($LASTEXITCODE -ne 0) {
        throw "A tabela $TableName nao ficou disponivel na regiao $Region."
    }

    Write-Host "Tabela pronta: $TableName"
}

Ensure-DynamoTable `
    -TableName "grease_lubrication_state" `
    -AttributeDefinitions @("AttributeName=tenant_id,AttributeType=S", "AttributeName=asset_id,AttributeType=S") `
    -KeySchema @("AttributeName=tenant_id,KeyType=HASH", "AttributeName=asset_id,KeyType=RANGE")

Ensure-DynamoTable `
    -TableName "grease_lubrication_cycles" `
    -AttributeDefinitions @("AttributeName=tenant_asset,AttributeType=S", "AttributeName=cycle_timestamp,AttributeType=S") `
    -KeySchema @("AttributeName=tenant_asset,KeyType=HASH", "AttributeName=cycle_timestamp,KeyType=RANGE")
