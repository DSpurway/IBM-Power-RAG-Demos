# Activation Features UI Component - Implementation Guide

## Overview

This document provides the complete React component for displaying activation features with a list + detail view, allowing users to compare LLM-generated descriptions with raw Sales Manual chunks.

## Component File

Create: `Part3-RAG-Sales-Manual/carbon-rag-ui/src/components/ActivationFeaturesView/ActivationFeaturesView.js`

```javascript
'use client';
import React, { useState } from 'react';
import {
  Grid,
  Column,
  Tile,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListRow,
  StructuredListCell,
  StructuredListBody,
  Tag,
} from '@carbon/react';
import { Checkmark, WarningAlt } from '@carbon/icons-react';
import './ActivationFeaturesView.scss';

export default function ActivationFeaturesView({ features, serverModel }) {
  const [selectedFeature, setSelectedFeature] = useState(
    features && features.length > 0 ? features[0] : null
  );

  if (!features || features.length === 0) {
    return (
      <Tile>
        <p>No activation features found for this server.</p>
      </Tile>
    );
  }

  // Categorize features
  const processorFeatures = features.filter(f => 
    f.description.toLowerCase().includes('processor') || 
    f.description.toLowerCase().includes('proc') ||
    f.description.toLowerCase().includes('core')
  );
  
  const memoryFeatures = features.filter(f => 
    f.description.toLowerCase().includes('memory') || 
    f.description.toLowerCase().includes('ram') ||
    f.description.toLowerCase().includes('gb')
  );
  
  const otherFeatures = features.filter(f => 
    !processorFeatures.includes(f) && !memoryFeatures.includes(f)
  );

  const renderFeatureList = (featureList, title) => {
    if (featureList.length === 0) return null;
    
    return (
      <>
        <h5 className="feature-category-title">{title}</h5>
        {featureList.map((feature) => (
          <StructuredListRow
            key={feature.feature_code}
            onClick={() => setSelectedFeature(feature)}
            className={`feature-list-row ${
              selectedFeature?.feature_code === feature.feature_code ? 'selected' : ''
            }`}
          >
            <StructuredListCell>
              <strong>#{feature.feature_code}</strong>
            </StructuredListCell>
            <StructuredListCell>
              <div className="feature-description">
                {feature.description.length > 60 
                  ? feature.description.substring(0, 60) + '...' 
                  : feature.description}
              </div>
            </StructuredListCell>
            <StructuredListCell>
              {feature.is_available ? (
                <Tag type="green" renderIcon={Checkmark}>
                  Available
                </Tag>
              ) : (
                <Tag type="red" renderIcon={WarningAlt}>
                  Discontinued
                </Tag>
              )}
            </StructuredListCell>
          </StructuredListRow>
        ))}
      </>
    );
  };

  return (
    <div className="activation-features-container">
      <Grid fullWidth>
        <Column lg={16}>
          <h3>Activation Features for {serverModel}</h3>
          <p className="feature-summary">
            Found {features.length} activation feature(s): {' '}
            {features.filter(f => f.is_available).length} available, {' '}
            {features.filter(f => !f.is_available).length} discontinued
          </p>
        </Column>
      </Grid>

      <Grid fullWidth className="features-grid">
        {/* Left Panel: Feature List */}
        <Column lg={8} md={8} sm={4}>
          <Tile className="feature-list-tile">
            <h4>Features ({features.length})</h4>
            <p className="list-instructions">
              Click a feature to view full Sales Manual details
            </p>
            
            <StructuredListWrapper>
              <StructuredListHead>
                <StructuredListRow head>
                  <StructuredListCell head>Code</StructuredListCell>
                  <StructuredListCell head>Description</StructuredListCell>
                  <StructuredListCell head>Status</StructuredListCell>
                </StructuredListRow>
              </StructuredListHead>
              <StructuredListBody>
                {renderFeatureList(processorFeatures, 'Processor Activations')}
                {renderFeatureList(memoryFeatures, 'Memory Activations')}
                {renderFeatureList(otherFeatures, 'Other Activations')}
              </StructuredListBody>
            </StructuredListWrapper>
          </Tile>
        </Column>

        {/* Right Panel: Feature Details */}
        <Column lg={8} md={8} sm={4}>
          <Tile className="feature-detail-tile">
            {selectedFeature ? (
              <>
                <div className="detail-header">
                  <h4>Feature #{selectedFeature.feature_code}</h4>
                  {selectedFeature.is_available ? (
                    <Tag type="green" renderIcon={Checkmark}>
                      Available
                    </Tag>
                  ) : (
                    <Tag type="red" renderIcon={WarningAlt}>
                      Discontinued {selectedFeature.discontinued_date && 
                        `(${selectedFeature.discontinued_date})`}
                    </Tag>
                  )}
                </div>

                <div className="detail-section">
                  <h5>Description</h5>
                  <p className="feature-description-full">
                    {selectedFeature.description}
                  </p>
                </div>

                <div className="detail-section">
                  <h5>Sales Manual Content</h5>
                  <div className="chunk-text-container">
                    <pre className="chunk-text">
                      {selectedFeature.chunk_text || 'No detailed content available'}
                    </pre>
                  </div>
                </div>

                {selectedFeature.metadata?.source_url && (
                  <div className="detail-section">
                    <h5>Source</h5>
                    <a 
                      href={selectedFeature.metadata.source_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="source-link"
                    >
                      View in IBM Sales Manual →
                    </a>
                  </div>
                )}
              </>
            ) : (
              <p>Select a feature from the list to view details</p>
            )}
          </Tile>
        </Column>
      </Grid>
    </div>
  );
}
```

