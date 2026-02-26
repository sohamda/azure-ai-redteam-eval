// app-service.bicep — App Service for hosting the FastAPI agent application

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string = resourceGroup().location

@description('Environment tag')
param environment string = 'dev'

@description('Managed identity resource ID')
param identityId string

@description('Azure OpenAI endpoint')
param openAIEndpoint string

@description('OpenAI deployment name')
param openAIDeployment string = 'gpt-4o'

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('AI Foundry project name')
param aiFoundryProject string

@description('AI Foundry endpoint')
param aiFoundryEndpoint string

// ---------------------------------------------------------------------------
// App Service Plan
// ---------------------------------------------------------------------------

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${baseName}-plan'
  location: location
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    SecurityControl: 'Ignore'
  }
  sku: {
    name: 'B2'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true // Linux
  }
}

// ---------------------------------------------------------------------------
// App Service
// ---------------------------------------------------------------------------

resource appService 'Microsoft.Web/sites@2023-12-01' = {
  name: '${baseName}-app'
  location: location
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    SecurityControl: 'Ignore'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'uvicorn src.app:app --host 0.0.0.0 --port 8000'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAIEndpoint }
        { name: 'AZURE_OPENAI_DEPLOYMENT', value: openAIDeployment }
        { name: 'AZURE_OPENAI_API_VERSION', value: '2024-12-01-preview' }
        { name: 'AZURE_AI_FOUNDRY_PROJECT', value: aiFoundryProject }
        { name: 'AZURE_AI_FOUNDRY_ENDPOINT', value: aiFoundryEndpoint }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'LOG_LEVEL', value: 'INFO' }
        { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
      ]
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------

@description('App Service default hostname')
output hostname string = appService.properties.defaultHostName

@description('App Service resource ID')
output appServiceId string = appService.id

@description('App Service name')
output appServiceName string = appService.name
