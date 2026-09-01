// Azure Container Apps deployment for the SQLite build of the Pokedex API.
//
// Scale-to-zero: with no traffic the app costs nothing, and Container Apps'
// monthly free grant (180k vCPU-seconds + 360k GiB-seconds) covers a low-
// traffic read-only API outright. There is no database resource because the
// SQLite file ships inside the image.

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Name of the container app; also used as a prefix for its environment.')
param appName string = 'pokedex-api'

@description('Fully qualified image reference, e.g. myreg.azurecr.io/pokedex-api:2026-07-18.')
param containerImage string

@description('Container registry login server. Leave empty for a public image.')
param registryServer string = ''

@description('Registry username. Ignored when registryServer is empty.')
param registryUsername string = ''

@description('Registry password. Ignored when registryServer is empty.')
@secure()
param registryPassword string = ''

@description('Port the container listens on. Matches PORT_HTTP in the Dockerfile.')
param targetPort int = 158

@description('Upper bound on replicas. Scale-to-zero means the floor is always 0.')
@minValue(1)
@maxValue(10)
param maxReplicas int = 2

@description('Custom domain to serve on, e.g. poke-api.duocore.dev. Set this on every deploy — it drives the DNS record outputs even before the domain is bound.')
param customDomain string = ''

@description('''
Whether to issue the managed TLS certificate and bind the custom domain.
Leave false on the first deploy: certificate issuance is validated via CNAME,
so DNS must already point at this app before it can succeed. Deploy once with
false, create the two records from the outputs, then deploy again with true.
''')
param bindCustomDomain bool = false

@description('''
den-den-mushi hub HTTP ingest URL, e.g. https://logs.example.dev. The app runs
on Container Apps where no fleet forwarder can see it, so it ships logs to the
hub over HTTP. Empty (default) disables shipping — the app still logs to stdout,
visible via `az containerapp logs show`.
''')
param dendenHubUrl string = ''

@description('Basic-auth username for the den-den hub. Ignored when dendenHubUrl is empty.')
param dendenHubUser string = ''

@description('Basic-auth password for the den-den hub. Ignored when dendenHubUrl is empty.')
@secure()
param dendenHubPassword string = ''

var usesPrivateRegistry = !empty(registryServer)
var shipsLogs = !empty(dendenHubUrl)
var bindDomain = !empty(customDomain) && bindCustomDomain
var certName = replace(customDomain, '.', '-')

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
  location: location
  // No appLogsConfiguration: skipping the Log Analytics workspace keeps this
  // free. `az containerapp logs show --follow` still streams live logs; they
  // just aren't retained. Add a workspace here if you need history.
  properties: {}
}

// Azure-managed TLS certificate: free, auto-renewing, and validated by the
// CNAME that already has to exist for the domain to route here. Creation fails
// if DNS is not yet pointing at the app, which is why binding is a second pass.
resource cert 'Microsoft.App/managedEnvironments/managedCertificates@2024-03-01' = if (bindDomain) {
  parent: env
  name: certName
  location: location
  properties: {
    subjectName: customDomain
    domainControlValidation: 'CNAME'
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        // Container Apps terminates TLS at ingress and redirects HTTP to
        // HTTPS, which is why the container itself runs with TLS_CERT=off.
        allowInsecure: false
        customDomains: bindDomain ? [
          {
            name: customDomain
            bindingType: 'SniEnabled'
            certificateId: cert.id
          }
        ] : []
      }
      registries: usesPrivateRegistry ? [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ] : []
      secrets: concat(
        usesPrivateRegistry ? [
          {
            name: 'registry-password'
            value: registryPassword
          }
        ] : [],
        (shipsLogs && !empty(dendenHubPassword)) ? [
          {
            name: 'denden-hub-password'
            value: dendenHubPassword
          }
        ] : []
      )
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(
            [
              // Container Apps terminates TLS at ingress, so the container
              // serves plain HTTP on targetPort.
              {
                name: 'TLS_CERT'
                value: 'off'
              }
              {
                name: 'PORT_HTTP'
                value: string(targetPort)
              }
            ],
            shipsLogs ? [
              {
                name: 'DENDEN_HUB_HTTP'
                value: dendenHubUrl
              }
              {
                name: 'DENDEN_HUB_USER'
                value: dendenHubUser
              }
            ] : [],
            (shipsLogs && !empty(dendenHubPassword)) ? [
              {
                name: 'DENDEN_HUB_PASSWORD'
                secretRef: 'denden-hub-password'
              }
            ] : []
          )
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: targetPort
              }
              initialDelaySeconds: 3
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz'
                port: targetPort
              }
              initialDelaySeconds: 1
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
output apiUrl string = bindDomain
  ? 'https://${customDomain}'
  : 'https://${app.properties.configuration.ingress.fqdn}'

// The two records the managed certificate validates against. Both are emitted
// as soon as customDomain is set, so the first (unbound) deploy already tells
// you exactly what to create. Names are full FQDNs — if your DNS provider
// wants a name relative to the zone, drop the zone suffix.
output dnsCnameRecord string = empty(customDomain)
  ? '(set customDomain to emit this)'
  : '${customDomain}  CNAME  ${app.properties.configuration.ingress.fqdn}'
output dnsTxtRecord string = empty(customDomain)
  ? '(set customDomain to emit this)'
  : 'asuid.${customDomain}  TXT  ${app.properties.customDomainVerificationId}'
output customDomainVerificationId string = app.properties.customDomainVerificationId
output domainBound bool = bindDomain
