# Clustering Experiments for Failure Signatures

## Goal
Cluster test failures by **code-fix locus** - group failures requiring the same code fix.

## Current Status ✅
**Production-ready** with Exp 6 approach using **OpenAI text-embedding-3-small**:
- 15 clusters from 267 failures
- 0.602 silhouette score (good separation)
- 100% coherent clusters
- Fast (seconds), reliable

## Quick Start
```bash
# Collect failure signatures
./scripts/collect_all_failures.sh

# Cluster with OpenAI Small (recommended)
uv run python3 scripts/cluster_failures.py \
  trace_reports/failure_signature_collection_*.json \
  --model openai-small --min-cluster-size 5

# Compare all embedding models
uv run python3 scripts/compare_all_models.py trace_reports/
```

---

## Evolution of Approaches

### Experiments 1-2: Dictionary-Based Grouping ❌

**Tried:**
- Exact error matching → 21 clusters (too granular)
- Pattern-based generalization → 14 clusters (better but wrong component)

**Problems:**
- Used TEST span as component, not SUT code location
- No semantic understanding of failures
- Abandoned for embedding-based approach

### Experiments 3-4: Semantic Clustering with Generalization ⚠️

**Approach:** OpenAI embeddings + HDBSCAN + value normalization
- Exp 3: Error + execution path + anomalies → 21 clusters, 86% coherence, 0.804 silhouette
- Exp 4: + assertion expressions → 20 clusters, 85% coherence, 0.838 silhouette

**Key Innovation - Generic Value Generalization:**
```python
# Domain-agnostic patterns that work everywhere
"'long quoted text'" → "'[VALUE]'"
"123" → "[NUM]"
"[a, b, c]" → "[LIST]"
"2026-01-26" → "[DATE]"
```

Works across LLMs, databases, compilers, APIs, web services!

**Achievements:**
- ✅ 85-86% coherence
- ✅ Generic (works for any domain)
- ✅ HDBSCAN auto-discovers cluster count

**Limitations:**
- ⚠️ 20 clusters from 10 fault profiles (clusters by symptom, not root cause)
- ⚠️ Multiple assertions per test split into separate clusters (correct but not ideal)

### Experiment 5: Unified Format for Fix Generation ✅

**Approach:** Dual-purpose signatures with clustering data + fix context

**Added:**
- Full LLM prompts (system + user messages)
- Detailed assertion failures with resolved values
- Complete input/output data for each failure

**Results:** 21 clusters, 90% coherence, 0.815 silhouette

**Status:** Production-ready for AI fix generation (21 clusters = 21 AI calls for 229 failures)

### Experiment 6: Pure Assertion-Based Clustering ✅

**Date:** 2026-01-29  
**Key Innovation:** Use ONLY Merit's rich assertion format as cluster key

**Cluster Key:**
```
Assertion Failed!
│  actual_temp = travel_ops_sut.agent.config.temperature
>  assert (abs(actual_temp - expected_temp) < 0.01), f"..."
╰─ where:
     abs(actual_temp - expected_temp) = 1.8041288098746464

Assertion Passed!
>  assert isinstance(response.itinerary, dict)
╰─ where:
     isinstance(response.itinerary, dict) = True
```

**Results:**
- 15 clusters from 238 failures
- **100% coherence** (best yet!)
- 0.602 silhouette (good)
- Perfect test alignment

**Why It Works:**
- Rich context from Merit's pretty format
- Resolved argument values differentiate similar tests
- Multiple assertions per test naturally split (different fixes needed)
---

## Experiments 7-11: Embedding Model Comparison 🏆

**Date:** 2026-01-29  
**Goal:** Compare embedding models to find best quality/cost/speed trade-off for clustering  
**Method:** Same pure assertion approach as Exp 6, different embedding models

### Models Tested

| Model | Type | Dimensions | Runtime | Cost | Best For |
|-------|------|------------|---------|------|----------|
| `text-embedding-3-small` | OpenAI API | 1536 | seconds | $ | Fast, reliable |
| `text-embedding-3-large` | OpenAI API | 3072 | seconds | $$ | Maximum embeddings |
| `juanwisz/modernbert-python-code-retrieval` | Local HF | 768 | ~5 min | Free (CPU) / $ (hosted) | Python code |
| `google/embeddinggemma-300m` | Local HF (gated) | 256 | ~3 min | Free (CPU) / $ (hosted) | Compact |
| `Qwen/Qwen3-Embedding-0.6B` | Local HF | 896 | ~45 min | Free (CPU) / $ (hosted) | Multilingual |

