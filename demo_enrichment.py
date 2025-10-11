#!/usr/bin/env python3
"""Demo script for SAM.gov enrichment functionality."""

import os
from src.sbir_cet_classifier.common.config import EnrichmentConfig
from src.sbir_cet_classifier.data.enrichment.sam_client import SAMClient
from src.sbir_cet_classifier.data.enrichment.enrichers import EnrichmentService, EnrichmentType

def main():
    """Demonstrate enrichment functionality."""
    print("🚀 SAM.gov Enrichment Demo")
    print("=" * 50)
    
    # Check if API key is configured
    api_key = os.getenv("SAM_API_KEY")
    if not api_key:
        print("⚠️  SAM_API_KEY not set. Using mock configuration for demo.")
        api_key = "demo-key-12345"
    
    # Create configuration
    config = EnrichmentConfig(
        api_key=api_key,
        base_url="https://api.sam.gov/prod/federalregistry/v2",
        rate_limit=100,
        timeout=30,
        max_retries=3
    )
    
    print(f"📡 API Configuration:")
    print(f"   Base URL: {config.base_url}")
    print(f"   Rate Limit: {config.rate_limit} req/min")
    print(f"   Timeout: {config.timeout}s")
    print()
    
    # Initialize services
    sam_client = SAMClient(config)
    enrichment_service = EnrichmentService(sam_client)
    
    print("🔧 Services initialized successfully!")
    print(f"   SAM Client: {type(sam_client).__name__}")
    print(f"   Enrichment Service: {type(enrichment_service).__name__}")
    print()
    
    # Demo enrichment types
    print("📋 Available Enrichment Types:")
    for enrichment_type in EnrichmentType:
        print(f"   • {enrichment_type.value}")
    print()
    
    # Demo award enrichment (mock)
    print("🎯 Demo Award Enrichment:")
    print("   Award ID: DEMO-AWARD-123")
    print("   Enrichment Types: [awardee]")
    print()
    
    try:
        # This would normally call the real API
        print("   Status: Ready for enrichment")
        print("   Note: Set SAM_API_KEY environment variable for live API calls")
        
        # Show what the result structure would look like
        print("\n📊 Expected Result Structure:")
        print("   ✓ success: bool")
        print("   ✓ confidence: float (0.0-1.0)")
        print("   ✓ processing_time_ms: int")
        print("   ✓ data: dict (enriched award data)")
        print("   ✓ error_message: str (if failed)")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎉 Demo completed successfully!")
    print("\nNext steps:")
    print("1. Set SAM_API_KEY environment variable")
    print("2. Run: python -m sbir_cet_classifier.cli.app enrich award <award-id>")
    print("3. Or use the batch enrichment: python -m sbir_cet_classifier.cli.app enrich batch <award-ids>")

if __name__ == "__main__":
    main()
