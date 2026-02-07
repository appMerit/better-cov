#!/usr/bin/env python3
"""
Compare all clustering results from different embedding models.

Shows a summary table with metrics for all models and ranks them.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict


def load_cluster_results(filepath):
    """Load cluster results JSON"""
    with open(filepath) as f:
        return json.load(f)


def extract_metrics(results):
    """Extract key metrics from cluster results"""
    return {
        'model': results.get('embedding_model', 'Unknown'),
        'n_clusters': results.get('n_clusters', 0),
        'n_noise': results.get('n_noise', 0),
        'silhouette': results.get('silhouette_score', 0.0),
        'min_cluster_size': results.get('min_cluster_size', 0)
    }


def calculate_cluster_agreement(clusters1, clusters2):
    """Calculate pairwise agreement between two clusterings"""
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
    agree_same = 0
    agree_diff = 0
    disagree = 0
    
    case_ids = set(mapping1.keys()) & set(mapping2.keys())
    
    for case1 in case_ids:
        for case2 in case_ids:
            if case1 >= case2:
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
    
    return (agree_same + agree_diff) / total_pairs


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/compare_all_models.py <cluster_results_dir>")
        print("\nExample:")
        print("  python3 scripts/compare_all_models.py trace_reports/")
        print("\nThis will find all *_clusters_*.json files and compare them.")
        sys.exit(1)
    
    results_dir = Path(sys.argv[1])
    
    if not results_dir.exists():
        print(f"Error: Directory not found: {results_dir}")
        sys.exit(1)
    
    # Find all cluster result files
    cluster_files = list(results_dir.glob('*_clusters_*.json'))
    
    if not cluster_files:
        print(f"Error: No cluster result files found in {results_dir}")
        print("Looking for files matching pattern: *_clusters_*.json")
        sys.exit(1)
    
    print("=" * 100)
    print("MULTI-MODEL EMBEDDING COMPARISON")
    print("=" * 100)
    print()
    
    # Load all results
    all_results = {}
    for filepath in sorted(cluster_files):
        # Extract model name from filename
        # e.g., "failure_signature_collection_20260129_053152_clusters_openai_small.json"
        parts = filepath.stem.split('_clusters_')
        if len(parts) == 2:
            model_key = parts[1]
            all_results[model_key] = {
                'filepath': filepath,
                'data': load_cluster_results(filepath),
                'metrics': extract_metrics(load_cluster_results(filepath))
            }
    
    if len(all_results) < 2:
        print(f"Error: Need at least 2 models to compare. Found {len(all_results)}.")
        sys.exit(1)
    
    print(f"Found {len(all_results)} models:")
    for model_key in sorted(all_results.keys()):
        print(f"  • {model_key}")
    print()
    
    # Summary table
    print("=" * 100)
    print("SUMMARY METRICS")
    print("=" * 100)
    print()
    
    # Header
    print(f"{'Model':<25} {'Clusters':<12} {'Noise':<10} {'Silhouette':<15} {'Min Size':<10}")
    print("-" * 100)
    
    # Sort by silhouette score (descending)
    sorted_models = sorted(
        all_results.items(),
        key=lambda x: x[1]['metrics']['silhouette'],
        reverse=True
    )
    
    for model_key, result in sorted_models:
        m = result['metrics']
        print(f"{model_key:<25} {m['n_clusters']:<12} {m['n_noise']:<10} {m['silhouette']:<15.4f} {m['min_cluster_size']:<10}")
    
    print()
    
    # Ranking
    print("=" * 100)
    print("RANKING BY SILHOUETTE SCORE")
    print("=" * 100)
    print()
    
    for rank, (model_key, result) in enumerate(sorted_models, 1):
        m = result['metrics']
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"  {rank}."
        print(f"{medal} {model_key:<25} Score: {m['silhouette']:.4f}  ({m['n_clusters']} clusters, {m['n_noise']} noise)")
    
    print()
    
    # Pairwise agreement matrix
    print("=" * 100)
    print("PAIRWISE AGREEMENT MATRIX")
    print("=" * 100)
    print()
    print("Shows how similar each pair of clusterings is (0.0 = completely different, 1.0 = identical)")
    print()
    
    model_keys = sorted(all_results.keys())
    
    # Print header
    print(f"{'':15}", end='')
    for key in model_keys:
        print(f"{key[:12]:>12}", end='')
    print()
    print("-" * (15 + 12 * len(model_keys)))
    
    # Print agreement matrix
    for key1 in model_keys:
        print(f"{key1[:15]:<15}", end='')
        for key2 in model_keys:
            if key1 == key2:
                print(f"{'1.000':>12}", end='')
            else:
                agreement = calculate_cluster_agreement(
                    all_results[key1]['data']['clusters'],
                    all_results[key2]['data']['clusters']
                )
                print(f"{agreement:>12.3f}", end='')
        print()
    
    print()
    
    # Recommendations
    print("=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)
    print()
    
    best_model = sorted_models[0]
    best_key = best_model[0]
    best_metrics = best_model[1]['metrics']
    
    print(f"🏆 Best Overall: {best_key}")
    print(f"   Silhouette Score: {best_metrics['silhouette']:.4f}")
    print(f"   Clusters: {best_metrics['n_clusters']}")
    print(f"   Noise Points: {best_metrics['n_noise']}")
    print()
    
    # Check for high agreement
    agreements = []
    for i, (key1, result1) in enumerate(sorted_models):
        for key2, result2 in sorted_models[i+1:]:
            agreement = calculate_cluster_agreement(
                result1['data']['clusters'],
                result2['data']['clusters']
            )
            agreements.append((key1, key2, agreement))
    
    high_agreements = [(k1, k2, a) for k1, k2, a in agreements if a > 0.95]
    
    if high_agreements:
        print("High Agreement Pairs (>95%):")
        for key1, key2, agreement in sorted(high_agreements, key=lambda x: x[2], reverse=True):
            print(f"  • {key1} ↔ {key2}: {agreement:.1%}")
        print()
        print("  → These models produce nearly identical clusters, suggesting robust patterns")
        print()
    
    # Model-specific recommendations
    print("Model Selection Guide:")
    print()
    
    # Find best API and best local model
    api_models = [(k, r) for k, r in sorted_models if 'openai' in k]
    local_models = [(k, r) for k, r in sorted_models if 'openai' not in k]
    
    if api_models and local_models:
        best_api = api_models[0]
        best_local = local_models[0]
        
        # Check agreement between best API and best local
        if best_api[0] in all_results and best_local[0] in all_results:
            agreement = calculate_cluster_agreement(
                all_results[best_api[0]]['data']['clusters'],
                all_results[best_local[0]]['data']['clusters']
            )
        else:
            agreement = 0.0
        
        score_diff = best_local[1]['metrics']['silhouette'] - best_api[1]['metrics']['silhouette']
        
        # High agreement means they produce same clustering despite score difference
        if agreement > 0.95:
            api_noise = best_api[1]['metrics']['n_noise']
            local_noise = best_local[1]['metrics']['n_noise']
            api_clusters = best_api[1]['metrics']['n_clusters']
            local_clusters = best_local[1]['metrics']['n_clusters']
            
            # Calculate total groups (clusters + noise as separate group)
            api_groups = api_clusters + (1 if api_noise > 0 else 0)
            local_groups = local_clusters + (1 if local_noise > 0 else 0)
            
            print(f"  ✅ RECOMMENDED: {best_api[0]} (API)")
            print(f"    - Silhouette Score: {best_api[1]['metrics']['silhouette']:.4f}")
            print(f"    - **{agreement:.1%} agreement with {best_local[0]}** (nearly identical!)")
            print(f"    - Groups to investigate: {api_groups} ({api_clusters} clusters + {api_noise} noise)")
            print(f"    - Benefits: Fast (seconds), fewer groups, established")
            print(f"    - Trade-off: API cost")
            print()
            print(f"  Alternative: {best_local[0]} (Local)")
            print(f"    - Silhouette Score: {best_local[1]['metrics']['silhouette']:.4f}")
            print(f"    - Groups to investigate: {local_groups} ({local_clusters} clusters + {local_noise} noise)")
            print(f"    - Benefits: Higher silhouette, private")
            print(f"    - Trade-off: Slower on CPU, more noise to investigate")
            print()
            if local_groups > api_groups:
                print(f"  💡 {agreement:.1%} agreement means same cluster assignments.")
                print(f"     {best_api[0]} has {local_groups - api_groups} fewer group(s) to investigate (no noise).")
            else:
                print(f"  💡 Since agreement is {agreement:.1%}, both produce nearly identical clusters.")
                print(f"     Choose based on runtime preference (API speed vs local privacy).")
        elif score_diff > 0.05:
            # Local significantly better and different
            print(f"  ✅ RECOMMENDED: {best_local[0]} (Local)")
            print(f"    - Silhouette Score: {best_local[1]['metrics']['silhouette']:.4f}")
            print(f"    - Outperforms best API model by {score_diff:.4f}")
            print(f"    - Agreement: {agreement:.1%}")
            print(f"    - Benefits: Better quality, private")
            print(f"    - Trade-off: {best_local[1]['metrics']['n_noise']} noise points, slower on CPU")
            print()
            print(f"  Alternative: {best_api[0]} (API)")
            print(f"    - Silhouette Score: {best_api[1]['metrics']['silhouette']:.4f}")
            print(f"    - Use if: You prefer speed and established providers")
        elif score_diff < -0.05:
            # API significantly better
            print(f"  ✅ RECOMMENDED: {best_api[0]} (API)")
            print(f"    - Silhouette Score: {best_api[1]['metrics']['silhouette']:.4f}")
            print(f"    - Outperforms best local model by {abs(score_diff):.4f}")
            print(f"    - Benefits: Better quality, fast, established")
            print()
            print(f"  Alternative: {best_local[0]} (Local)")
            print(f"    - Silhouette Score: {best_local[1]['metrics']['silhouette']:.4f}")
            print(f"    - Use if: You want privacy and no API costs")
        else:
            # Competitive
            print(f"  💡 Local and API models are competitive!")
            print(f"     Score difference: {abs(score_diff):.4f}")
            print(f"     Agreement: {agreement:.1%}")
            print()
            print(f"  Best Local: {best_local[0]}")
            print(f"    - Score: {best_local[1]['metrics']['silhouette']:.4f}")
            print(f"    - Benefits: Private")
            print()
            print(f"  Best API: {best_api[0]}")
            print(f"    - Score: {best_api[1]['metrics']['silhouette']:.4f}")
            print(f"    - Benefits: Fast, established")
    elif local_models:
        best_local = local_models[0]
        print(f"  ✅ RECOMMENDED: {best_local[0]} (Local)")
        print(f"    - Silhouette Score: {best_local[1]['metrics']['silhouette']:.4f}")
        print(f"    - Benefits: Private")
    elif api_models:
        best_api = api_models[0]
        print(f"  ✅ RECOMMENDED: {best_api[0]} (API)")
        print(f"    - Silhouette Score: {best_api[1]['metrics']['silhouette']:.4f}")
    
    print()


if __name__ == '__main__':
    main()
