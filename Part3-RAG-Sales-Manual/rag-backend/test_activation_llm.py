#!/usr/bin/env python3
"""
Test script for LLM-enhanced activation feature descriptions
Tests the new LLM integration in activation_feature_service.py
"""

import sys
import logging
from activation_feature_service import ActivationFeatureService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample chunk texts from Sales Manual (examples of messy data)
SAMPLE_CHUNKS = [
    {
        'text': """(#EDAR) -512 GB Base Memory activation (Pools 2.0) from Static Feature EDAR not orderable in China
(#EDAS) -500 GB Base Memory activation (Pools 2.0) from Static Feature EDAS not orderable in China
(#EDAT) -1 GB Base Memory activation (Pools 2.0) MES only Feature EDAT not orderable in China

Attributes provided: Memory activation for Pools 2.0 systems""",
        'metadata': {'source': 'test'}
    },
    {
        'text': """(#EDPB) 1 core Processor Activation for #EDP2
(#EDPC) 1 core Processor Activation for #EDP3
(#EDPD) 1 core Processor Activation for #EDP4

These processor activations enable additional cores on Power10 systems.
Compatible with Capacity on Demand and Pools 2.0.

Attributes provided: Processor activation""",
        'metadata': {'source': 'test'}
    },
    {
        'text': """Feature Code: #EMAC
Name: 512 GB Memory Activation for #EHC9 no cost

This feature provides memory activation for HEX systems.
No longer available as of March 15, 2024

Attributes provided: Memory activation (discontinued)""",
        'metadata': {'source': 'test'}
    },
    {
        'text': """(#ELCP) 1 core Processor activation for #EHC9 no cost
(#ELCQ) Power Linux processor activation for #EDP3 Feature EME4 not orderable in China.
(#EP2Y) 1 core Mobile Processor Activation
(#EPDC) 1 core Base Processor Activation (Pools 2.0) for EDP2 any OS Feature EPDC not orderable in China

Attributes provided: Various processor activations for different systems""",
        'metadata': {'source': 'test'}
    }
]


def test_llm_descriptions():
    """Test LLM-based description generation"""
    print("\n" + "="*80)
    print("Testing LLM-Enhanced Activation Feature Descriptions")
    print("="*80 + "\n")
    
    # Test with LLM enabled
    print("1. Testing with LLM enabled:")
    print("-" * 80)
    service_with_llm = ActivationFeatureService(use_llm_descriptions=True)
    
    features_with_llm = service_with_llm.extract_features_from_chunks(SAMPLE_CHUNKS)
    
    if features_with_llm:
        print(f"\nExtracted {len(features_with_llm)} features with LLM descriptions:\n")
        for feature in features_with_llm:
            print(f"  #{feature.feature_code}")
            print(f"    Description: {feature.description}")
            print(f"    Status: {feature.status}")
            print()
    else:
        print("  ⚠️  No features extracted (LLM may be unavailable)")
    
    # Test with LLM disabled (fallback)
    print("\n2. Testing with LLM disabled (manual extraction):")
    print("-" * 80)
    service_without_llm = ActivationFeatureService(use_llm_descriptions=False)
    
    features_without_llm = service_without_llm.extract_features_from_chunks(SAMPLE_CHUNKS)
    
    if features_without_llm:
        print(f"\nExtracted {len(features_without_llm)} features with manual extraction:\n")
        for feature in features_without_llm:
            print(f"  #{feature.feature_code}")
            print(f"    Description: {feature.description}")
            print(f"    Status: {feature.status}")
            print()
    else:
        print("  ⚠️  No features extracted")
    
    # Compare results
    print("\n3. Comparison:")
    print("-" * 80)
    if features_with_llm and features_without_llm:
        print(f"  Features with LLM: {len(features_with_llm)}")
        print(f"  Features without LLM: {len(features_without_llm)}")
        
        # Show side-by-side comparison for first feature
        if features_with_llm and features_without_llm:
            print(f"\n  Example comparison for #{features_with_llm[0].feature_code}:")
            print(f"    LLM:    {features_with_llm[0].description[:100]}...")
            print(f"    Manual: {features_without_llm[0].description[:100]}...")
    
    # Test answer generation
    print("\n4. Testing answer generation:")
    print("-" * 80)
    if features_with_llm:
        answer = service_with_llm.generate_activation_answer(features_with_llm, 
                                                             "What activation features are available?")
        print("\nGenerated Answer:")
        print(answer)
    
    print("\n" + "="*80)
    print("Test Complete")
    print("="*80 + "\n")


def test_single_feature():
    """Test extraction of a single feature"""
    print("\n" + "="*80)
    print("Testing Single Feature Extraction")
    print("="*80 + "\n")
    
    service = ActivationFeatureService(use_llm_descriptions=True)
    
    # Test with a single chunk
    chunk_text = """(#EDAR) 512 GB Base Memory activation (Pools 2.0) from Static Feature EDAR not orderable in China

This feature provides 512 GB of memory activation for Power10 systems using Pools 2.0.
The activation is converted from static feature EDAR.

Attributes provided: Memory capacity, Pools 2.0 compatibility
Note: This feature cannot be ordered in China."""
    
    feature = service.extract_feature_from_chunk(chunk_text, {'source': 'test'})
    
    if feature:
        print(f"Feature Code: #{feature.feature_code}")
        print(f"Description: {feature.description}")
        print(f"Status: {feature.status}")
        print(f"Available: {feature.is_available}")
    else:
        print("⚠️  No feature extracted")
    
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    try:
        print("\n🧪 Activation Feature LLM Enhancement Test Suite\n")
        
        # Run tests
        test_llm_descriptions()
        test_single_feature()
        
        print("✅ All tests completed successfully!\n")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}\n")
        sys.exit(1)

# Made with Bob
