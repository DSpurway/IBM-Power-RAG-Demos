#!/bin/bash
# Git commands to sync Carbon alignment improvements to GitHub

echo "=== Syncing Carbon Alignment Improvements to GitHub ==="
echo ""

# Navigate to the repository root
cd /c/Users/029878866/EMEA-AI-SQUAD/RAG-with-Notebook

# Check current status
echo "1. Checking git status..."
git status

echo ""
echo "2. Adding new and modified files..."
# Add the new files
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/_mixins.scss
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/_overrides.scss
git add Part3-RAG-Sales-Manual/carbon-rag-ui/CARBON_ALIGNMENT_IMPROVEMENTS.md

# Add modified files
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/_sales-manual-page.scss
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js

echo ""
echo "3. Committing changes..."
git commit -m "feat: Align RAG UI with Carbon Design System standards

- Add shared styling architecture (_mixins.scss, _overrides.scss)
- Improve layout structure with proper Grid nesting
- Add negative margins for full-bleed sections
- Update spacing to match Carbon spacing scale
- Enhance typography with Carbon type styles
- Add AILabel component for AI-generated content presentation
- Improve answer section styling with better readability
- Add comprehensive documentation of improvements

Based on Carbon GenAI Demos best practices."

echo ""
echo "4. Pushing to GitHub..."
git push origin main

echo ""
echo "=== Sync Complete ==="
echo ""
echo "Next steps:"
echo "1. Verify changes on GitHub"
echo "2. Rebuild frontend in OCP cluster"
echo "3. Test the improved UI"

# Made with Bob
