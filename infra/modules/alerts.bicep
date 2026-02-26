// alerts.bicep — Azure Monitor alert rules for CE/CM
// Deployed as IaC to ensure alerts are version-controlled

@description('Base name for resources')
param baseName string

@description('Azure region')
param location string = resourceGroup().location

@description('Environment tag')
param environment string = 'dev'

@description('Application Insights resource ID')
param appInsightsId string

@description('Action group ID for alert notifications (optional)')
param actionGroupId string = ''

// ---------------------------------------------------------------------------
// CE Alert: Groundedness Score Drop
// ---------------------------------------------------------------------------

resource groundednessAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${baseName}-ce-groundedness-drop'
  location: 'global'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    category: 'CE'
    SecurityControl: 'Ignore'
  }
  properties: {
    description: 'Groundedness evaluation score dropped below threshold'
    severity: 1
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'GroundednessScoreDrop'
          metricName: 'ce.score.groundedness'
          metricNamespace: 'azure.applicationinsights'
          operator: 'LessThan'
          threshold: 4
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
          skipMetricValidation: true
        }
      ]
    }
    autoMitigate: true
    actions: actionGroupId != '' ? [{ actionGroupId: actionGroupId }] : []
  }
}

// ---------------------------------------------------------------------------
// CE Alert: Safety Score Violation
// ---------------------------------------------------------------------------

resource safetyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${baseName}-ce-safety-violation'
  location: 'global'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    category: 'CE'
    SecurityControl: 'Ignore'
  }
  properties: {
    description: 'Safety evaluation score dropped below critical threshold'
    severity: 0 // Critical
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'SafetyScoreDrop'
          metricName: 'ce.score.safety'
          metricNamespace: 'azure.applicationinsights'
          operator: 'LessThan'
          threshold: 5
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
          skipMetricValidation: true
        }
      ]
    }
    autoMitigate: true
    actions: actionGroupId != '' ? [{ actionGroupId: actionGroupId }] : []
  }
}

// ---------------------------------------------------------------------------
// CM Alert: Agent Latency P99
// ---------------------------------------------------------------------------

resource latencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${baseName}-cm-agent-latency'
  location: 'global'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    category: 'CM'
    SecurityControl: 'Ignore'
  }
  properties: {
    description: 'Agent P99 latency exceeded threshold (5s)'
    severity: 2
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'AgentLatencyHigh'
          metricName: 'agent.request.duration'
          metricNamespace: 'azure.applicationinsights'
          operator: 'GreaterThan'
          threshold: 5000
          timeAggregation: 'Maximum'
          criterionType: 'StaticThresholdCriterion'
          skipMetricValidation: true
        }
      ]
    }
    autoMitigate: true
    actions: actionGroupId != '' ? [{ actionGroupId: actionGroupId }] : []
  }
}

// ---------------------------------------------------------------------------
// CM Alert: Agent Error Rate
// ---------------------------------------------------------------------------

resource errorRateAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${baseName}-cm-agent-errors'
  location: 'global'
  tags: {
    project: 'azure-ai-redteam-eval'
    environment: environment
    category: 'CM'
    SecurityControl: 'Ignore'
  }
  properties: {
    description: 'Agent error count exceeded threshold'
    severity: 1
    enabled: true
    scopes: [appInsightsId]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'AgentErrorRate'
          metricName: 'agent.error.count'
          metricNamespace: 'azure.applicationinsights'
          operator: 'GreaterThan'
          threshold: 10
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
          skipMetricValidation: true
        }
      ]
    }
    autoMitigate: true
    actions: actionGroupId != '' ? [{ actionGroupId: actionGroupId }] : []
  }
}
