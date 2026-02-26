// main.bicep — Orchestrator for all infrastructure modules
// Deploys the complete CE/CM demo environment

targetScope = 'resourceGroup'

@description('Base name prefix for all resources')
param baseName string

@description('Azure region')
param location string = resourceGroup().location

@description('Environment (dev or prod)')
@allowed(['dev', 'prod'])
param environment string = 'dev'

@description('OpenAI model deployment name')
param modelDeploymentName string = 'gpt-4o'

@description('OpenAI model capacity (TPM in thousands)')
param modelCapacityTPM int = 30

// ---------------------------------------------------------------------------
// Module: Managed Identity
// ---------------------------------------------------------------------------

module identity 'modules/managed-identity.bicep' = {
  name: 'identity-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
  }
}

// ---------------------------------------------------------------------------
// Module: Monitoring (must deploy before AI Foundry — it needs App Insights ID)
// ---------------------------------------------------------------------------

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
  }
}

// ---------------------------------------------------------------------------
// Module: Key Vault
// ---------------------------------------------------------------------------

module keyVault 'modules/key-vault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
    identityPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------------
// Module: Azure OpenAI
// ---------------------------------------------------------------------------

module openAI 'modules/openai.bicep' = {
  name: 'openai-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
    modelDeploymentName: modelDeploymentName
    capacityTPM: modelCapacityTPM
    identityPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------------
// Module: AI Foundry Hub + Project
// ---------------------------------------------------------------------------

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'aifoundry-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
    appInsightsId: monitoring.outputs.appInsightsId
    keyVaultId: keyVault.outputs.keyVaultId
    identityPrincipalId: identity.outputs.principalId
  }
}

// ---------------------------------------------------------------------------
// Module: App Service
// ---------------------------------------------------------------------------

module appService 'modules/app-service.bicep' = {
  name: 'appservice-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
    identityId: identity.outputs.identityId
    openAIEndpoint: openAI.outputs.endpoint
    openAIDeployment: modelDeploymentName
    appInsightsConnectionString: monitoring.outputs.connectionString
    aiFoundryProject: aiFoundry.outputs.projectName
    aiFoundryEndpoint: aiFoundry.outputs.endpoint
  }
}

// ---------------------------------------------------------------------------
// Module: Alert Rules
// ---------------------------------------------------------------------------

module alerts 'modules/alerts.bicep' = {
  name: 'alerts-deployment'
  params: {
    baseName: baseName
    location: location
    environment: environment
    appInsightsId: monitoring.outputs.appInsightsId
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('App Service hostname')
output appHostname string = appService.outputs.hostname

@description('Azure OpenAI endpoint')
output openAIEndpoint string = openAI.outputs.endpoint

@description('AI Foundry project name')
output aiFoundryProject string = aiFoundry.outputs.projectName

@description('App Insights connection string')
output appInsightsConnectionString string = monitoring.outputs.connectionString

@description('Key Vault URI')
output keyVaultUri string = keyVault.outputs.keyVaultUri
