#!/bin/bash
# ============================================================
# setup-azure.sh — Azure prerequisites bootstrap script
# ============================================================
# Run this ONCE before the first GitHub Actions deploy.
# Requires: az cli logged in with Owner or User Access Administrator
# on the target subscription.
#
# What it does:
#   1. Creates the resource group
#   2. Creates or reuses an App Registration + Service Principal
#   3. Adds federated credentials for GitHub Actions OIDC
#   4. Assigns RBAC roles (Contributor + User Access Administrator)
#      scoped to the resource group
#   5. Prints the GitHub secrets you need to configure
# ============================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID:-84b82c4c-ae43-4127-8cf6-ecd1c9466830}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-redteam-eval}"
LOCATION="${AZURE_LOCATION:-swedencentral}"
APP_REG_NAME="${APP_REG_NAME:-agent_eval_action}"
GITHUB_REPO="${GITHUB_REPO:-}"  # e.g., "myorg/azure-ai-redteam-eval"
# ──────────────────────────────────────────────────────────────

echo "============================================================"
echo "  Azure Prerequisites Setup — azure-ai-redteam-eval"
echo "============================================================"
echo ""

# Validate required input
if [ -z "$GITHUB_REPO" ]; then
  read -rp "GitHub repo (owner/name): " GITHUB_REPO
fi

echo "Subscription:  $SUBSCRIPTION_ID"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location:       $LOCATION"
echo "App Reg:        $APP_REG_NAME"
echo "GitHub Repo:    $GITHUB_REPO"
echo ""

# ── 1. Set subscription ──────────────────────────────────────
echo "→ Setting subscription..."
az account set --subscription "$SUBSCRIPTION_ID"

# ── 2. Create resource group ─────────────────────────────────
echo "→ Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --tags project=azure-ai-redteam-eval environment=dev SecurityControl=Ignore \
  --output none

# ── 3. Create or get App Registration ────────────────────────
echo "→ Looking up App Registration '$APP_REG_NAME'..."
APP_ID=$(az ad app list --display-name "$APP_REG_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)

if [ -z "$APP_ID" ]; then
  echo "  Creating new App Registration..."
  APP_ID=$(az ad app create --display-name "$APP_REG_NAME" --query appId -o tsv)
  echo "  Created: $APP_ID"
else
  echo "  Found existing: $APP_ID"
fi

# Ensure Service Principal exists
echo "→ Ensuring Service Principal exists..."
SP_OBJ_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv 2>/dev/null || true)
if [ -z "$SP_OBJ_ID" ]; then
  SP_OBJ_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
  echo "  Created SP: $SP_OBJ_ID"
else
  echo "  Found SP: $SP_OBJ_ID"
fi

# ── 4. Get Tenant ID ─────────────────────────────────────────
TENANT_ID=$(az account show --query tenantId -o tsv)
echo "→ Tenant ID: $TENANT_ID"

# ── 5. Add Federated Credentials for GitHub OIDC ─────────────
echo "→ Adding federated credentials for GitHub Actions..."

ISSUER="https://token.actions.githubusercontent.com"
AUDIENCE="api://AzureADTokenExchange"

# Credential for push to main
echo "  Adding credential: main branch..."
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters "{
    \"name\": \"github-main\",
    \"issuer\": \"$ISSUER\",
    \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
    \"audiences\": [\"$AUDIENCE\"],
    \"description\": \"GitHub Actions — push to main\"
  }" --output none 2>/dev/null || echo "  (already exists)"

# Credential for pull requests
echo "  Adding credential: pull requests..."
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters "{
    \"name\": \"github-pr\",
    \"issuer\": \"$ISSUER\",
    \"subject\": \"repo:${GITHUB_REPO}:pull_request\",
    \"audiences\": [\"$AUDIENCE\"],
    \"description\": \"GitHub Actions — pull requests\"
  }" --output none 2>/dev/null || echo "  (already exists)"

# Credential for environment: dev
echo "  Adding credential: dev environment..."
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters "{
    \"name\": \"github-env-dev\",
    \"issuer\": \"$ISSUER\",
    \"subject\": \"repo:${GITHUB_REPO}:environment:dev\",
    \"audiences\": [\"$AUDIENCE\"],
    \"description\": \"GitHub Actions — dev environment\"
  }" --output none 2>/dev/null || echo "  (already exists)"

# ── 6. RBAC Role Assignments (scoped to resource group) ──────
RG_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

echo "→ Assigning RBAC roles on '$RESOURCE_GROUP'..."

echo "  Contributor..."
az role assignment create \
  --assignee "$APP_ID" \
  --role "Contributor" \
  --scope "$RG_SCOPE" \
  --output none 2>/dev/null || echo "  (already assigned)"

echo "  User Access Administrator..."
az role assignment create \
  --assignee "$APP_ID" \
  --role "User Access Administrator" \
  --scope "$RG_SCOPE" \
  --output none 2>/dev/null || echo "  (already assigned)"

echo "  Cognitive Services OpenAI User..."
az role assignment create \
  --assignee "$APP_ID" \
  --role "Cognitive Services OpenAI User" \
  --scope "$RG_SCOPE" \
  --output none 2>/dev/null || echo "  (already assigned)"

