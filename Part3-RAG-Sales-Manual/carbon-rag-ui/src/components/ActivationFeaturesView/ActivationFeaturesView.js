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
        {featureList.map((feature) => {
          const isSelected = selectedFeature?.feature_code === feature.feature_code;
          return (
            <StructuredListRow
              key={feature.feature_code}
              className={`feature-list-row ${isSelected ? 'selected' : ''}`}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setSelectedFeature(feature);
                }
              }}
            >
              <StructuredListCell onClick={() => setSelectedFeature(feature)}>
                <strong>#{feature.feature_code}</strong>
              </StructuredListCell>
              <StructuredListCell onClick={() => setSelectedFeature(feature)}>
                <div className="feature-description">
                  {feature.description && feature.description.length > 60
                    ? feature.description.substring(0, 60) + '...'
                    : feature.description || 'No description'}
                </div>
              </StructuredListCell>
              <StructuredListCell onClick={() => setSelectedFeature(feature)}>
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
          );
        })}
      </>
    );
  };

  return (
    <div className="activation-features-container">
      <Grid fullWidth>
        <Column lg={16}>
          <h3>Activation Features for {serverModel}</h3>
          <p className="feature-summary">
            Found {processorFeatures.length + memoryFeatures.length} activation feature(s): {' '}
            {[...processorFeatures, ...memoryFeatures].filter(f => f.is_available).length} available, {' '}
            {[...processorFeatures, ...memoryFeatures].filter(f => !f.is_available).length} discontinued
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
                {/* Hide "Other Activations" - only show processor and memory */}
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
                    {selectedFeature.chunk_text ? (
                      <pre className="chunk-text">
                        {selectedFeature.chunk_text}
                      </pre>
                    ) : (
                      <div className="no-content-message">
                        <p>No detailed content available</p>
                        <p style={{ fontSize: '0.75rem', color: '#888', marginTop: '0.5rem' }}>
                          Debug: chunk_text field is {typeof selectedFeature.chunk_text === 'undefined' ? 'undefined' : 'empty'}
                        </p>
                        <p style={{ fontSize: '0.75rem', color: '#888' }}>
                          Available fields: {Object.keys(selectedFeature).join(', ')}
                        </p>
                      </div>
                    )}
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

// Made with Bob
