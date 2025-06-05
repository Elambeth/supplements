#!/usr/bin/env python3
"""
Test script to verify PubMed query building and filtering logic
"""

import json
from datetime import datetime

# Copy the constants and query building function from the Lambda script
HIGH_QUALITY_PUBLICATION_TYPES = [
    "Randomized Controlled Trial",
    "Systematic Review", 
    "Meta-Analysis",
    "Network Meta-Analysis",
    "Clinical Trial, Phase II",
    "Clinical Trial, Phase III", 
    "Controlled Clinical Trial",
    "Pragmatic Clinical Trial",
    "Adaptive Clinical Trial",
    "Observational Study",
    "Clinical Study",
    "Comparative Study",
    "Multicenter Study",
    "Review",
    "Scoping Review",
    "Practice Guideline",
    "Guideline"
]

def build_search_query(supplement: str, search_params: dict = None) -> str:
    """
    Build a comprehensive PubMed search query with high-quality filters.
    """
    if search_params is None:
        search_params = {}
    
    # Base search for supplement
    query = f'"{supplement}"[Title/Abstract]'
    
    # Add therapeutic context
    query += ' AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract] OR therapeutic[Title/Abstract] OR clinical[Title/Abstract])'
    
    # Add high-quality publication type filters
    pub_type_filters = []
    for pub_type in HIGH_QUALITY_PUBLICATION_TYPES:
        pub_type_filters.append(f'"{pub_type}"[Publication Type]')
    
    if pub_type_filters:
        query += f" AND ({' OR '.join(pub_type_filters)})"
    
    # Add date range if specified
    start_year = search_params.get('start_year')
    end_year = search_params.get('end_year', datetime.now().year)
    
    if start_year:
        query += f" AND {start_year}:{end_year}[pdat]"
    
    # Add language filter (English only for consistency)
    query += ' AND English[Language]'
    
    # Add human studies filter
    query += ' AND humans[MeSH Terms]'
    
    return query

def test_query_building():
    """Test the query building with different parameters"""
    
    print("=== Testing PubMed Query Building ===\n")
    
    # Test 1: Basic supplement query
    print("1. Basic Creatine Query:")
    query1 = build_search_query("Creatine")
    print(f"Query: {query1}")
    print(f"Length: {len(query1)} characters")
    print()
    
    # Test 2: With date range
    print("2. Creatine Query with Date Range (2020-2024):")
    query2 = build_search_query("Creatine", {"start_year": 2020, "end_year": 2024})
    print(f"Query: {query2}")
    print()
    
    # Test 3: Different supplement
    print("3. Vitamin D Query:")
    query3 = build_search_query("Vitamin D")
    print(f"Query: {query3}")
    print()
    
    # Test 4: Count publication types
    print("4. Publication Type Analysis:")
    print(f"Number of publication types included: {len(HIGH_QUALITY_PUBLICATION_TYPES)}")
    print("Publication types:")
    for i, pub_type in enumerate(HIGH_QUALITY_PUBLICATION_TYPES, 1):
        print(f"  {i:2d}. {pub_type}")
    print()
    
    # Test 5: Verify key components are present
    print("5. Query Component Verification:")
    test_query = build_search_query("TestSupplement")
    
    components_to_check = [
        ('Supplement in title/abstract', '"TestSupplement"[Title/Abstract]'),
        ('Therapeutic context', 'therapy[Title/Abstract]'),
        ('Clinical context', 'clinical[Title/Abstract]'),
        ('RCT filter', '"Randomized Controlled Trial"[Publication Type]'),
        ('Meta-analysis filter', '"Meta-Analysis"[Publication Type]'),
        ('Human studies filter', 'humans[MeSH Terms]'),
        ('English language filter', 'English[Language]')
    ]
    
    for component_name, component_text in components_to_check:
        is_present = component_text in test_query
        status = "✅ PRESENT" if is_present else "❌ MISSING"
        print(f"  {status}: {component_name}")
    
    print()
    
    return {
        "basic_query": query1,
        "dated_query": query2,
        "vitamin_d_query": query3,
        "publication_types_count": len(HIGH_QUALITY_PUBLICATION_TYPES)
    }

if __name__ == "__main__":
    results = test_query_building()
    
    # Save results to file for inspection
    with open("query_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("Test results saved to 'query_test_results.json'")
    print("\n=== Test Complete ===")