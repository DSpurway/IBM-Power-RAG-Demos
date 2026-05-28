#!/bin/bash

echo "=========================================="
echo "Carbon RAG UI Deployment Status"
echo "=========================================="
echo ""

# Check if deployment exists
echo "1. Checking if deployment exists..."
oc get deployment carbon-rag-ui -n rag-demo 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: carbon-rag-ui deployment not found!"
    echo ""
    echo "Available deployments:"
    oc get deployments -n rag-demo
    exit 1
fi

echo ""
echo "2. Checking pod status..."
oc get pods -l app=carbon-rag-ui -n rag-demo

echo ""
echo "3. Checking deployment details..."
oc describe deployment carbon-rag-ui -n rag-demo

echo ""
echo "4. Checking service..."
oc get service carbon-rag-ui -n rag-demo

echo ""
echo "5. Checking route..."
oc get route carbon-rag-ui -n rag-demo

echo ""
echo "6. Checking build status..."
oc get builds -l buildconfig=carbon-rag-ui -n rag-demo

echo ""
echo "7. Checking image stream..."
oc get imagestream carbon-rag-ui -n rag-demo 2>/dev/null

echo ""
echo "8. If pod exists, checking logs..."
POD=$(oc get pod -l app=carbon-rag-ui -n rag-demo -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$POD" ]; then
    echo "Pod name: $POD"
    echo ""
    echo "Recent logs:"
    oc logs $POD -n rag-demo --tail=50
else
    echo "No pod found for carbon-rag-ui"
    echo ""
    echo "Checking deployment events:"
    oc get events -n rag-demo --sort-by='.lastTimestamp' | grep carbon-rag-ui | tail -20
fi

echo ""
echo "=========================================="
echo "Diagnosis Complete"
echo "=========================================="

# Made with Bob
