#!/usr/bin/env python3
"""
Detailed comparison of clustering results from different embedding models.

Analyzes:
- Cluster quality metrics
- Cluster overlap/agreement between models
- Case-by-case comparison
"""
import json
import sys
from pathlib import Path
from collections import defaultdict


def load_cluster_results(filepath):
    """Load cluster results JSON"""
    with open(filepath) as f:
        return json.load(f)


def calculate_cluster_agreement(clusters1, clusters2, total_cases):
    """
    Calculate Adjusted Rand Index-style agreement between two clusterings.
    
    Returns score between -1 (complete disagreement) and 1 (perfect agreement).
    """
    # Build case_id -> cluster_label mappings
    mapping1 = {}
    for label, case_ids in clusters1.items():
        if label != 'noise':
            for case_id in case_ids:
                mapping1[case_id] = label
    
    mapping2 = {}
    for label, case_ids in clusters2.items():
        if label != 'noise':
            for case_id in case_ids:
                mapping2[case_id] = label
    
    # Count pairs that agree
    agree_same = 0  # Both in same cluster
    agree_diff = 0  # Both in different clusters
    disagree = 0    # Models disagree
    
    case_ids = set(mapping1.keys()) & set(mapping2.keys())
    
    for case1 in case_ids:
        for case2 in case_ids:
            if case1 >= case2:  # Avoid double counting
                continue
            
            same_in_1 = mapping1.get(case1) == mapping1.get(case2)
            same_in_2 = mapping2.get(case1) == mapping2.get(case2)
            
            if same_in_1 and same_in_2:
                agree_same += 1
            elif not same_in_1 and not same_in_2:
                agree_diff += 1
            else:
                disagree += 1
    
    total_pairs = agree_same + agree_diff + disagree
    if total_pairs == 0:
        return 0.0
    
    agreement = (agree_same + agree_diff) / total_pairs
    return agreement


def analyze_cluster_sizes(clusters):
    """Analyze cluster size distribution"""
    sizes = []
    for label, case_ids in clusters.items():
        if label != 'noise':
            sizes.append(len(case_ids))
    
    if not sizes:
        return {}
    
    return {
        'min': min(sizes),
        'max': max(sizes),
        'mean': sum(sizes) / len(sizes),
        'total_clusters': len(sizes)
    }


def find_cluster_overlaps(clusters1, clusters2):
    """Find which clusters from model 1 overlap with clusters from model 2"""
    overlaps = defaultdict(lambda: defaultdict(int))
    
    # Build mapping from case_id to cluster label
    mapping1 = {}
    for label, case_ids in clusters1.items():
        if label != 'noise':
            for case_id in case_ids:
                mapping1[case_id] = label
    
    mapping2 = {}
    for label, case_ids in clusters2.items():
        if label != 'noise':
            for case_id in case_ids:
                mapping2[case_id] = label
    
    # Count overlaps
    for case_id in set(mapping1.keys()) & set(mapping2.keys()):
        label1 = mapping1[case_id]
        label2 = mapping2[case_id]
        overlaps[label1][label2] += 1
    
    return overlaps


