# Activation Feature Detail View

## Concept

**List View (Left):** Show clean, concise activation feature descriptions
**Detail View (Right):** Show full Sales Manual chunk when user clicks a feature

This approach:
- ✅ Avoids LLM timeout (no processing needed for detail view)
- ✅ Gives users full context when they need it
- ✅ Fast initial response (just show list)
- ✅ No additional backend calls (data already in response)

## Backend Changes (Complete)

### Change Made

**File:** `activation_feature_service.py` (line 37-47)

Added `chunk_text` to the JSON response:

```python
def to_dict(self) -> Dict:
    """Convert to dictionary for JSON serialization"""
    return {
        'feature_code': self.feature_code,
        'description': self.description,
        'discontinued_date': self.discontinued_date,
        'is_available': self.is_available,
        'status': self.status,
        'metadata': self.metadata,
        'chunk_text': self.chunk_text  # Full Sales Manual text for detail view
    }
```

### API Response Structure

```json
{
  "success": true,
  "query_type": "activation_lookup",
  "features": [
    {
      "feature_code": "EDAR",
      "description": "512 GB Base Memory activation (Pools 2.0) from Static",
      "discontinued_date": null,
      "is_available": true,
      "status": "Available",
      "metadata": {
        "source": "sales_manual",
        "source_url": "https://www.ibm.com/docs/..."
      },
      "chunk_text": "(#EDAR) 512 GB Base Memory activation (Pools 2.0) from Static\n\nEach occurrence of this feature will permanently activate...\n\n– Attributes provided: 512 GB base memory\n– Attributes required: #EHC9\n– Minimum required: 0\n– Maximum allowed: 16\n..."
    }
  ]
}
```

## Frontend Implementation (Carbon UI)

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Activation Features for IBM Power E1080                    │
├──────────────────────────┬──────────────────────────────────┤
│  Feature List            │  Feature Details                 │
│                          │                                  │
│  ☑ #EDAR                 │  (#EDAR) 512 GB Base Memory     │
│    512 GB Base Memory... │  activation (Pools 2.0)         │
│                          │                                  │
│  ☐ #EMAC                 │  Each occurrence of this        │
│    512 GB Memory...      │  feature will permanently       │
│                          │  activate 512 GB of base        │
│  ☐ #EDP2                 │  memory...                      │
│    1 core Processor...   │                                  │
│                          │  – Attributes provided:         │
│  ☐ #EDP4                 │    512 GB base memory           │
│    Activation for 2.0... │                                  │
│                          │  – Attributes required:         │
│                          │    #EHC9 with inactive memory   │
│                          │                                  │
│                          │  – Minimum required: 0          │
│                          │  – Maximum allowed: 16          │
│                          │                                  │
│                          │  Note: Feature EDAR not         │
│                          │  orderable in China             │
└──────────────────────────┴──────────────────────────────────┘
```

### React Component Structure

```typescript
// ActivationFeaturesView.tsx
import { useState } from 'react';
import { Tile, StructuredListWrapper, StructuredListHead, 
         StructuredListRow, StructuredListCell, StructuredListBody } from '@carbon/react';

interface ActivationFeature {
  feature_code: string;
  description: string;
  is_available: boolean;
  status: string;
  chunk_text: string;
  discontinued_date?: string;
}

export const ActivationFeaturesView = ({ features }: { features: ActivationFeature[] }) => {
  const [selectedFeature, setSelectedFeature] = useState<ActivationFeature | null>(
    features.length > 0 ? features[0] : null
  );

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', height: '600px' }}>
      {/* Left: Feature List */}
      <Tile style={{ overflow: 'auto' }}>
        <h4>Activation Features ({features.length})</h4>
        <StructuredListWrapper>
          <StructuredListHead>
            <StructuredListRow head>
              <StructuredListCell head>Feature Code</StructuredListCell>
              <StructuredListCell head>Description</StructuredListCell>
              <StructuredListCell head>Status</StructuredListCell>
            </StructuredListRow>
          </StructuredListHead>
          <StructuredListBody>
            {features.map((feature) => (
              <StructuredListRow
                key={feature.feature_code}
                onClick={() => setSelectedFeature(feature)}
                style={{
                  cursor: 'pointer',
                  backgroundColor: selectedFeature?.feature_code === feature.feature_code 
                    ? '#e0e0e0' 
                    : 'transparent'
                }}
              >
                <StructuredListCell>
                  <strong>#{feature.feature_code}</strong>
                </StructuredListCell>
                <StructuredListCell>
                  {feature.description.substring(0, 50)}...
                </StructuredListCell>
                <StructuredListCell>
                  <span style={{ 
                    color: feature.is_available ? 'green' : 'red',
                    fontWeight: 'bold'
                  }}>
                    {feature.status}
                  </span>
                </StructuredListCell>
              </StructuredListRow>
            ))}
          </StructuredListBody>
        </StructuredListWrapper>
      </Tile>

      {/* Right: Feature Details */}
      <Tile style={{ overflow: 'auto' }}>
        {selectedFeature ? (
          <>
            <h4>Feature #{selectedFeature.feature_code}</h4>
            <p><strong>Status:</strong> {selectedFeature.status}</p>
            <hr />
            <pre style={{ 
              whiteSpace: 'pre-wrap', 
              fontFamily: 'monospace',
              fontSize: '0.9rem',
              lineHeight: '1.5'
            }}>
              {selectedFeature.chunk_text}
            </pre>
          </>
        ) : (
          <p>Select a feature to view details</p>
        )}
      </Tile>
    </div>
  );
};
```

### Integration with Existing Code

In your existing activation query handler:

```typescript
// When you receive the response
if (response.query_type === 'activation_lookup' && response.features) {
  return <ActivationFeaturesView features={response.features} />;
}
```

## Benefits

1. **No Timeout** - Detail view uses data already in response
2. **Fast Initial Load** - Just show list with descriptions
3. **Full Context** - Users can see complete Sales Manual text
4. **No LLM Needed** - Manual extraction for list is fast and clean
5. **Better UX** - Users choose what details they want to see

## Deployment

### Backend
```powershell
cd Part3-RAG-Sales-Manual\rag-backend
oc start-build rag-backend --from-dir=. --follow
oc rollout restart deployment/rag-backend
```

### Frontend
Update your Carbon UI component to use the new `ActivationFeaturesView` component.

## Testing

```powershell
# Test API response includes chunk_text
$BACKEND_URL = oc get route rag-backend -o jsonpath='{.spec.host}'
$body = @{
    question = "What activations are available?"
    collection_name = "rag_36d5fcdd8f17c37ef0f739637cde0718"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "https://$BACKEND_URL/api/search" -Method Post -Body $body -ContentType "application/json" -SkipCertificateCheck

# Check first feature has chunk_text
$response.features[0].chunk_text
```

## Future Enhancements

1. **Syntax Highlighting** - Format the chunk text with proper styling
2. **Collapsible Sections** - Collapse "Attributes required" section by default
3. **Copy to Clipboard** - Button to copy feature details
4. **Link to Sales Manual** - Direct link to source page
5. **Compare Features** - Select multiple features to compare side-by-side

## Decision on LLM

With this approach, you can:
- **Disable LLM entirely** (`use_llm_descriptions=False`) for fast, reliable list view
- **Or keep LLM** (`max_llm_calls=1`) if you want one enhanced description
- **Users get full context** in detail view regardless

The detail view solves the "not enough information" problem without needing LLM processing.