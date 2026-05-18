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

// Made with Bob
