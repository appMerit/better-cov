#!/bin/bash
set -e

# Compare clustering results across different embedding models

if [ "$#" -lt 1 ]; then
    echo "Usage: ./scripts/compare_embedding_models.sh <failure_signature_collection.json>"
    echo ""
    echo "This will:"
    echo "  1. Cluster with OpenAI text-embedding-3-small"
    echo "  2. Cluster with Salesforce SFR-Embedding-Code-400M_R"
    echo "  3. Generate comparison report"
    echo ""
    echo "Example:"
    echo "  ./scripts/compare_embedding_models.sh trace_reports/failure_signature_collection_20260129_053152.json"
    exit 1
fi

COLLECTION_FILE="$1"
MIN_CLUSTER_SIZE="${2:-5}"

if [ ! -f "$COLLECTION_FILE" ]; then
    echo "Error: File not found: $COLLECTION_FILE"
    exit 1
fi

echo "=========================================="
echo "Embedding Model Comparison"
echo "=========================================="
echo "Collection: $COLLECTION_FILE"
echo "Min cluster size: $MIN_CLUSTER_SIZE"
echo ""

# Run OpenAI clustering
echo "=========================================="
echo "Step 1: Clustering with OpenAI (text-embedding-3-small)"
echo "=========================================="
uv run python3 scripts/cluster_failures.py "$COLLECTION_FILE" \
    --model openai-small \
    --min-cluster-size "$MIN_CLUSTER_SIZE"
echo ""

# Run ModernBERT clustering
echo "=========================================="
echo "Step 2: Clustering with ModernBERT (modernbert-python-code-retrieval)"
echo "=========================================="
uv run python3 scripts/cluster_failures.py "$COLLECTION_FILE" \
    --model modernbert \
    --min-cluster-size "$MIN_CLUSTER_SIZE"
echo ""

# Generate comparison
echo "=========================================="
echo "Step 3: Comparison Report"
echo "=========================================="

BASENAME=$(basename "$COLLECTION_FILE" .json)
DIRNAME=$(dirname "$COLLECTION_FILE")
OPENAI_FILE="${DIRNAME}/${BASENAME}_clusters_openai_small.json"
MODERNBERT_FILE="${DIRNAME}/${BASENAME}_clusters_modernbert.json"

echo ""
echo "OpenAI Results:"
cat "$OPENAI_FILE" | jq '{
  model: .embedding_model,
  n_clusters: .n_clusters,
  n_noise: .n_noise,
  silhouette_score: .silhouette_score
}'

echo ""
echo "ModernBERT Results:"
cat "$MODERNBERT_FILE" | jq '{
  model: .embedding_model,
  n_clusters: .n_clusters,
  n_noise: .n_noise,
  silhouette_score: .silhouette_score
}'

echo ""
echo "Comparison Summary:"
echo "==================="

OPENAI_CLUSTERS=$(jq -r '.n_clusters' "$OPENAI_FILE")
MODERNBERT_CLUSTERS=$(jq -r '.n_clusters' "$MODERNBERT_FILE")
OPENAI_SCORE=$(jq -r '.silhouette_score' "$OPENAI_FILE")
MODERNBERT_SCORE=$(jq -r '.silhouette_score' "$MODERNBERT_FILE")

echo "Number of Clusters:"
echo "  OpenAI:      $OPENAI_CLUSTERS"
echo "  ModernBERT:  $MODERNBERT_CLUSTERS"
echo ""
echo "Silhouette Score (higher is better, max 1.0):"
echo "  OpenAI:      $OPENAI_SCORE"
echo "  ModernBERT:  $MODERNBERT_SCORE"
echo ""

# Determine winner
if (( $(echo "$MODERNBERT_SCORE > $OPENAI_SCORE" | bc -l) )); then
    echo "🏆 Winner: ModernBERT (better separation)"
elif (( $(echo "$OPENAI_SCORE > $MODERNBERT_SCORE" | bc -l) )); then
    echo "🏆 Winner: OpenAI (better separation)"
else
    echo "🤝 Tie: Both models have equal silhouette scores"
fi
echo ""

echo "Full results saved to:"
echo "  $OPENAI_FILE"
echo "  $MODERNBERT_FILE"
echo ""
