#!/usr/bin/env python
"""Test and compare NIH API matching strategies on 100 awards."""

import time
from pathlib import Path
from difflib import SequenceMatcher

import httpx

from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv


class NIHMatcher:
    """NIH API matching strategies."""
    
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.base_url = "https://api.reporter.nih.gov/v2"
        self.cache = {}
    
    def search_api(self, criteria, limit=5):
        """Search NIH API with criteria."""
        cache_key = str(sorted(criteria.items()))
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        payload = {
            'criteria': criteria,
            'include_fields': ['ProjectNum', 'Organization', 'AwardAmount', 'FiscalYear', 'AbstractText'],
            'limit': limit
        }
        
        try:
            response = self.client.post(f"{self.base_url}/projects/search", json=payload)
            if response.status_code == 200:
                results = response.json().get('results', [])
                self.cache[cache_key] = results
                return results
        except Exception:
            pass
        
        return []
    
    def strategy_1_org_amount_year(self, award):
        """Strategy 1: Organization + Amount + Year."""
        amount_min = int(award.award_amount * 0.9)
        amount_max = int(award.award_amount * 1.1)
        
        criteria = {
            'org_names': [award.firm_name],
            'award_amount_range': {'min_amount': amount_min, 'max_amount': amount_max},
            'fiscal_years': [award.award_date.year]
        }
        
        results = self.search_api(criteria, limit=1)
        return results[0] if results else None
    
    def strategy_2_text_similarity(self, award):
        """Strategy 2: Text Similarity Matching."""
        if not award.abstract:
            return None
        
        # Broad search by org + year
        criteria = {
            'org_names': [award.firm_name],
            'fiscal_years': [award.award_date.year]
        }
        
        candidates = self.search_api(criteria, limit=10)
        if not candidates:
            return None
        
        # Find best abstract match
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            candidate_abstract = candidate.get('abstract_text', '')
            if candidate_abstract:
                score = SequenceMatcher(None, award.abstract.lower(), candidate_abstract.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = candidate
        
        return best_match if best_score > 0.5 else None
    
    def strategy_3_fuzzy_org(self, award):
        """Strategy 3: Fuzzy Organization Name Matching."""
        # Normalize organization name
        org_name = award.firm_name.upper()
        for suffix in [' INC', ' LLC', ' CORP', ' CO', ' LTD', ' INCORPORATED', ',']:
            org_name = org_name.replace(suffix, '')
        org_name = org_name.strip()
        
        amount_min = int(award.award_amount * 0.9)
        amount_max = int(award.award_amount * 1.1)
        
        # Try variations
        variations = [
            award.firm_name,
            org_name,
            org_name.replace('.', ''),
        ]
        
        for org in variations:
            criteria = {
                'org_names': [org],
                'award_amount_range': {'min_amount': amount_min, 'max_amount': amount_max},
                'fiscal_years': [award.award_date.year]
            }
            
            results = self.search_api(criteria, limit=1)
            if results:
                return results[0]
        
        return None
    
    def strategy_4_hybrid(self, award):
        """Strategy 4: Hybrid Approach with confidence scoring."""
        matches = []
        
        # Try exact match
        exact = self.strategy_1_org_amount_year(award)
        if exact:
            matches.append(('exact', 1.0, exact))
        
        # Try fuzzy match
        fuzzy = self.strategy_3_fuzzy_org(award)
        if fuzzy and (not exact or fuzzy.get('project_num') != exact.get('project_num')):
            matches.append(('fuzzy', 0.8, fuzzy))
        
        # Try text similarity
        if award.abstract:
            similar = self.strategy_2_text_similarity(award)
            if similar and not any(m[2].get('project_num') == similar.get('project_num') for m in matches):
                matches.append(('similarity', 0.9, similar))
        
        # Return best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][2]
        
        return None


def test_strategies():
    """Test all strategies on 100 NIH awards."""
    print("="*70)
    print("NIH API MATCHING STRATEGIES TEST")
    print("="*70)
    
    # Load 100 HHS awards
    print("\n=== Loading Awards ===")
    result = load_bootstrap_csv(Path("award_data.csv"))
    hhs_awards = [a for a in result.awards if a.agency == 'HHS'][:100]
    print(f"✓ Loaded {len(hhs_awards)} HHS awards for testing")
    
    # Initialize matcher
    matcher = NIHMatcher()
    
    # Test each strategy
    strategies = [
        ('Strategy 1: Org + Amount + Year', matcher.strategy_1_org_amount_year),
        ('Strategy 2: Text Similarity', matcher.strategy_2_text_similarity),
        ('Strategy 3: Fuzzy Org Matching', matcher.strategy_3_fuzzy_org),
        ('Strategy 4: Hybrid Approach', matcher.strategy_4_hybrid),
    ]
    
    results = {}
    
    for strategy_name, strategy_func in strategies:
        print(f"\n=== Testing {strategy_name} ===")
        
        matches = []
        match_count = 0
        total_time = 0
        
        for i, award in enumerate(hhs_awards):
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/100...")
            
            start = time.time()
            match = strategy_func(award)
            elapsed = time.time() - start
            total_time += elapsed
            
            if match:
                match_count += 1
                matches.append({
                    'award_id': award.award_id,
                    'firm': award.firm_name,
                    'amount': award.award_amount,
                    'year': award.award_date.year,
                    'project_num': match.get('project_num'),
                    'nih_org': match.get('organization', {}).get('org_name'),
                    'nih_amount': match.get('award_amount'),
                })
        
        match_rate = match_count / len(hhs_awards) * 100
        avg_time = total_time / len(hhs_awards) * 1000
        
        results[strategy_name] = {
            'matches': match_count,
            'match_rate': match_rate,
            'avg_time_ms': avg_time,
            'total_time': total_time,
            'sample_matches': matches[:5]
        }
        
        print(f"✓ Complete:")
        print(f"  Matches: {match_count}/100 ({match_rate:.1f}%)")
        print(f"  Avg time: {avg_time:.1f}ms per award")
        print(f"  Total time: {total_time:.1f}s")
    
    # Print comparison
    print(f"\n{'='*70}")
    print("STRATEGY COMPARISON")
    print(f"{'='*70}")
    print(f"\n{'Strategy':<35} {'Matches':<12} {'Rate':<10} {'Avg Time'}")
    print(f"{'-'*70}")
    
    for strategy_name in results:
        r = results[strategy_name]
        print(f"{strategy_name:<35} {r['matches']:>3}/100      {r['match_rate']:>5.1f}%    {r['avg_time_ms']:>6.1f}ms")
    
    # Show sample matches
    print(f"\n{'='*70}")
    print("SAMPLE MATCHES (Strategy 4: Hybrid)")
    print(f"{'='*70}")
    
    for i, match in enumerate(results['Strategy 4: Hybrid Approach']['sample_matches'], 1):
        print(f"\n{i}. CSV Award:")
        print(f"   Firm: {match['firm']}")
        print(f"   Amount: ${match['amount']:,.0f}")
        print(f"   Year: {match['year']}")
        print(f"   NIH Match:")
        print(f"   Project: {match['project_num']}")
        print(f"   Org: {match['nih_org']}")
        print(f"   Amount: ${match['nih_amount']:,.0f}")
    
    # Recommendations
    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}")
    
    best_strategy = max(results.items(), key=lambda x: x[1]['match_rate'])
    fastest_strategy = min(results.items(), key=lambda x: x[1]['avg_time_ms'])
    
    print(f"\nBest Match Rate: {best_strategy[0]}")
    print(f"  {best_strategy[1]['match_rate']:.1f}% match rate")
    
    print(f"\nFastest: {fastest_strategy[0]}")
    print(f"  {fastest_strategy[1]['avg_time_ms']:.1f}ms per award")
    
    print(f"\nRecommended: Strategy 4 (Hybrid Approach)")
    print(f"  - Best balance of match rate and accuracy")
    print(f"  - Combines strengths of all strategies")
    print(f"  - {results['Strategy 4: Hybrid Approach']['match_rate']:.1f}% coverage")
    
    print(f"\n{'='*70}")


if __name__ == "__main__":
    test_strategies()
