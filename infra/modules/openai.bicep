// openai.bicep — Azure OpenAI resource + GPT-4o model deployment

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string = resourceGroup().location

@description('Environment tag')
param environment string = 'dev'

@description('OpenAI model deployment name')
param modelDeploymentName string = 'gpt-4o'

@description('OpenAI model version')
param modelVersion string = '2024-08-06'

@description('Model capacity (tokens per minute in thousands)')
param capacityTPM int = 30

@description('Managed identity principal ID for RBAC')
param identityPrincipalId string

// ---------------------------------------------------------------------------
// Azure OpenAI
// ---------------------------------------------------------------------------

resource openAI 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${baseName}-openai'
  location: location
  kind: 'OpenAI'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    SecurityControl: 'Ignore'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: '${baseName}-openai'
    publicNetworkAccess: 'Enabled'
  }
}

// GPT-4o model deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAI
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: capacityTPM
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: modelVersion
    }
  }
}

// RBAC: Cognitive Services OpenAI User for the managed identity
resource openAIUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAI.id, identityPrincipalId, 'Cognitive Services OpenAI User')
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: identityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('Azure OpenAI endpoint')
output endpoint string = openAI.properties.endpoint

@description('Azure OpenAI resource ID')
output openAIId string = openAI.id

@description('Model deployment name')
output deploymentName string = gpt4oDeployment.name
