# ============================================================
# setup-azure.ps1 — Azure prerequisites bootstrap script
# ============================================================
# Run this ONCE before the first GitHub Actions deploy.
# Requires: az cli logged in with Owner or User Access Administrator
# on the target subscription.
#
# Usage:
#   .\scripts\setup-azure.ps1 -GitHubRepo "myorg/azure-ai-redteam-eval"
#
# What it does:
#   1. Creates the resource group
#   2. Creates or reuses an App Registration + Service Principal
#   3. Adds federated credentials for GitHub Actions OIDC
#   4. Assigns RBAC roles scoped to the resource group
#   5. Optionally deploys Bicep infrastructure
#   6. Prints the GitHub secrets you need to configure
# ============================================================

param(
    [string]$SubscriptionId = "3b250d66-c6d7-48ff-b78e-351fa7f7a8eb",
    [string]$ResourceGroup = "rg-miniconf",
    [string]$Location = "swedencentral",
    [string]$AppRegName = "agent_eval_action",
    [Parameter(Mandatory = $true)]
    [string]$GitHubRepo  # e.g., "myorg/azure-ai-redteam-eval"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Azure Prerequisites Setup - azure-ai-redteam-eval" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Subscription:   $SubscriptionId"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location:       $Location"
Write-Host "App Reg:        $AppRegName"
Write-Host "GitHub Repo:    $GitHubRepo"
Write-Host ""

# ── 1. Set subscription ──────────────────────────────────────
Write-Host "-> Setting subscription..." -ForegroundColor Yellow
az account set --subscription $SubscriptionId

# ── 2. Create resource group ─────────────────────────────────
Write-Host "-> Creating resource group '$ResourceGroup' in '$Location'..." -ForegroundColor Yellow
az group create `
    --name $ResourceGroup `
    --location $Location `
    --tags project=azure-ai-redteam-eval environment=dev SecurityControl=Ignore `
    --output none

# ── 3. Create or get App Registration ────────────────────────
Write-Host "-> Looking up App Registration '$AppRegName'..." -ForegroundColor Yellow
$AppId = az ad app list --display-name $AppRegName --query "[0].appId" -o tsv 2>$null

if ([string]::IsNullOrEmpty($AppId)) {
    Write-Host "  Creating new App Registration..." -ForegroundColor Gray
    $AppId = az ad app create --display-name $AppRegName --query appId -o tsv
    Write-Host "  Created: $AppId" -ForegroundColor Green
}
else {
    Write-Host "  Found existing: $AppId" -ForegroundColor Green
}

# Ensure Service Principal exists
Write-Host "-> Ensuring Service Principal exists..." -ForegroundColor Yellow
$SpObjId = az ad sp show --id $AppId --query id -o tsv 2>$null
if ([string]::IsNullOrEmpty($SpObjId)) {
    $SpObjId = az ad sp create --id $AppId --query id -o tsv
    Write-Host "  Created SP: $SpObjId" -ForegroundColor Green
}
else {
    Write-Host "  Found SP: $SpObjId" -ForegroundColor Green
}

# ── 4. Get Tenant ID ─────────────────────────────────────────
$TenantId = az account show --query tenantId -o tsv
Write-Host "-> Tenant ID: $TenantId" -ForegroundColor Yellow

# ── 5. Add Federated Credentials for GitHub OIDC ─────────────
Write-Host "-> Adding federated credentials for GitHub Actions..." -ForegroundColor Yellow

$Issuer = "https://token.actions.githubusercontent.com"
$Audience = "api://AzureADTokenExchange"

$credentials = @(
    @{ name = "github-main";    subject = "repo:${GitHubRepo}:ref:refs/heads/main"; desc = "push to main" }
    @{ name = "github-pr";      subject = "repo:${GitHubRepo}:pull_request";        desc = "pull requests" }
    @{ name = "github-env-dev"; subject = "repo:${GitHubRepo}:environment:dev";     desc = "dev environment" }
)

foreach ($cred in $credentials) {
    Write-Host "  Adding credential: $($cred.desc)..." -ForegroundColor Gray
    $params = @{
        name        = $cred.name
        issuer      = $Issuer
        subject     = $cred.subject
        audiences   = @($Audience)
        description = "GitHub Actions - $($cred.desc)"
    } | ConvertTo-Json -Compress

    try {
        az ad app federated-credential create --id $AppId --parameters $params --output none 2>$null
    }
    catch {
        Write-Host "    (already exists)" -ForegroundColor DarkGray
    }
}

# ── 6. RBAC Role Assignments (scoped to resource group) ──────
$RgScope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"

Write-Host "-> Assigning RBAC roles on '$ResourceGroup'..." -ForegroundColor Yellow

$roles = @(
    "Contributor",
    "User Access Administrator",
    "Cognitive Services OpenAI User",
    "Azure AI Developer"
)

foreach ($role in $roles) {
    Write-Host "  $role..." -ForegroundColor Gray
    az role assignment create `
        --assignee $AppId `
        --role $role `
        --scope $RgScope `
        --output none 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    (already assigned)" -ForegroundColor DarkGray
    }
}