## Stylesheet

Create: `Part3-RAG-Sales-Manual/carbon-rag-ui/src/components/ActivationFeaturesView/ActivationFeaturesView.scss`

```scss
.activation-features-container {
  margin-top: 2rem;

  .feature-summary {
    margin-bottom: 1rem;
    color: #525252;
  }

  .features-grid {
    margin-top: 1rem;
  }

  .feature-list-tile,
  .feature-detail-tile {
    height: 600px;
    overflow-y: auto;
  }

  .list-instructions {
    font-size: 0.875rem;
    color: #525252;
    margin-bottom: 1rem;
  }

  .feature-category-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: #161616;
    margin: 1rem 0 0.5rem 0;
    padding: 0.5rem;
    background-color: #f4f4f4;
  }

  .feature-list-row {
    cursor: pointer;
    transition: background-color 0.2s;

    &:hover {
      background-color: #e0e0e0;
    }

    &.selected {
      background-color: #d0e2ff;
      border-left: 3px solid #0f62fe;
    }
  }

  .feature-description {
    font-size: 0.875rem;
    line-height: 1.4;
  }

  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e0e0e0;

    h4 {
      margin: 0;
    }
  }

  .detail-section {
    margin-bottom: 1.5rem;

    h5 {
      font-size: 0.875rem;
      font-weight: 600;
      color: #161616;
      margin-bottom: 0.5rem;
    }
  }

  .feature-description-full {
    font-size: 1rem;
    line-height: 1.5;
    color: #161616;
    padding: 1rem;
    background-color: #f4f4f4;
    border-radius: 4px;
  }

  .chunk-text-container {
    background-color: #f4f4f4;
    border-radius: 4px;
    padding: 1rem;
    max-height: 400px;
    overflow-y: auto;
  }

  .chunk-text {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
    margin: 0;
    color: #161616;
  }

  .source-link {
    color: #0f62fe;
    text-decoration: none;
    font-size: 0.875rem;

    &:hover {
      text-decoration: underline;
    }
  }
}
```

## Integration with Sales Manual Page

In `Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js`, add the import and render the component when activation features are detected:

```javascript
// Add to imports at top
import ActivationFeaturesView from '../../components/ActivationFeaturesView/ActivationFeaturesView';

// In the query results rendering section (around line 400-500), add:
{queryResults && queryResults.query_type === 'activation_lookup' && queryResults.features && (
  <ActivationFeaturesView 
    features={queryResults.features}
    serverModel={selectedServer?.model || 'Unknown Server'}
  />
)}
```

## Component Directory Structure

```
Part3-RAG-Sales-Manual/carbon-rag-ui/src/components/
└── ActivationFeaturesView/
    ├── ActivationFeaturesView.js
    ├── ActivationFeaturesView.scss
    └── index.js  (optional - for cleaner imports)
```

Optional `index.js`:
```javascript
export { default } from './ActivationFeaturesView';
```

## Features

1. **Two-Panel Layout**
   - Left: Scrollable list of features grouped by category
   - Right: Detailed view of selected feature

2. **Feature Categorization**
   - Processor Activations
   - Memory Activations
   - Other Activations

3. **Visual Indicators**
   - Green tag for available features
   - Red tag for discontinued features
   - Selected row highlighting

4. **Detail View Shows**
   - Feature code and status
   - Clean description (LLM or manual)
   - Full Sales Manual chunk text
   - Link to source documentation

5. **Responsive Design**
   - Uses Carbon Grid system
   - Adapts to different screen sizes

## Testing

1. Deploy backend with `chunk_text` support
2. Add the component files
3. Integrate into sales manual page
4. Query: "What activations are available for the E1080?"
5. Verify:
   - Features appear in list
   - Clicking a feature shows details
   - Chunk text is readable
   - Status tags are correct

## Benefits

- **Compare LLM vs Manual**: See description vs raw chunk side-by-side
- **No Additional API Calls**: All data in initial response
- **Fast**: No waiting for detail view
- **User-Friendly**: Click to explore, clear visual hierarchy

## Next Steps

1. Create the component files
2. Add to sales manual page
3. Test with activation queries
4. Evaluate if LLM descriptions add value
5. Optionally implement streaming (see STREAMING_ACTIVATION_FEATURES.md)