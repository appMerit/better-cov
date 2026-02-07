# Merit Database

## Overview

Merit automatically creates a SQLite database at `.merit/merit.db` to track test runs, assertions, metrics, and semantic predicates across all test executions.

**Location**: `.merit/merit.db` (168 KB, gitignored)  
**Format**: SQLite 3  
**Purpose**: Historical test analysis, failure clustering, and fix-oriented diagnostics

---

## Database Schema

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| **`runs`** | Test run sessions | `run_id`, `start_time`, `passed/failed/total`, `environment_json` |
| **`test_executions`** | Individual test cases | `execution_id`, `test_name`, `case_id`, `trace_id`, `status`, `duration_ms` |
| **`assertions`** | Test assertions | `expression_repr`, `passed`, `error_message` |
| **`metrics`** | Custom metrics | `name`, `value`, `scope` |
| **`predicates`** | Semantic/LLM assertions | `predicate_name`, `confidence`, `value`, `message` |

### Relationships

```
runs (1) ──→ (N) test_executions ──→ (N) assertions ──→ (N) predicates
                       │                      │
                       └──────→ (N) metrics ──┘
```

---

## Quick Access

### View Tables
```bash
sqlite3 .merit/merit.db ".tables"
```

### See Schema
```bash
sqlite3 .merit/merit.db ".schema"
```

### Interactive Mode
```bash
sqlite3 .merit/merit.db
# Enable column headers and better formatting
.headers on
.mode column
```

---

## Useful Queries

### Failure Rate by Test
```sql
SELECT 
    test_name, 
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failures,
    COUNT(*) as total,
    ROUND(100.0 * SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_rate
FROM test_executions
GROUP BY test_name
ORDER BY failure_rate DESC;
```

### Recent Test Runs
```sql
SELECT 
    run_id, 
    start_time, 
    passed, 
    failed, 
    total,
    ROUND(total_duration_ms / 1000.0, 2) as duration_sec
FROM runs
ORDER BY start_time DESC
LIMIT 10;
```

### Failed Test Details
```sql
SELECT 
    te.test_name,
    te.case_id,
    te.error_message,
    te.trace_id,
    r.start_time
FROM test_executions te
JOIN runs r ON te.run_id = r.run_id
WHERE te.status = 'failed'
ORDER BY r.start_time DESC;
```

### Slowest Tests
```sql
SELECT 
    test_name, 
    ROUND(duration_ms, 2) as duration_ms,
    status,
    case_id
FROM test_executions
ORDER BY duration_ms DESC
LIMIT 20;
```

### Assertion Failures by Pattern
```sql
SELECT 
    expression_repr,
    COUNT(*) as failure_count,
    GROUP_CONCAT(DISTINCT test_name) as failing_tests
FROM assertions a
JOIN test_executions te ON a.test_execution_id = te.execution_id
WHERE a.passed = 0
GROUP BY expression_repr
ORDER BY failure_count DESC;
```

### Semantic Predicate Confidence
```sql
SELECT 
    predicate_name,
    AVG(confidence) as avg_confidence,
    COUNT(*) as total_calls,
    SUM(value) as passed_count
FROM predicates
GROUP BY predicate_name;
```

---

## Use Cases

### 1. **Failure Clustering**
Group similar failures by `case_id`, `error_message`, or `trace_id` to identify fix locations.

```sql
-- Cluster by error message pattern
SELECT 
    CASE 
        WHEN error_message LIKE '%destination%' THEN 'missing_destination'
        WHEN error_message LIKE '%dates%' THEN 'missing_dates'
        WHEN error_message LIKE '%JSON%' THEN 'json_error'
        ELSE 'other'
    END as failure_cluster,
    COUNT(*) as count
FROM test_executions
WHERE status = 'failed'
GROUP BY failure_cluster;
```

### 2. **Historical Trends**
Track test stability over time.

```sql
SELECT 
    DATE(start_time) as date,
    AVG(passed * 1.0 / total) as pass_rate
FROM runs
GROUP BY DATE(start_time)
ORDER BY date DESC;
```

### 3. **Trace Correlation**
Link test failures to OpenTelemetry traces for debugging.

```sql
SELECT test_name, trace_id, error_message
FROM test_executions
WHERE status = 'failed' AND trace_id IS NOT NULL;
```

---

## Maintenance

**Auto-Cleanup**: Merit manages database growth automatically.  
**Manual Reset**: Delete `.merit/merit.db` to start fresh (safe, regenerates on next run).  
**Backup**: Copy `.merit/merit.db` to preserve test history.

---

## Integration with Fix Analyzer

This database provides the failure data needed for fix-oriented clustering:

1. **Failures** → Query `test_executions` where `status = 'failed'`
2. **Cluster** → Group by `error_message` patterns or `case_id`
3. **Map to Code** → Use `PATCH_SURFACE.yml` to identify fix locations
4. **Prioritize** → Sort clusters by `COUNT(*)` to fix high-impact issues first

Example clustering query:

```sql
SELECT 
    -- Extract fault type from test name
    REPLACE(REPLACE(test_name, 'merit_', ''), '_travelops', '') as fault_type,
    COUNT(*) as failure_count,
    GROUP_CONCAT(DISTINCT case_id) as case_ids,
    GROUP_CONCAT(DISTINCT trace_id) as trace_ids
FROM test_executions
WHERE status = 'failed'
GROUP BY fault_type
ORDER BY failure_count DESC;
```

This groups all failures by their fault profile, making it easy to identify which code modules need fixes.
