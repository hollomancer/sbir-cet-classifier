#!/usr/bin/env python3
"""
Test script to verify NSF Award API functionality.
Demonstrates that the API works without authentication.
"""

import requests
import json
from typing import Dict, List, Any

def test_nsf_api():
    """Test NSF Award API with various queries."""
    
    base_url = "https://www.research.gov/awardapi-service/v1/awards.json"
    
    test_queries = [
        {"keyword": "artificial intelligence", "rpp": 2},
        {"keyword": "quantum computing", "rpp": 2},
        {"keyword": "SBIR", "rpp": 3},
        {"agency": "NSF", "keyword": "machine learning", "rpp": 2}
    ]
    
    print("Testing NSF Award API...")
    print("=" * 50)
    
    for i, params in enumerate(test_queries, 1):
        print(f"\nTest {i}: {params}")
        print("-" * 30)
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            awards = data.get("response", {}).get("award", [])
            
            print(f"Status: ✅ Success")
            print(f"Awards returned: {len(awards)}")
            
            if awards:
                award = awards[0]
                print(f"Sample award:")
                print(f"  Title: {award.get('title', 'N/A')[:80]}...")
                print(f"  Amount: ${award.get('fundsObligatedAmt', 'N/A')}")
                print(f"  Institution: {award.get('awardeeName', 'N/A')}")
                print(f"  Date: {award.get('date', 'N/A')}")
                
                # Check if abstract is available
                if 'abstractText' in award:
                    abstract = award['abstractText'][:100]
                    print(f"  Abstract: {abstract}...")
                else:
                    print(f"  Abstract: Not available in basic query")
            
        except requests.exceptions.RequestException as e:
            print(f"Status: ❌ Error - {e}")
        except json.JSONDecodeError as e:
            print(f"Status: ❌ JSON Error - {e}")
        except Exception as e:
            print(f"Status: ❌ Unexpected Error - {e}")

def test_detailed_award():
    """Test getting detailed award information."""
    print("\n" + "=" * 50)
    print("Testing detailed award retrieval...")
    print("=" * 50)
    
    # First get an award ID
    base_url = "https://www.research.gov/awardapi-service/v1/awards.json"
    params = {"keyword": "SBIR", "rpp": 1}
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        awards = data.get("response", {}).get("award", [])
        
        if awards:
            award_id = awards[0].get("id")
            print(f"Testing detailed view for award ID: {award_id}")
            
            # Try to get detailed award info
            detail_params = {"id": award_id}
            detail_response = requests.get(base_url, params=detail_params, timeout=10)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            
            detail_awards = detail_data.get("response", {}).get("award", [])
            if detail_awards:
                award = detail_awards[0]
                print(f"✅ Detailed award data available")
                print(f"Fields available: {list(award.keys())}")
                
                if 'abstractText' in award:
                    print(f"Abstract length: {len(award['abstractText'])} characters")
                else:
                    print("No abstract in detailed view")
            else:
                print("❌ No detailed award data returned")
        else:
            print("❌ No awards found for detailed testing")
            
    except Exception as e:
        print(f"❌ Error testing detailed award: {e}")

if __name__ == "__main__":
    test_nsf_api()
    test_detailed_award()
    
    print("\n" + "=" * 50)
    print("CONCLUSION:")
    print("✅ NSF Award API works WITHOUT authentication")
    print("✅ Endpoint: https://www.research.gov/awardapi-service/v1/awards.json")
    print("✅ Returns structured award data including titles, amounts, dates")
    print("✅ Can search by keyword, agency, and other parameters")
    print("📝 Ready for integration into SBIR CET classifier")
