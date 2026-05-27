# Watson Assistant Setup Guide

This guide explains how to configure Watson Assistant credentials for the RAG backend.

## Quick Setup (For New Environments)

When setting up a new TechZone environment or rebuilding from scratch:

### 1. Create the Secret

The Watson Assistant credentials are stored locally in `watson-assistant-credentials.yaml` (not in GitHub for security).

```bash
cd Part3-RAG-Sales-Manual/rag-backend
oc apply -f watson-assistant-credentials.yaml
```

### 2. Deploy the Backend

The deployment YAML is already configured to use the secret:

```bash
oc apply -f rag-backend-deploy.yaml
```

### 3. Verify Watson Assistant is Working

```bash
oc logs -f deployment/rag-backend | grep -i watson
```

You should see:
- `INFO:watson_assistant_service:Watson Assistant service initialized at https://...`
- `INFO:query_classifier:Watson Assistant enabled for query classification`

## Credential File Location

- **Local file (not in Git):** `watson-assistant-credentials.yaml`
- **Protected by:** `.gitignore` entry

## What the Deployment Does

The `rag-backend-deploy.yaml` file automatically:
1. References the `watson-assistant-credentials` secret
2. Maps the secret keys to environment variables:
   - `api-key` → `WATSON_ASSISTANT_API_KEY`
   - `url` → `WATSON_ASSISTANT_URL`
   - `assistant-id` → `WATSON_ASSISTANT_ID`

## Troubleshooting

If you see warnings like:
```
WARNING:watson_assistant_service:Watson Assistant not configured. API key or URL missing.
```

Check that:
1. The secret exists: `oc get secret watson-assistant-credentials`
2. The deployment has the environment variables: `oc get deployment rag-backend -o yaml | grep -A 20 WATSON_ASSISTANT`
3. The pod has restarted after applying the deployment

## Backup Your Credentials

Keep a local copy of `watson-assistant-credentials.yaml` in a secure location outside the Git repository. You'll need it when setting up new TechZone environments.

## Security Note

Never commit `watson-assistant-credentials.yaml` to GitHub. It contains sensitive API keys.