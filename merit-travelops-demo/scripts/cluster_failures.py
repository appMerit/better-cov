#!/usr/bin/env python3
"""
Cluster failures using embeddings + HDBSCAN.

Supports multiple embedding models:
- OpenAI: text-embedding-3-small, text-embedding-3-large
- Salesforce: SFR-Embedding-Code-400M_R (code-specialized)

Auto-discovers number of clusters - no need to specify k upfront!

No hard-coded rules - purely semantic similarity.
Works for any assertion type (simple assertions, semantic predicates, etc.)
"""
import json
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
from sklearn.metrics import silhouette_score, silhouette_samples
from dotenv import load_dotenv

# Import HDBSCAN (required)
try:
    import hdbscan
except ImportError:
    print("Error: hdbscan not installed")
    print("\nInstall with:")
    print("  pip install hdbscan")
    print("  # or")
    print("  uv pip install hdbscan")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Supported models
SUPPORTED_MODELS = {
    'openai-small': 'text-embedding-3-small',
    'openai-large': 'text-embedding-3-large',
    'modernbert': 'juanwisz/modernbert-python-code-retrieval',
    'gemma': 'google/embeddinggemma-300m',
    'qwen': 'Qwen/Qwen3-Embedding-0.6B'
}


def create_embedding_text(sig):
    """
    Create text representation of failure for embedding.
    
    Uses the new cluster_key which contains ALL assertions (passed and failed)
    formatted in Merit's pretty format with context lines and resolved values.
    
    Falls back to old format if cluster_key not present.
    """
    
    # NEW FORMAT: Use cluster_key if available (concatenated pretty assertions)
    cluster_key = sig.get('cluster_key')
    if cluster_key:
        # Cluster key already contains everything we need:
        # - All assertions (passed and failed)
        # - Context lines (lines_above, lines_below)
        # - Resolved argument values
        # - Consistent ordering
        return cluster_key
    
    # OLD FORMAT FALLBACK: Construct from individual pieces
    clustering = sig.get('clustering', sig)
    parts = []
    
    # Assertion expressions (CRITICAL: what assertion actually failed)
    assertions = clustering.get('assertion_expressions', [])
    if assertions:
        assertion_text = '; '.join(assertions)
        parts.append(f"Assertion: {assertion_text}")
    
    # Error message (symptom - now secondary signal)
    error_type = clustering.get('error_type', 'Unknown error')
    parts.append(f"Error: {error_type}")
    
    # Execution flow (which components were involved)
    flow = clustering.get('execution_flow', [])
    if flow:
        # Already filtered to SUT components only
        parts.append(f"Execution path: {' -> '.join(flow)}")
    
    # Anomaly flags (behavioral signals)
    anomalies = clustering.get('anomaly_flags', {})
    anomaly_list = [k.replace('has_', '').replace('_', ' ') 
                    for k, v in anomalies.items() if v and isinstance(v, bool)]
    if anomaly_list:
        parts.append(f"Anomalies: {', '.join(anomaly_list)}")
    
    # Test type (gives context about what's being tested)
    test_name = sig.get('test_name', '')
    test_type = test_name.replace('merit_', '').replace('_', ' ')
    if test_type:
        parts.append(f"Test type: {test_type}")
    
    return ' | '.join(parts)


def get_embeddings_openai(texts, model_name, api_key):
    """Get embeddings from OpenAI API"""
    from openai import OpenAI
    
    client = OpenAI(api_key=api_key)
    
    print(f"Getting embeddings for {len(texts)} failures using {model_name}...")
    
    # Batch embeddings (max 100 per batch for efficiency)
    batch_size = 100
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(texts)-1)//batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}...", end='', flush=True)
        
        response = client.embeddings.create(
            model=model_name,
            input=batch
        )
        
        embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(embeddings)
        print(" ✓")
    
    return np.array(all_embeddings)