# ── 7. Optionally deploy infrastructure ──────────────────────
Write-Host ""
$deployNow = Read-Host "Deploy Bicep infrastructure now? (y/N)"
if ($deployNow -eq "y" -or $deployNow -eq "Y") {
    Write-Host "-> Deploying Bicep..." -ForegroundColor Yellow
    az deployment group create `
        --resource-group $ResourceGroup `
        --template-file infra/main.bicep `
        --parameters infra/parameters/dev.bicepparam `
        --name "initial-setup-deploy"
    Write-Host "  Deployment complete." -ForegroundColor Green
}

# ── 8. Retrieve outputs for GitHub secrets ────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  GitHub Secrets to configure" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Try to retrieve from the main Bicep deployment (has openAIEndpoint output)
$deployName = az deployment group list `
    --resource-group $ResourceGroup `
    --query "[?properties.outputs.openAIEndpoint != null] | [0].name" -o tsv 2>$null

$openaiEndpoint = "<run Bicep deploy first>"
$aiProject = "<run Bicep deploy first>"
$appInsightsCs = "<run Bicep deploy first>"

if (-not [string]::IsNullOrEmpty($deployName)) {
    Write-Host "  Found deployment: $deployName" -ForegroundColor Gray
    $openaiEndpoint = az deployment group show `
        --resource-group $ResourceGroup `
        --name $deployName `
        --query "properties.outputs.openAIEndpoint.value" -o tsv 2>$null
    $aiProject = az deployment group show `
        --resource-group $ResourceGroup `
        --name $deployName `
        --query "properties.outputs.aiFoundryProject.value" -o tsv 2>$null
    $appInsightsCs = az deployment group show `
        --resource-group $ResourceGroup `
        --name $deployName `
        --query "properties.outputs.appInsightsConnectionString.value" -o tsv 2>$null
}

Write-Host "  AZURE_CLIENT_ID                      = $AppId" -ForegroundColor White
Write-Host "  AZURE_TENANT_ID                      = $TenantId" -ForegroundColor White
Write-Host "  AZURE_SUBSCRIPTION_ID                = $SubscriptionId" -ForegroundColor White
Write-Host "  AZURE_RESOURCE_GROUP                 = $ResourceGroup" -ForegroundColor White
Write-Host "  AZURE_OPENAI_ENDPOINT                = $openaiEndpoint" -ForegroundColor White
Write-Host "  AZURE_OPENAI_DEPLOYMENT              = gpt-4o" -ForegroundColor White
Write-Host "  AZURE_AI_FOUNDRY_PROJECT             = $aiProject" -ForegroundColor White
Write-Host "  AZURE_AI_FOUNDRY_ENDPOINT            = <from AI Foundry portal>" -ForegroundColor White
Write-Host "  APPLICATIONINSIGHTS_CONNECTION_STRING = $appInsightsCs" -ForegroundColor White
Write-Host ""
Write-Host "GitHub Variable:" -ForegroundColor Cyan
Write-Host "  AZURE_LOCATION                       = $Location" -ForegroundColor White
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Done! Configure the above in GitHub -> Settings -> Secrets" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
