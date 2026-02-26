// ai-foundry.bicep — Azure AI Foundry hub + project
// Powers the evaluation SDK and model management

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string = resourceGroup().location

@description('Environment tag')
param environment string = 'dev'

@description('Application Insights resource ID')
param appInsightsId string

@description('Key Vault resource ID')
param keyVaultId string

@description('Storage account ID for the hub')
param storageAccountId string = ''

@description('Managed identity principal ID for RBAC')
param identityPrincipalId string

// ---------------------------------------------------------------------------
// AI Foundry Hub
// ---------------------------------------------------------------------------

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: '${baseName}-aihub'
  location: location
  kind: 'Hub'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    SecurityControl: 'Ignore'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: '${baseName} AI Hub'
    description: 'AI Foundry Hub for Continuous Evaluation & Monitoring demo'
    keyVault: keyVaultId
    applicationInsights: appInsightsId
    publicNetworkAccess: 'Enabled'
  }
}

// ---------------------------------------------------------------------------
// AI Foundry Project
// ---------------------------------------------------------------------------

resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: '${baseName}-aiproject'
  location: location
  kind: 'Project'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    SecurityControl: 'Ignore'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: '${baseName} AI Project'
    description: 'AI Foundry Project for CE/CM evaluations'
    hubResourceId: aiHub.id
    publicNetworkAccess: 'Enabled'
  }
}

// RBAC: Azure AI Developer for the managed identity
resource aiDeveloperRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, identityPrincipalId, 'Azure AI Developer')
  scope: aiProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalId: identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('AI Foundry Hub ID')
output hubId string = aiHub.id

@description('AI Foundry Project ID')
output projectId string = aiProject.id

@description('AI Foundry Project name')
output projectName string = aiProject.name

@description('AI Foundry endpoint')
output endpoint string = aiHub.properties.discoveryUrl