def get_embeddings_local(texts, model_name, model_key):
    """Get embeddings from local HuggingFace models using sentence-transformers
    
    Supports standard encoder models (ModernBERT, Gemma, Qwen, etc.)
    that don't require task-specific prefixes.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("Error: sentence-transformers not installed")
        print("\nInstall with:")
        print("  pip install sentence-transformers")
        print("  # or")
        print("  uv pip install sentence-transformers")
        sys.exit(1)
    
    print(f"Loading {model_name}...")
    
    # Some models may need trust_remote_code
    trust_remote = model_key in ['qwen']  # Qwen models need trust_remote_code
    
    try:
        # Force CPU to avoid MPS/accelerator issues on macOS
        if trust_remote:
            model = SentenceTransformer(model_name, device='cpu', trust_remote_code=True)
        else:
            model = SentenceTransformer(model_name, device='cpu')
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Trying with trust_remote_code=True...")
        model = SentenceTransformer(model_name, device='cpu', trust_remote_code=True)
    
    print(f"Getting embeddings for {len(texts)} failures...")
    print(f"  Model max sequence length: {model.max_seq_length}")
    print(f"  Device: {model.device}")
    
    # Batch embeddings for efficiency
    batch_size = 16  # Reasonable batch for CPU
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(texts)-1)//batch_size + 1
        print(f"  Batch {batch_num}/{total_batches}...", end='', flush=True)
        
        # Model handles truncation automatically if needed
        embeddings = model.encode(
            batch, 
            convert_to_numpy=True, 
            show_progress_bar=False,
            normalize_embeddings=True
        )
        all_embeddings.append(embeddings)
        print(" ✓")
    
    return np.vstack(all_embeddings)


def get_embeddings(texts, model_key, api_key=None):
    """Get embeddings using specified model"""
    model_name = SUPPORTED_MODELS.get(model_key)
    if not model_name:
        raise ValueError(f"Unknown model: {model_key}. Supported: {list(SUPPORTED_MODELS.keys())}")
    
    if model_key.startswith('openai'):
        if not api_key:
            raise ValueError("OpenAI API key required for OpenAI models")
        return get_embeddings_openai(texts, model_name, api_key)
    else:
        # All other models are local HuggingFace models
        return get_embeddings_local(texts, model_name, model_key)


def cluster_with_hdbscan(embeddings, min_cluster_size=5):
    """
    Cluster using HDBSCAN - auto-discovers number of clusters!
    """
    print(f"\nClustering with HDBSCAN...")
    print(f"  min_cluster_size: {min_cluster_size}")
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric='euclidean',
        cluster_selection_method='eom'  # Excess of Mass
    )
    labels = clusterer.fit_predict(embeddings)
    
    # Count clusters (excluding noise)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = sum(labels == -1)
    
    print(f"  Found {n_clusters} clusters")
    if n_noise > 0:
        print(f"  Noise points: {n_noise} ({100*n_noise/len(labels):.1f}%)")
    
    # Calculate quality metric (excluding noise)
    non_noise = labels != -1
    if len(set(labels[non_noise])) > 1 and sum(non_noise) > 1:
        score = silhouette_score(embeddings[non_noise], labels[non_noise])
        print(f"  Silhouette score: {score:.3f} ", end='')
        if score > 0.7:
            print("(very good!)")
        elif score > 0.5:
            print("(good)")
        elif score > 0.3:
            print("(fair)")
        else:
            print("(poor)")
    else:
        score = 0
    
    return labels, score


def calculate_sample_metrics(embeddings, labels):
    """
    Calculate per-sample metrics for representativeness within clusters.
    
    Returns dict mapping index -> {silhouette, distance_to_centroid, cluster}
    """
    print("\nCalculating per-sample metrics...")
    
    sample_metrics = {}
    
    # Calculate per-sample silhouette scores
    # Note: silhouette_samples returns scores for all points, including noise
    # Noise points get compared to nearest cluster
    silhouette_scores = silhouette_samples(embeddings, labels)
    
    # Calculate cluster centroids
    unique_labels = set(labels)
    centroids = {}
    
    for label in unique_labels:
        if label == -1:
            # Skip centroid for noise (doesn't make sense)
            continue
        mask = labels == label
        centroids[label] = embeddings[mask].mean(axis=0)
    
    # Calculate distance to centroid for each sample
    for idx, (embedding, label) in enumerate(zip(embeddings, labels)):
        silhouette = float(silhouette_scores[idx])
        
        # Distance to centroid (only for non-noise points)
        if label != -1 and label in centroids:
            distance = float(np.linalg.norm(embedding - centroids[label]))
        else:
            # For noise points, use None or a large value
            distance = None
        
        sample_metrics[idx] = {
            'cluster': int(label),
            'silhouette': silhouette,
            'distance_to_centroid': distance
        }
    
    print(f"  ✓ Calculated metrics for {len(sample_metrics)} samples")
    
    return sample_metrics


def print_cluster_summary(labels, signatures):
    """Print detailed cluster summary"""
    print("\n" + "=" * 80)
    print("CLUSTERING RESULTS")
    print("=" * 80)
    
    # Group by label
    clusters = defaultdict(list)
    for label, sig in zip(labels, signatures):
        clusters[label].append(sig)
    
    # Total groups to investigate (including noise as a separate group)
    n_clusters = len(clusters)
    print(f"Total groups to investigate: {n_clusters}")
    print(f"Total failures: {len(signatures)}")
    print()
    
    # Sort by size
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
    
    for i, (label, sigs) in enumerate(sorted_clusters, 1):
        # Analyze cluster composition (support both old and new structure)
        def get_error(sig):
            if 'clustering' in sig:
                return sig['clustering'].get('error_type', 'Unknown')
            return sig.get('error_type', 'Unknown')
        
        errors = set(get_error(sig) for sig in sigs)
        tests = set(sig.get('test_name', 'Unknown') for sig in sigs)
        case_ids = [sig.get('case_id', 'Unknown') for sig in sigs]
        
        # Coherence check
        coherence = "✓" if len(errors) <= 3 else "✗"
        
        print(f"\n{'='*80}")
        print(f"Cluster {i} (Label {label}): {len(sigs)} failures {coherence}")
        print(f"{'='*80}")
        
        # Show error distribution
        print(f"Error types ({len(errors)}):")
        error_counts = defaultdict(int)
        for sig in sigs:
            error_counts[get_error(sig)] += 1
        
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            pct = 100 * count / len(sigs)
            print(f"  • {error[:70]}")
            print(f"    ({count}/{len(sigs)} = {pct:.0f}%)")
        
        if len(error_counts) > 5:
            print(f"  ... and {len(error_counts) - 5} more error types")
        
        # Show test distribution
        print(f"\nTests involved ({len(tests)}):")
        test_counts = defaultdict(int)
        for sig in sigs:
            test_counts[sig.get('test_name', 'Unknown')] += 1
        
        for test, count in sorted(test_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"  • {test}: {count} failures")
        
        # Show sample case IDs
        print(f"\nSample case IDs:")
        for case_id in case_ids[:3]:
            print(f"  • {case_id}")
        if len(case_ids) > 3:
            print(f"  ... and {len(case_ids) - 3} more")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    avg_size = len(signatures) / n_clusters
    print(f"Average cluster size: {avg_size:.1f} failures")
    
    sizes = [len(sigs) for sigs in clusters.values()]
    print(f"Largest cluster: {max(sizes)} failures")
    print(f"Smallest cluster: {min(sizes)} failures")
    
    # Coherence score (support both old and new structure)
    def get_error(sig):
        if 'clustering' in sig:
            return sig['clustering'].get('error_type', 'Unknown')
        return sig.get('error_type', 'Unknown')
    
    coherent = sum(1 for sigs in clusters.values() 
                   if len(set(get_error(sig) for sig in sigs)) <= 3)
    pct_coherent = 100 * coherent / n_clusters
    print(f"Coherent clusters (≤3 error types): {coherent}/{n_clusters} ({pct_coherent:.0f}%)")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Cluster failure signatures using embeddings + HDBSCAN',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use OpenAI (default)
  uv run python3 scripts/cluster_failures.py trace_reports/failure_signature_collection_*.json
  
  # Use local models (no API costs)
  uv run python3 scripts/cluster_failures.py trace_reports/failure_signature_*.json --model modernbert
  uv run python3 scripts/cluster_failures.py trace_reports/failure_signature_*.json --model qwen
  
  # Use OpenAI large model
  uv run python3 scripts/cluster_failures.py trace_reports/failure_signature_*.json --model openai-large
  
  # Adjust min cluster size
  uv run python3 scripts/cluster_failures.py trace_reports/failure_signature_*.json --min-cluster-size 10

Supported models:
  openai-small   : text-embedding-3-small (default, fast, cheap)
  openai-large   : text-embedding-3-large (higher quality, more expensive)
  modernbert     : modernbert-python-code-retrieval (Python code-specialized, local)
  qwen           : Qwen3-Embedding-0.6B (efficient, multilingual, local)
        '''
    )
    
    parser.add_argument('collection_file', type=Path,
                        help='Path to failure signature collection JSON file')
    parser.add_argument('--model', '-m', 
                        choices=list(SUPPORTED_MODELS.keys()),
                        default='openai-small',
                        help='Embedding model to use (default: openai-small)')
    parser.add_argument('--min-cluster-size', type=int, default=5,
                        help='Minimum cluster size for HDBSCAN (default: 5)')
    
    args = parser.parse_args()
    
    if not args.collection_file.exists():
        print(f"Error: File not found: {args.collection_file}")
        sys.exit(1)
    
    # Check for API key if using OpenAI
    api_key = None
    if args.model.startswith('openai'):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("Error: OPENAI_API_KEY not found in environment")
            print("Make sure it's set in your .env file or environment")
            sys.exit(1)
    
    # Load signatures
    print(f"Loading signatures from {args.collection_file}...")
    with open(args.collection_file) as f:
        signatures = json.load(f)
    
    print(f"Loaded {len(signatures)} failure signatures")
    print(f"Model: {args.model} ({SUPPORTED_MODELS[args.model]})")
    print()
    
    # Create embedding texts
    print("Creating embedding texts...")
    texts = [create_embedding_text(sig) for sig in signatures]
    
    # Show sample
    print(f"\nSample embedding text (first 200 chars):")
    print(f"  {texts[0][:200]}...")
    print()
    
    # Get embeddings
    embeddings = get_embeddings(texts, args.model, api_key)
    print(f"Got embeddings: {embeddings.shape}")
    
    # Cluster with HDBSCAN (auto-discovers cluster count)
    labels, score = cluster_with_hdbscan(embeddings, min_cluster_size=args.min_cluster_size)
    
    # Calculate per-sample metrics
    sample_metrics = calculate_sample_metrics(embeddings, labels)
    
    # Print results
    print_cluster_summary(labels, signatures)
    
    # Save results with model name
    model_suffix = f"_{args.model.replace('-', '_')}"
    output_file = args.collection_file.parent / f"{args.collection_file.stem}_clusters{model_suffix}.json"
    
    n_clusters_found = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = sum(labels == -1) if -1 in labels else 0
    
    output_data = {
        'method': 'HDBSCAN',
        'embedding_model': SUPPORTED_MODELS[args.model],
        'min_cluster_size': int(args.min_cluster_size),
        'n_clusters': int(n_clusters_found),
        'n_noise': int(n_noise),
        'silhouette_score': float(score),
        'clusters': {},
        'sample_metrics': {}
    }
    
    for idx, (label, sig) in enumerate(zip(labels, signatures)):
        label_str = 'noise' if label == -1 else str(label)
        if label_str not in output_data['clusters']:
            output_data['clusters'][label_str] = []
        output_data['clusters'][label_str].append(sig['case_id'])
        
        # Add per-sample metrics
        output_data['sample_metrics'][sig['case_id']] = sample_metrics[idx]
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"Cluster assignments saved to: {output_file}")
    print()


if __name__ == '__main__':
    main()
