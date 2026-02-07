#!/usr/bin/env python3
"""
Sample representative failures from each cluster.

Usage:
    python3 scripts/sample_cluster_representatives.py <cluster_results.json> [--strategy middle|edge|diverse]
"""
import json
import sys
from pathlib import Path


def sample_most_representative(cluster_case_ids, sample_metrics, n=1):
    """
    Sample the most representative (most central) items from a cluster.
    
    Returns list of case_ids sorted by centrality (most central first).
    """
    # Sort by distance to centroid (lower = more central)
    sorted_ids = sorted(
        cluster_case_ids,
        key=lambda case_id: sample_metrics[case_id]['distance_to_centroid']
    )
    return sorted_ids[:n]


def sample_edge_cases(cluster_case_ids, sample_metrics, n=1):
    """
    Sample edge cases (least representative) from a cluster.
    
    Returns list of case_ids with lowest silhouette scores.
    """
    # Sort by silhouette score (lower = more edge-like)
    sorted_ids = sorted(
        cluster_case_ids,
        key=lambda case_id: sample_metrics[case_id]['silhouette']
    )
    return sorted_ids[:n]


def sample_diverse(cluster_case_ids, sample_metrics, n=3):
    """
    Sample diverse representatives: most central + edges.
    
    Returns: [most_central, medium, edge_case]
    """
    if len(cluster_case_ids) < n:
        return cluster_case_ids
    
    # Sort by distance
    by_distance = sorted(
        cluster_case_ids,
        key=lambda case_id: sample_metrics[case_id]['distance_to_centroid']
    )
    
    # Take from different positions
    indices = [0, len(by_distance) // 2, -1]  # First, middle, last
    return [by_distance[i] for i in indices[:n]]


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/sample_cluster_representatives.py <cluster_results.json> [--strategy middle|edge|diverse]")
        sys.exit(1)
    
    cluster_file = Path(sys.argv[1])
    strategy = 'middle'  # default
    
    if len(sys.argv) > 2 and sys.argv[2] in ['--strategy']:
        strategy = sys.argv[3] if len(sys.argv) > 3 else 'middle'
    
    if not cluster_file.exists():
        print(f"Error: File not found: {cluster_file}")
        sys.exit(1)
    
    # Load cluster results
    with open(cluster_file) as f:
        data = json.load(f)
    
    clusters = data['clusters']
    sample_metrics = data['sample_metrics']
    
    print("=" * 80)
    print(f"SAMPLING STRATEGY: {strategy.upper()}")
    print("=" * 80)
    print()
    
    # Sample from each cluster
    for cluster_label, case_ids in sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True):
        # Skip empty clusters
        if not case_ids:
            continue
        
        print(f"Cluster {cluster_label}: {len(case_ids)} failures")
        
        # Choose sampling strategy
        if strategy == 'middle':
            samples = sample_most_representative(case_ids, sample_metrics, n=1)
            print(f"  Most representative:")
        elif strategy == 'edge':
            samples = sample_edge_cases(case_ids, sample_metrics, n=1)
            print(f"  Edge case:")
        elif strategy == 'diverse':
            samples = sample_diverse(case_ids, sample_metrics, n=3)
            print(f"  Diverse sample:")
        else:
            samples = [case_ids[0]]
            print(f"  First item:")
        
        # Print samples with metrics
        for case_id in samples:
            metrics = sample_metrics[case_id]
            sil = metrics['silhouette']
            dist = metrics['distance_to_centroid']
            
            # Classify representativeness
            if dist is not None:
                if dist < 0.05:
                    rep = "VERY CENTRAL"
                elif dist < 0.15:
                    rep = "CENTRAL"
                elif dist < 0.30:
                    rep = "MODERATE"
                else:
                    rep = "EDGE"
            else:
                rep = "NOISE"
            
            print(f"    • {case_id}")
            dist_str = f"{dist:.4f}" if dist is not None else "N/A"
            print(f"      Silhouette: {sil:.3f}, Distance: {dist_str}, Position: {rep}")
        
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total clusters: {len([k for k in clusters.keys() if k != 'noise'])}")
    print(f"Sampling strategy: {strategy}")
    print()
    print("To send to error analyzer:")
    print("  - 'middle': Send 1 most representative per cluster (fastest)")
    print("  - 'diverse': Send 3 diverse samples per cluster (comprehensive)")
    print("  - 'edge': Send edge cases (catch unusual failures)")
    print()


if __name__ == '__main__':
    main()