echo "  Azure AI Developer..."
az role assignment create \
  --assignee "$APP_ID" \
  --role "Azure AI Developer" \
  --scope "$RG_SCOPE" \
  --output none 2>/dev/null || echo "  (already assigned)"

# ── 7. Purge soft-deleted resources (name reservations) ──────
# Key Vaults and Cognitive Services (Azure OpenAI) are soft-deleted on removal
# and keep their names reserved until purged. Bicep derives globally-unique
# names deterministically from the resource group, so a re-deploy regenerates
# the SAME name — any soft-deleted leftover will block it with
# "VaultAlreadyExists" / "FlagMustBeSetForRestore". Purge them first.
echo ""
echo "→ Checking for soft-deleted resources in '$LOCATION' that would block re-deploy..."

DELETED_VAULTS=$(az keyvault list-deleted \
  --query "[?properties.location=='${LOCATION}'].name" -o tsv 2>/dev/null || true)
DELETED_COG=$(az cognitiveservices account list-deleted \
  --query "[?location=='${LOCATION}'].{name:name,rg:resourceGroup}" -o tsv 2>/dev/null || true)

if [ -n "$DELETED_VAULTS" ] || [ -n "$DELETED_COG" ]; then
  echo "  Found soft-deleted resources:"
  [ -n "$DELETED_VAULTS" ] && echo "    Key Vaults:          $DELETED_VAULTS"
  [ -n "$DELETED_COG" ] && echo "    Cognitive Services:  $(echo "$DELETED_COG" | awk '{print $1}' | tr '\n' ' ')"
  read -rp "  Purge these now? (irreversible) (y/N): " PURGE_NOW
  if [[ "$PURGE_NOW" =~ ^[Yy]$ ]]; then
    for v in $DELETED_VAULTS; do
      echo "    Purging Key Vault '$v'..."
      az keyvault purge --name "$v" --location "$LOCATION" --output none 2>/dev/null \
        || echo "    (failed to purge '$v' — purge manually)"
    done
    # Cognitive Services purge needs name + resource group + location
    echo "$DELETED_COG" | while read -r cog_name cog_rg; do
      [ -z "$cog_name" ] && continue
      echo "    Purging Cognitive Services '$cog_name'..."
      az cognitiveservices account purge \
        --name "$cog_name" \
        --resource-group "$cog_rg" \
        --location "$LOCATION" --output none 2>/dev/null \
        || echo "    (failed to purge '$cog_name' — purge manually)"
    done
    echo "  Purge complete."
  else
    echo "  Skipped. Re-deploy may fail if a name is still reserved."
  fi
else
  echo "  None found."
fi

# ── 8. Deploy infrastructure (initial Bicep) ─────────────────
echo ""
read -rp "Deploy Bicep infrastructure now? (y/N): " DEPLOY_NOW
if [[ "$DEPLOY_NOW" =~ ^[Yy]$ ]]; then
  echo "→ Deploying Bicep..."
  az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file infra/main.bicep \
    --parameters infra/parameters/dev.bicepparam \
    --name "initial-setup-deploy" \
    --output json
  echo "  Deployment complete."
fi

# ── 9. Retrieve outputs for GitHub secrets ────────────────────
echo ""
echo "============================================================"
echo "  GitHub Secrets to configure"
echo "============================================================"
echo ""
echo "  AZURE_CLIENT_ID             = $APP_ID"
echo "  AZURE_TENANT_ID             = $TENANT_ID"
echo "  AZURE_SUBSCRIPTION_ID       = $SUBSCRIPTION_ID"
echo "  AZURE_RESOURCE_GROUP        = $RESOURCE_GROUP"

# Try to get deployment outputs — find the main deployment (has openAIEndpoint output)
DEPLOY_NAME=$(az deployment group list \
  --resource-group "$RESOURCE_GROUP" \
  --query "[?properties.outputs.openAIEndpoint != null] | [0].name" -o tsv 2>/dev/null)

if [ -n "$DEPLOY_NAME" ]; then
  echo "  Found deployment: $DEPLOY_NAME"
  OPENAI_ENDPOINT=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOY_NAME" \
    --query properties.outputs.openAIEndpoint.value -o tsv 2>/dev/null)
  AI_PROJECT=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOY_NAME" \
    --query properties.outputs.aiFoundryProject.value -o tsv 2>/dev/null)
  APPINSIGHTS_CS=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOY_NAME" \
    --query properties.outputs.appInsightsConnectionString.value -o tsv 2>/dev/null)
else
  OPENAI_ENDPOINT="<run Bicep deploy first>"
  AI_PROJECT="<run Bicep deploy first>"
  APPINSIGHTS_CS="<run Bicep deploy first>"
fi

echo "  AZURE_OPENAI_ENDPOINT       = $OPENAI_ENDPOINT"
echo "  AZURE_OPENAI_DEPLOYMENT     = gpt-4.1-mini"
echo "  AZURE_AI_FOUNDRY_PROJECT    = $AI_PROJECT"
echo "  AZURE_AI_FOUNDRY_ENDPOINT   = <from AI Foundry portal>"
echo "  APPLICATIONINSIGHTS_CONNECTION_STRING = $APPINSIGHTS_CS"
echo ""
echo "GitHub Variable:"
echo "  AZURE_LOCATION              = $LOCATION"
echo ""
echo "============================================================"
echo "  Done! Configure the above in GitHub → Settings → Secrets"
echo "============================================================"
