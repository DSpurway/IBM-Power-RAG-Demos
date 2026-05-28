#!/bin/bash

echo "=========================================="
echo "Fixing Routes Configuration"
echo "=========================================="
echo ""

# Check current namespace
NAMESPACE=$(oc project -q)
echo "Current namespace: $NAMESPACE"
echo ""

# Step 1: Create the frontend route if it doesn't exist
echo "Step 1: Creating carbon-rag-ui route..."
cat <<EOF | oc apply -f -
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: carbon-rag-ui
  namespace: $NAMESPACE
  labels:
    app: carbon-rag-ui
  annotations:
    haproxy.router.openshift.io/timeout: 60s
spec:
  to:
    kind: Service
    name: carbon-rag-ui
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF

echo ""
echo "Step 2: Removing unnecessary backend route..."
oc delete route rag-backend --ignore-not-found=true

echo ""
echo "Step 3: Removing unnecessary granite-service route..."
oc delete route granite-service --ignore-not-found=true

echo ""
echo "=========================================="
echo "Routes Configuration Complete"
echo "=========================================="
echo ""

# Display current routes
echo "Current routes in namespace $NAMESPACE:"
oc get routes

echo ""
echo "=========================================="
echo "Frontend URL"
echo "=========================================="
UI_URL=$(oc get route carbon-rag-ui -o jsonpath='{.spec.host}' 2>/dev/null)
if [ -n "$UI_URL" ]; then
    echo "Carbon RAG UI: https://$UI_URL"
else
    echo "Warning: carbon-rag-ui route not found"
fi
echo ""

# Made with Bob