def main():
    if len(sys.argv) < 3:
        print("Usage: uv run python3 scripts/analyze_cluster_comparison.py <clusters1.json> <clusters2.json>")
        print("\nExample:")
        print("  uv run python3 scripts/analyze_cluster_comparison.py \\")
        print("    trace_reports/failure_signature_collection_*_clusters_openai_small.json \\")
        print("    trace_reports/failure_signature_collection_*_clusters_salesforce.json")
        sys.exit(1)
    
    file1 = Path(sys.argv[1])
    file2 = Path(sys.argv[2])
    
    if not file1.exists():
        print(f"Error: File not found: {file1}")
        sys.exit(1)
    
    if not file2.exists():
        print(f"Error: File not found: {file2}")
        sys.exit(1)
    
    # Load results
    results1 = load_cluster_results(file1)
    results2 = load_cluster_results(file2)
    
    model1 = results1.get('embedding_model', 'Model 1')
    model2 = results2.get('embedding_model', 'Model 2')
    
    print("=" * 80)
    print("EMBEDDING MODEL COMPARISON")
    print("=" * 80)
    print()
    print(f"Model 1: {model1}")
    print(f"  File: {file1.name}")
    print()
    print(f"Model 2: {model2}")
    print(f"  File: {file2.name}")
    print()
    
    # Basic metrics
    print("=" * 80)
    print("BASIC METRICS")
    print("=" * 80)
    print()
    
    metrics = [
        ('Number of Clusters', 'n_clusters'),
        ('Noise Points', 'n_noise'),
        ('Silhouette Score', 'silhouette_score'),
        ('Min Cluster Size', 'min_cluster_size')
    ]
    
    for label, key in metrics:
        val1 = results1.get(key, 'N/A')
        val2 = results2.get(key, 'N/A')
        print(f"{label:25} {model1:30} {model2:30}")
        print(f"{'':25} {str(val1):30} {str(val2):30}")
        print()
    
    # Cluster size analysis
    print("=" * 80)
    print("CLUSTER SIZE DISTRIBUTION")
    print("=" * 80)
    print()
    
    sizes1 = analyze_cluster_sizes(results1['clusters'])
    sizes2 = analyze_cluster_sizes(results2['clusters'])
    
    print(f"{'Metric':25} {model1:30} {model2:30}")
    print("-" * 85)
    print(f"{'Total Clusters':25} {sizes1['total_clusters']:30} {sizes2['total_clusters']:30}")
    print(f"{'Min Size':25} {sizes1['min']:30} {sizes2['min']:30}")
    print(f"{'Max Size':25} {sizes1['max']:30} {sizes2['max']:30}")
    print(f"{'Mean Size':25} {sizes1['mean']:30.1f} {sizes2['mean']:30.1f}")
    print()
    
    # Cluster agreement
    print("=" * 80)
    print("CLUSTER AGREEMENT")
    print("=" * 80)
    print()
    
    # Get total case count
    all_cases1 = set()
    for case_ids in results1['clusters'].values():
        all_cases1.update(case_ids)
    
    all_cases2 = set()
    for case_ids in results2['clusters'].values():
        all_cases2.update(case_ids)
    
    total_cases = len(all_cases1 | all_cases2)
    
    agreement = calculate_cluster_agreement(
        results1['clusters'], 
        results2['clusters'], 
        total_cases
    )
    
    print(f"Pairwise Agreement: {agreement:.3f}")
    print()
    
    if agreement > 0.8:
        print("✓ High agreement - models produce very similar clusters")
    elif agreement > 0.6:
        print("~ Moderate agreement - models agree on major patterns")
    else:
        print("✗ Low agreement - models produce different clusterings")
    print()
    
    # Cluster overlaps (top 5)
    print("=" * 80)
    print("CLUSTER OVERLAPS (Top 5 by size)")
    print("=" * 80)
    print()
    
    overlaps = find_cluster_overlaps(results1['clusters'], results2['clusters'])
    
    # Get top 5 clusters from model 1 by size
    sorted_clusters1 = sorted(
        [(label, len(case_ids)) for label, case_ids in results1['clusters'].items() if label != 'noise'],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    for label1, size1 in sorted_clusters1:
        print(f"Model 1 Cluster {label1} ({size1} failures):")
        
        # Find overlaps with model 2
        overlapping = overlaps[label1]
        sorted_overlaps = sorted(overlapping.items(), key=lambda x: x[1], reverse=True)
        
        for label2, count in sorted_overlaps[:3]:
            pct = 100 * count / size1
            size2 = len(results2['clusters'][label2])
            print(f"  → Model 2 Cluster {label2}: {count}/{size1} ({pct:.0f}%) [Cluster size: {size2}]")
        
        if not sorted_overlaps:
            print("  (No overlaps)")
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    better_score = None
    if results1['silhouette_score'] > results2['silhouette_score']:
        better_score = model1
        diff = results1['silhouette_score'] - results2['silhouette_score']
    elif results2['silhouette_score'] > results1['silhouette_score']:
        better_score = model2
        diff = results2['silhouette_score'] - results1['silhouette_score']
    
    if better_score:
        print(f"🏆 Better Silhouette Score: {better_score}")
        print(f"   Difference: +{diff:.3f}")
    else:
        print("🤝 Equal Silhouette Scores")
    print()
    
    print(f"Cluster Agreement: {agreement:.1%}")
    print()
    
    if agreement > 0.8 and better_score:
        print(f"Recommendation: Use {better_score} (better quality, similar results)")
    elif agreement < 0.6:
        print("Recommendation: Models disagree significantly - review both clusterings")
        print("               Different models may reveal different patterns")
    else:
        print(f"Recommendation: Both models produce reasonable results")
        if better_score:
            print(f"               Slight preference for {better_score}")
    print()


if __name__ == '__main__':
    main()
