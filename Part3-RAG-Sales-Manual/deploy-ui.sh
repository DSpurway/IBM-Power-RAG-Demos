#!/bin/bash

echo "=========================================="
echo "Deploying Carbon RAG UI"
echo "=========================================="
echo ""

# Get current namespace
NAMESPACE=$(oc project -q)
echo "Current namespace: $NAMESPACE"

# Get backend URL
BACKEND_URL=$(oc get route rag-backend -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null)
if [ -z "$BACKEND_URL" ]; then
    echo "ERROR: rag-backend route not found!"
    echo "Creating backend route first..."
    cat <<EOF | oc apply -f -
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: rag-backend
  namespace: $NAMESPACE
  labels:
    app: rag-backend
spec:
  to:
    kind: Service
    name: rag-backend
  port:
    targetPort: 8080-tcp
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF
    BACKEND_URL=$(oc get route rag-backend -n $NAMESPACE -o jsonpath='{.spec.host}')
fi

echo "Backend URL: https://$BACKEND_URL"
echo ""

# Deploy the UI
echo "Creating carbon-rag-ui deployment..."
cat <<EOF | oc apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: carbon-rag-ui
  namespace: $NAMESPACE
  labels:
    app: carbon-rag-ui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: carbon-rag-ui
  template:
    metadata:
      labels:
        app: carbon-rag-ui
    spec:
      containers:
      - name: carbon-rag-ui
        image: image-registry.openshift-image-registry.svc:5000/$NAMESPACE/carbon-rag-ui:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 3000
          protocol: TCP
        env:
        - name: NEXT_PUBLIC_RAG_BACKEND_URL
          value: "https://$BACKEND_URL"
        - name: NODE_ENV
          value: "production"
        - name: NEXT_TELEMETRY_DISABLED
          value: "1"
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
EOF

echo ""
echo "Creating carbon-rag-ui service..."
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Service
metadata:
  name: carbon-rag-ui
  namespace: $NAMESPACE
  labels:
    app: carbon-rag-ui
spec:
  type: ClusterIP
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
    name: http
  selector:
    app: carbon-rag-ui
EOF

echo ""
echo "Creating carbon-rag-ui route..."
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
echo "Waiting for deployment to be ready..."
oc rollout status deployment/carbon-rag-ui --timeout=5m

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo ""

# Get UI URL
UI_URL=$(oc get route carbon-rag-ui -n $NAMESPACE -o jsonpath='{.spec.host}')
echo "Carbon RAG UI: https://$UI_URL"
echo "Backend API:   https://$BACKEND_URL"
echo ""

# Check pod status
echo "Pod status:"
oc get pods -l app=carbon-rag-ui -n $NAMESPACE

# Made with Bob