### Results (267 failures)

| Rank | Model | Silhouette | Clusters | Noise | Agreement w/ OpenAI Small |
|------|-------|------------|----------|-------|--------------------------|
| 1 | qwen | 0.7265 | 15 | 11 (4%) | **100%** ✅ |
| 2 | modernbert | 0.6759 | 17 | 20 (7%) | 99.1% |
| 3 | **openai_small** | **0.6021** | **15** | **0 (0%)** ✅ | **-** |
| 4 | gemma | 0.5979 | 17 | 4 (1%) | 98.8% |
| 5 | openai_large | 0.5883 | 14 | 4 (1%) | 99.6% |

### Critical Finding: Near-Identical Clustering Between Qwen and OpenAI Small

**Qwen and OpenAI Small produce nearly identical cluster assignments** (100% agreement on non-noise points)!

**Practical Difference:**
- **Qwen**: 15 clusters + 11 noise points = **16 groups to investigate**
- **OpenAI Small**: 15 clusters + 0 noise = **15 groups to investigate**
- Non-noise assignments are 100% identical
- Silhouette difference = internal cluster density, not clustering quality

### Key Findings

✅ **Winner: OpenAI text-embedding-3-small**
- **100% agreement with Qwen on non-noise assignments**
- **500x faster** (seconds vs 45 minutes on CPU)
- **15 groups to investigate** (vs 16 for Qwen - 11 noise points become separate group)
- **0 noise points** = all failures clearly clustered
- Lower silhouette (0.6021) doesn't matter since cluster assignments are identical
- Cost-effective for production use

✅ **High Agreement Across All Models (98-100%)**
- All models produce nearly identical clusterings
- Suggests robust, underlying patterns in the data
- Choice of model has minimal impact on cluster assignments

✅ **Local Models Have Higher Silhouette But Slower**
- Qwen: Best silhouette (0.7265) but 45 min runtime on CPU
- ModernBERT: Good silhouette (0.6759) but 5 min runtime
- Both require GPU or hosted inference for production speed
- Cost of hosted inference ≈ OpenAI API cost

### Recommendation

**Use OpenAI text-embedding-3-small** for production clustering:
- ✅ Fast (seconds, not minutes)
- ✅ Same clustering as best model (100% agreement with Qwen)
- ✅ Zero noise points
- ✅ Reliable, established API
- ✅ Cost-effective (cheaper than hosting Qwen with GPU)

**Usage:**
```bash
uv run python3 scripts/cluster_failures.py \
  trace_reports/failure_signature_collection_*.json \
  --model openai-small \
  --min-cluster-size 5
```

**Compare All Models:**
```bash
uv run python3 scripts/compare_all_models.py trace_reports/
```

**Alternative:** If you have GPU infrastructure, Qwen offers highest silhouette with same clustering.

See `EMBEDDING_MODEL_COMPARISON.md` for detailed comparison methodology.

---

## Summary Table

| Experiment | Embedding Model | Features | Clusters | Coherence | Silhouette | Runtime | Status |
|------------|----------------|----------|----------|-----------|------------|---------|--------|
| 1 | None | Exact error + component | 21 | N/A | N/A | instant | ❌ |
| 2 | None | Generalized error + component | 14 | N/A | N/A | instant | ❌ |
| 3 | text-embedding-3-small | Error + flow + anomalies | 21 | 86% | 0.804 | seconds | ⚠️ |
| 4 | text-embedding-3-small | + assertion expressions | 20 | 85% | 0.838 | seconds | ⚠️ |
| 5 | text-embedding-3-small | Enriched fix context | 21 | 90% | 0.815 | seconds | ✅ |
| **6** | **text-embedding-3-small** | **Pure assertions (pretty)** | **15** | **100%** | **0.602** | **seconds** | **✅** |
| **7-11** | **5 models compared** | **Pure assertions (pretty)** | **14-17** | **100%** | **0.588-0.726** | **secs-45min** | **✅** |

**Final Recommendation:** Use Exp 6 approach with **OpenAI text-embedding-3-small** for best speed/quality trade-off
- **100% agreement** with highest-performing model (Qwen)
- **500x faster** runtime (seconds vs 45 minutes on CPU)
- **Zero noise** points
- Cost-effective for production
