---
name: databricks-cost-optimizer
description: Analyze Databricks costs and find optimization opportunities using system tables.
disable-model-invocation: true
---

# Databricks Cost Optimizer

Systematic cost optimization analysis using Databricks system tables. Follows a highest-impact-first framework derived from real customer engagements.

## Prerequisites

- Databricks CLI configured OR Databricks DBSQL MCP server connected
- Access to `system.billing`, `system.compute`, `system.lakeflow`, and `system.query` schemas
- Unity Catalog enabled workspace

## Critical: Query Performance

**Always filter on `usage_date` in `system.billing.usage`.** This column is the partition key. Without it, queries trigger full table scans and will time out on any account with meaningful usage.

```sql
-- SLOW (full scan):
WHERE usage_start_time >= '2026-01-01'

-- FAST (partition pruning):
WHERE usage_date >= '2026-01-01'
```

## Analysis Framework

Run these analyses in order. Each builds on the previous.

```
 1. Spend Overview           → Where is money going?
 2. ALL_PURPOSE vs JOBS      → Biggest rate arbitrage
 3. Cluster Cost Attribution → Which clusters cost most?
 4. Jobs on ALL_PURPOSE      → Migration candidates
 5. Cluster Utilization      → Right-sizing
 6. Failing Jobs             → Waste
 7. Continuous Clusters      → Always-on spend
 8. SQL Warehouse Analysis   → Query-level cost + sizing
 9. Streaming Job Efficiency → 24/7 compute that doesn't need to be
10. Idle Cluster Detection   → Auto-termination gaps
11. Delta Table Optimization → Reduce DBUs per query
12. Tagging & Governance     → Attribution gaps
13. DBR Version Audit        → EOL risk + perf
14. Networking & Storage     → Often overlooked
```

---

## 1. Spend Overview

**What to look for:** Total spend by product type and SKU. Establishes baseline and identifies dominant cost categories.

```sql
SELECT
  product_type,
  sku_name,
  SUM(usage_quantity) AS total_dbus,
  SUM(usage_quantity * p.pricing.default) AS est_list_cost_usd,
  ROUND(SUM(usage_quantity) / SUM(SUM(usage_quantity)) OVER () * 100, 1) AS pct_of_total
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 90 DAYS
GROUP BY product_type, sku_name
ORDER BY total_dbus DESC
```

**How to interpret:**
- ALL_PURPOSE > 30% of total = likely optimization opportunity (should be JOBS)
- SQL > JOBS = unusual unless analytics-heavy org
- Look for unexpected SKUs (NETWORKING, STORAGE) as % of total

---

## 2. ALL_PURPOSE vs JOBS Rate Gap

**What to look for:** The price per DBU for ALL_PURPOSE is typically 3-4x higher than JOBS compute. Any scheduled workload running on ALL_PURPOSE is overpaying.

```sql
SELECT
  sku_name,
  ROUND(AVG(p.pricing.default), 4) AS list_rate_per_dbu
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND u.sku_name LIKE '%ALL_PURPOSE%' OR u.sku_name LIKE '%JOBS%'
GROUP BY sku_name
ORDER BY list_rate_per_dbu DESC
```

**Typical rates (list price):**
| SKU | Typical Rate |
|-----|-------------|
| ALL_PURPOSE (classic) | $0.55/DBU |
| ALL_PURPOSE (Photon) | $0.55/DBU |
| JOBS (classic) | $0.15/DBU |
| JOBS (Photon) | $0.15/DBU |
| JOBS (serverless) | ~$0.07/DBU (varies by region) |

**Red flag:** If ALL_PURPOSE DBUs > JOBS DBUs, investigate why.

---

## 3. Cluster-Level Cost Attribution

**What to look for:** Which specific clusters consume the most DBUs. Identifies the top targets for optimization.

```sql
SELECT
  u.usage_metadata.cluster_id AS cluster_id,
  u.sku_name,
  SUM(u.usage_quantity) AS total_dbus,
  SUM(u.usage_quantity * p.pricing.default) AS est_list_cost_usd,
  MIN(u.usage_date) AS first_seen,
  MAX(u.usage_date) AS last_seen,
  COUNT(DISTINCT u.usage_date) AS active_days
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 90 DAYS
  AND u.sku_name LIKE '%ALL_PURPOSE%'
GROUP BY u.usage_metadata.cluster_id, u.sku_name
ORDER BY total_dbus DESC
LIMIT 20
```

**Then enrich with cluster metadata:**

```sql
SELECT
  cluster_id,
  cluster_name,
  dbr_version,
  driver_node_type,
  worker_node_type,
  cluster_source,
  change_time
FROM system.compute.clusters
WHERE cluster_id = '<CLUSTER_ID>'
ORDER BY change_time DESC
LIMIT 5
```

**How to interpret:**
- `cluster_source = 'UI'` = manually created (likely interactive)
- `cluster_source = 'API'` = orchestrator-managed (Airflow, etc.)
- `cluster_source = 'JOB'` = job cluster (already on JOBS pricing)
- `active_days` close to 90 = always-on cluster

---

## 4. Jobs Running on ALL_PURPOSE Clusters

**What to look for:** Jobs using "existing cluster" configuration run at ALL_PURPOSE rates instead of JOBS rates. These are the easiest migration wins.

**Key insight:** When a job runs on an existing ALL_PURPOSE cluster, `billing.usage` records the DBUs with `job_id = NULL` because billing attributes to the cluster, not the job. Use `lakeflow_job_task_run_timeline.compute_ids` to link jobs to clusters.

```sql
SELECT
  t.job_id,
  j.name AS job_name,
  COUNT(DISTINCT t.run_id) AS total_runs,
  SUM(CASE WHEN t.result_state = 'SUCCEEDED' THEN 1 ELSE 0 END) AS succeeded,
  SUM(CASE WHEN t.result_state IN ('ERROR', 'FAILED') THEN 1 ELSE 0 END) AS failed,
  MIN(t.period_start_time) AS first_run,
  MAX(t.period_end_time) AS last_run
FROM system.lakeflow.job_task_run_timeline t
JOIN system.lakeflow.jobs j
  ON t.workspace_id = j.workspace_id AND t.job_id = j.job_id
WHERE ARRAY_CONTAINS(t.compute_ids, '<ALL_PURPOSE_CLUSTER_ID>')
  AND t.period_start_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY t.job_id, j.name
ORDER BY total_runs DESC
```

**Migration assessment:**
- High-frequency jobs (1000+ runs/month) = high savings potential
- Jobs with few runs but long duration = also worthwhile
- Interactive notebook work = cannot migrate (legitimate ALL_PURPOSE use)

**Migration paths:**
1. **Dedicated job cluster** — best for long-running jobs, cluster stays warm per run
2. **Serverless jobs** — best for short jobs, near-instant startup, cheapest rate
3. **Continuous job** — best for micro-batch patterns (many short runs), keeps cluster warm at JOBS rate

---

## 5. Cluster Utilization (Right-Sizing)

**What to look for:** CPU, memory, and swap metrics to determine if clusters are over- or under-provisioned.

```sql
SELECT
  driver,
  ROUND(AVG(cpu_user_percent + cpu_system_percent), 1) AS avg_cpu_pct,
  ROUND(PERCENTILE(cpu_user_percent + cpu_system_percent, 0.50), 1) AS p50_cpu_pct,
  ROUND(PERCENTILE(cpu_user_percent + cpu_system_percent, 0.95), 1) AS p95_cpu_pct,
  ROUND(MAX(cpu_user_percent + cpu_system_percent), 1) AS max_cpu_pct,
  ROUND(AVG(mem_used_percent), 1) AS avg_mem_pct,
  ROUND(PERCENTILE(mem_used_percent, 0.95), 1) AS p95_mem_pct,
  ROUND(MAX(mem_used_percent), 1) AS max_mem_pct,
  ROUND(AVG(mem_swap_percent), 2) AS avg_swap_pct,
  ROUND(AVG(cpu_wait_percent), 2) AS avg_io_wait_pct
FROM system.compute.node_timeline
WHERE cluster_id = '<CLUSTER_ID>'
  AND start_time >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY driver
ORDER BY driver
```

**Hourly pattern (find idle periods):**

```sql
SELECT
  HOUR(start_time) AS hour_utc,
  ROUND(AVG(cpu_user_percent + cpu_system_percent), 1) AS avg_cpu_pct,
  ROUND(AVG(mem_used_percent), 1) AS avg_mem_pct
FROM system.compute.node_timeline
WHERE cluster_id = '<CLUSTER_ID>'
  AND start_time >= CURRENT_DATE - INTERVAL 7 DAYS
  AND driver = false
GROUP BY HOUR(start_time)
ORDER BY hour_utc
```

### Interpretation Thresholds

| Metric | Value | Meaning | Action |
|--------|-------|---------|--------|
| **Avg CPU < 20%** | Severely oversized | Reduce instance size or worker count |
| **Avg CPU 20-40%** | Moderately oversized | Consider smaller instances |
| **Avg CPU 40-70%** | Well-sized | No change needed |
| **P95 CPU > 85%** | CPU-constrained at peaks | Don't shrink, may need to grow |
| **Avg Memory < 30%** | Memory over-provisioned | Switch to compute-optimized family (c5/c6) |
| **P95 Memory > 80%** | Memory-tight | Don't reduce, consider memory-optimized (r5/r6) |
| **Max Memory > 95%** | Memory-critical | Increase instance size or add workers |
| **Swap > 0%** | Memory-constrained | Workload exceeding RAM, increase memory |
| **Swap > 10%** | Severe memory pressure | Urgent: larger instances or more workers |
| **IO Wait > 5%** | Storage-bound | Consider SSD-backed instances (i3/i4i) |

### Instance Family Guide

| Family | Strength | Use When |
|--------|----------|----------|
| **c5/c6** (compute) | High CPU, low memory | CPU-bound, memory < 30% |
| **m5/m6** (general) | Balanced | Moderate CPU and memory |
| **r5/r6** (memory) | High memory | Memory > 60%, or shuffle-heavy |
| **i3/i4i** (storage) | NVMe SSD | IO-bound, large shuffles, ML with disk cache |

---

## 6. Failing Jobs Analysis

**What to look for:** Jobs with high failure rates waste compute on retries. Combined with always-on clusters, this compounds cost.

```sql
WITH job_stats AS (
  SELECT
    r.job_id,
    j.name AS job_name,
    COUNT(DISTINCT r.run_id) AS total_runs,
    SUM(CASE WHEN r.result_state = 'SUCCEEDED' THEN 1 ELSE 0 END) AS succeeded,
    SUM(CASE WHEN r.result_state IN ('ERROR', 'FAILED') THEN 1 ELSE 0 END) AS failed
  FROM system.lakeflow.job_run_timeline r
  JOIN system.lakeflow.jobs j
    ON r.workspace_id = j.workspace_id AND r.job_id = j.job_id
  WHERE r.period_start_time >= CURRENT_DATE - INTERVAL 30 DAYS
    AND r.result_state IS NOT NULL
  GROUP BY r.job_id, j.name
)
SELECT
  *,
  ROUND(failed * 100.0 / NULLIF(failed + succeeded, 0), 1) AS error_rate_pct
FROM job_stats
WHERE failed > 5
ORDER BY failed DESC
LIMIT 30
```

**Cost of failed runs (for jobs with their own job clusters):**

```sql
SELECT
  u.usage_metadata.job_id AS job_id,
  u.sku_name,
  SUM(u.usage_quantity) AS total_dbus,
  SUM(u.usage_quantity * p.pricing.default) AS est_wasted_cost_usd
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND u.usage_metadata.job_id = '<JOB_ID>'
GROUP BY u.usage_metadata.job_id, u.sku_name
```

**Thresholds:**
- Error rate > 50% = investigate root cause
- Error rate > 90% = critical waste, likely broken job
- Failed jobs on shared ALL_PURPOSE clusters won't appear in billing by job_id — they consume cluster DBUs without attribution

---

## 7. Continuous / Always-On Cluster Detection

**What to look for:** Clusters running 24/7 that could be shut down during off-hours or replaced with auto-terminating job clusters.

```sql
SELECT
  cluster_id,
  COUNT(DISTINCT DATE(start_time)) AS active_days,
  COUNT(DISTINCT HOUR(start_time)) AS distinct_hours,
  MIN(start_time) AS earliest,
  MAX(end_time) AS latest,
  ROUND(AVG(cpu_user_percent + cpu_system_percent), 1) AS avg_cpu_pct
FROM system.compute.node_timeline
WHERE start_time >= CURRENT_DATE - INTERVAL 7 DAYS
  AND driver = false
GROUP BY cluster_id
HAVING active_days = 7
ORDER BY distinct_hours DESC
```

**Red flags:**
- `active_days = 7` AND `distinct_hours = 24` = truly 24/7
- Low avg CPU (< 20%) on an always-on cluster = massive waste
- Check if jobs on these clusters actually need continuous processing or could run on a schedule

**Micro-batch detection:** If a cluster runs thousands of short job runs per day (visible via analysis #4), it's likely a micro-batch pattern using an existing cluster to avoid startup latency. The fix is a **continuous job** on a JOBS cluster — same warm-cluster benefit at ~3.7x lower rate.

---

## 8. SQL Warehouse Analysis

**What to look for:** Expensive queries, undersized warehouses causing disk spill, and oversized warehouses sitting idle. Uses `system.query.history`.

### Top expensive queries

```sql
SELECT
  warehouse_id,
  statement_id,
  SUBSTRING(statement_text, 1, 200) AS query_preview,
  total_duration_ms,
  rows_produced,
  ROUND(bytes_read / 1073741824, 2) AS gb_read,
  ROUND(spilled_local_bytes / 1073741824, 2) AS gb_spilled,
  execution_status,
  start_time
FROM system.query.history
WHERE start_time >= CURRENT_DATE - INTERVAL 30 DAYS
ORDER BY total_duration_ms DESC
LIMIT 25
```

### Disk spill detection (warehouse undersizing)

Spill means a query ran out of memory and wrote intermediate results to disk — it still succeeds but runs slower and burns more DBUs. Consistent spill = warehouse is too small for its workload.

```sql
SELECT
  warehouse_id,
  COUNT(*) AS total_queries,
  SUM(CASE WHEN spilled_local_bytes > 0 THEN 1 ELSE 0 END) AS spill_queries,
  ROUND(SUM(CASE WHEN spilled_local_bytes > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS spill_pct,
  ROUND(SUM(spilled_local_bytes) / 1073741824, 1) AS total_spill_gb,
  ROUND(AVG(CASE WHEN spilled_local_bytes > 0 THEN total_duration_ms END), 0) AS avg_spill_query_ms
FROM system.query.history
WHERE start_time >= CURRENT_DATE - INTERVAL 30 DAYS
  AND execution_status = 'FINISHED'
GROUP BY warehouse_id
HAVING spill_queries > 0
ORDER BY total_spill_gb DESC
```

**Thresholds:**
- Spill rate > 10% of queries = warehouse likely undersized, increase T-shirt size
- Spill rate < 1% with low query volume = warehouse may be oversized, try downsizing
- Individual queries > 10 GB spill = candidate for query rewrite or table optimization

### Warehouse utilization (idle cost)

Compare actual query execution time to total warehouse uptime. Low ratios mean you're paying for idle compute.

```sql
SELECT
  warehouse_id,
  COUNT(*) AS total_queries,
  ROUND(SUM(total_duration_ms) / 3600000, 1) AS total_query_hours,
  ROUND(SUM(total_duration_ms) / 1000 /
    NULLIF(TIMESTAMPDIFF(SECOND, MIN(start_time), MAX(start_time)), 0) * 100, 1) AS utilization_pct,
  MIN(start_time) AS first_query,
  MAX(start_time) AS last_query
FROM system.query.history
WHERE start_time >= CURRENT_DATE - INTERVAL 7 DAYS
  AND execution_status = 'FINISHED'
GROUP BY warehouse_id
ORDER BY total_query_hours DESC
```

**How to interpret:**
- `utilization_pct` < 5% = warehouse is mostly idle, review auto-stop settings or consolidate with another warehouse
- Warehouses with no queries in 7+ days = candidate for removal
- High query volume with high spill = scale up the warehouse size
- Low query volume with zero spill on a large warehouse = scale down

### Frequently failing queries

```sql
SELECT
  warehouse_id,
  SUBSTRING(statement_text, 1, 200) AS query_preview,
  COUNT(*) AS executions,
  SUM(CASE WHEN execution_status = 'FAILED' THEN 1 ELSE 0 END) AS failures,
  ROUND(SUM(CASE WHEN execution_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS failure_pct
FROM system.query.history
WHERE start_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY warehouse_id, SUBSTRING(statement_text, 1, 200)
HAVING failures > 5
ORDER BY failures DESC
LIMIT 20
```

---

## 9. Streaming Job Efficiency

**What to look for:** Streaming jobs that run 24/7 on always-on compute but don't actually need real-time latency. These are candidates for `Trigger.AvailableNow` which processes incrementally on a schedule instead of continuously, allowing compute to scale down between batches.

### Detect long-running streaming jobs

Streaming jobs appear as single runs with very long durations — hours or days for one run, as opposed to batch jobs which complete in minutes.

```sql
SELECT
  r.job_id,
  j.name AS job_name,
  r.run_id,
  r.period_start_time,
  r.period_end_time,
  ROUND(TIMESTAMPDIFF(MINUTE, r.period_start_time, r.period_end_time) / 60.0, 1) AS duration_hours,
  r.result_state
FROM system.lakeflow.job_run_timeline r
JOIN system.lakeflow.jobs j
  ON r.workspace_id = j.workspace_id AND r.job_id = j.job_id
WHERE r.period_start_time >= CURRENT_DATE - INTERVAL 7 DAYS
  AND TIMESTAMPDIFF(HOUR, r.period_start_time, r.period_end_time) > 12
ORDER BY duration_hours DESC
LIMIT 20
```

### Measure streaming job cost

```sql
SELECT
  u.usage_metadata.job_id AS job_id,
  u.sku_name,
  SUM(u.usage_quantity) AS total_dbus,
  SUM(u.usage_quantity * p.pricing.default) AS est_list_cost,
  COUNT(DISTINCT u.usage_date) AS active_days,
  ROUND(SUM(u.usage_quantity) / COUNT(DISTINCT u.usage_date), 0) AS avg_daily_dbus
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND u.usage_metadata.job_id IN ('<STREAMING_JOB_ID_1>', '<STREAMING_JOB_ID_2>')
GROUP BY u.usage_metadata.job_id, u.sku_name
ORDER BY total_dbus DESC
```

**How to interpret:**
- A streaming job running 24/7 with consistent daily DBUs = continuous trigger
- Ask: does this workload actually need sub-minute latency?
- If SLA is >= 5 minutes: switch to `Trigger.AvailableNow` on a cron schedule. Compute spins up, processes all available data, then shuts down. Can reduce cost by 50-80% depending on data arrival rate.
- If SLA is truly real-time: leave as continuous, but ensure it's on JOBS compute (not ALL_PURPOSE) and consider serverless

**Common pattern:** Teams start with continuous streaming during development, then never revisit the trigger mode for production even when the business only needs 5-15 minute freshness.

---

## 10. Idle Cluster Detection (Auto-Termination Gaps)

**What to look for:** Interactive clusters that run for hours with no meaningful work. These often lack auto-termination or have it set too high.

### Find clusters with extended idle periods

```sql
SELECT
  cluster_id,
  DATE(start_time) AS day,
  COUNT(*) AS data_points,
  ROUND(AVG(cpu_user_percent + cpu_system_percent), 1) AS avg_cpu_pct,
  SUM(CASE WHEN (cpu_user_percent + cpu_system_percent) < 5 THEN 1 ELSE 0 END) AS idle_points,
  ROUND(SUM(CASE WHEN (cpu_user_percent + cpu_system_percent) < 5 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS idle_pct
FROM system.compute.node_timeline
WHERE start_time >= CURRENT_DATE - INTERVAL 7 DAYS
  AND driver = true
GROUP BY cluster_id, DATE(start_time)
HAVING idle_pct > 50
ORDER BY idle_pct DESC
```

**Why driver node:** The driver is always active when the cluster is running. If the driver's CPU is < 5%, nothing is happening on the cluster — it's burning money sitting idle.

### Cross-reference with billing

```sql
SELECT
  u.usage_metadata.cluster_id AS cluster_id,
  c.cluster_name,
  SUM(u.usage_quantity) AS total_dbus,
  SUM(u.usage_quantity * p.pricing.default) AS est_idle_cost,
  COUNT(DISTINCT u.usage_date) AS active_days
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
LEFT JOIN (
  SELECT cluster_id, cluster_name,
    ROW_NUMBER() OVER (PARTITION BY cluster_id ORDER BY change_time DESC) AS rn
  FROM system.compute.clusters
) c ON u.usage_metadata.cluster_id = c.cluster_id AND c.rn = 1
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND u.sku_name LIKE '%ALL_PURPOSE%'
  AND u.usage_metadata.cluster_id IN ('<IDLE_CLUSTER_IDS>')
GROUP BY u.usage_metadata.cluster_id, c.cluster_name
ORDER BY est_idle_cost DESC
```

**Recommendations:**
- Set auto-termination to 30 minutes for development clusters, 1 hour maximum
- For clusters only needed during business hours, combine auto-termination with a scheduled restart
- If a cluster is idle > 50% of the time, it should NOT be always-on
- Consider serverless compute for interactive/exploratory work — it starts in seconds and stops automatically

---

## 11. Delta Table Optimization

**What to look for:** Tables where queries scan far more data than they return, indicating poor data layout — missing clustering, too many small files, or stale statistics. Optimizing these tables reduces DBUs consumed per query.

**Approach:** System tables can't directly show file counts or clustering config. Instead, use a two-step method: (1) identify candidate tables from query patterns, (2) inspect them individually.

### Step 1: Find tables with high scan-to-result ratios

Tables where queries read significantly more data than they produce are candidates for clustering or OPTIMIZE. This indicates poor data skipping.

```sql
SELECT
  REGEXP_EXTRACT(statement_text, '(?i)FROM\\s+([\\w.]+)', 1) AS table_name,
  COUNT(*) AS query_count,
  ROUND(AVG(bytes_read / 1073741824), 2) AS avg_gb_read,
  ROUND(AVG(rows_produced), 0) AS avg_rows_returned,
  ROUND(SUM(bytes_read) / NULLIF(SUM(rows_produced), 0), 0) AS bytes_per_row,
  ROUND(SUM(total_duration_ms) / 3600000, 1) AS total_query_hours
FROM system.query.history
WHERE start_time >= CURRENT_DATE - INTERVAL 30 DAYS
  AND execution_status = 'FINISHED'
  AND bytes_read > 0
  AND rows_produced > 0
GROUP BY REGEXP_EXTRACT(statement_text, '(?i)FROM\\s+([\\w.]+)', 1)
HAVING query_count >= 10
ORDER BY bytes_per_row DESC
LIMIT 20
```

**How to interpret:**
- `bytes_per_row` > 10 MB = extremely poor data skipping, high-priority optimization candidate
- `bytes_per_row` > 1 MB = likely benefiting from clustering on filter columns
- High `total_query_hours` + high `bytes_per_row` = biggest bang for optimization buck
- Tables with many queries (`query_count`) benefit most from optimization since every query gets faster

### Step 2: Check if predictive optimization is running

`system.storage.predictive_optimization_operations_history` shows what automated maintenance has been performed. Tables NOT appearing may not have predictive optimization enabled.

```sql
SELECT
  table_name,
  operation_type,
  COUNT(*) AS operations,
  MAX(start_time) AS last_run,
  SUM(CASE WHEN operation_status = 'SUCCESSFUL' THEN 1 ELSE 0 END) AS succeeded,
  SUM(CASE WHEN operation_status = 'FAILED' THEN 1 ELSE 0 END) AS failed
FROM system.storage.predictive_optimization_operations_history
WHERE start_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY table_name, operation_type
ORDER BY table_name, operation_type
```

### Step 3: Inspect top candidates (per-table)

For each high-priority table from Step 1, run:

```sql
DESCRIBE DETAIL <catalog>.<schema>.<table>;
-- Check: numFiles (small file problem if >1000 with small avgFileSize)

DESCRIBE TABLE EXTENDED <catalog>.<schema>.<table>;
-- Check: clusteringColumns, partitioning, table properties

SHOW TBLPROPERTIES <catalog>.<schema>.<table>;
-- Check: delta.autoOptimize.autoCompact, delta.autoOptimize.optimizeWrite
```

**Optimization actions by finding:**

| Finding | Action |
|---------|--------|
| Many small files (1000+ files, avg < 100 MB) | Run `OPTIMIZE` to compact. Enable auto-compaction. |
| No clustering keys on a frequently filtered table | Add liquid clustering on common filter columns |
| High bytes_per_row but table has clustering | Clustering keys may not match query patterns — review common WHERE clauses |
| VACUUM never run (check table history) | Schedule regular VACUUM to clean up stale files and reduce storage costs |
| Predictive optimization not running | Enable at catalog level: `ALTER CATALOG <name> ENABLE PREDICTIVE OPTIMIZATION` |

---

## 12. Tagging & Governance Audit

**What to look for:** Resources without cost attribution tags. Untagged compute makes it impossible to do chargeback, identify ownership, or hold teams accountable for spend.

```sql
SELECT
  sku_name,
  usage_metadata.cluster_id AS cluster_id,
  custom_tags,
  SUM(usage_quantity) AS total_dbus,
  SUM(usage_quantity * p.pricing.default) AS est_cost
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND u.sku_name LIKE '%ALL_PURPOSE%'
  AND (u.custom_tags IS NULL OR SIZE(u.custom_tags) = 0)
GROUP BY sku_name, usage_metadata.cluster_id, custom_tags
ORDER BY est_cost DESC
LIMIT 20
```

**What good tagging looks like:**
- Minimum tags: `team`/`business_unit`, `project`/`cost_center`, `environment` (dev/staging/prod)
- Tags propagate to billing system tables automatically
- Budget policies can enforce tagging for serverless compute

**Recommendations:**
- Compute policies can enforce required tags at cluster creation time
- Budget policies assign tags to serverless workloads automatically
- Set up budget alerts per team/project to catch spend anomalies early
- Schedule monthly tag audit to catch drift

---

## 13. DBR Version Audit

**What to look for:** Clusters running end-of-life Databricks Runtime versions miss performance improvements, security patches, and new features.

```sql
SELECT
  cluster_id,
  cluster_name,
  dbr_version,
  driver_node_type,
  worker_node_type,
  MAX(change_time) AS last_config_change
FROM system.compute.clusters
WHERE change_time >= CURRENT_DATE - INTERVAL 90 DAYS
  AND delete_time IS NULL
GROUP BY cluster_id, cluster_name, dbr_version, driver_node_type, worker_node_type
ORDER BY dbr_version ASC
```

**DBR LTS Lifecycle (approximate):**
- Each LTS version is supported ~12 months after release
- Running 2+ major versions behind = EOL
- DBR 13.3 LTS → EOL ~mid 2024
- DBR 14.3 LTS → EOL ~early 2025
- DBR 15.4 LTS → EOL ~September 2025
- DBR 16.x LTS → current

**Impact of upgrading:**
- Photon improvements: 10-30% faster on compatible workloads
- Spark engine improvements: better join strategies, adaptive query execution
- Security patches: compliance requirement for many orgs

---

## 14. Networking & Storage Costs

**What to look for:** Often overlooked costs that can spike unexpectedly.

```sql
SELECT
  sku_name,
  SUM(usage_quantity) AS total_units,
  SUM(usage_quantity * p.pricing.default) AS est_cost_usd,
  MIN(usage_date) AS first_seen,
  MAX(usage_date) AS last_seen
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.cloud = p.cloud
  AND u.usage_start_time >= p.price_start_time
  AND (p.price_end_time IS NULL OR u.usage_start_time < p.price_end_time)
WHERE u.usage_date >= CURRENT_DATE - INTERVAL 30 DAYS
  AND (u.sku_name LIKE '%CONNECTIVITY%'
    OR u.sku_name LIKE '%EGRESS%'
    OR u.sku_name LIKE '%STORAGE%'
    OR u.sku_name LIKE '%NETWORK%')
GROUP BY u.sku_name
ORDER BY est_cost_usd DESC
```

**Networking:**
- `PUBLIC_CONNECTIVITY_DATA_PROCESSED` = data transfer for serverless compute. Check `source_region` and `destination_region` in billing metadata to determine direction.
- Spikes with `source_region=INTERNET` and no associated job = bulk data ingestion
- Inter-region egress = cross-region data movement (consider co-locating compute and storage)

**Storage:**
- `PREMIUM_DATABRICKS_STORAGE` = Databricks-managed storage (DSU). ~$0.023/DSU/day where 1 DSU ≈ 1 GB.
- This is ~30x more expensive than raw cloud storage (S3/ADLS/GCS)
- Managed tables can be configured to use customer's own cloud storage at the metastore, catalog, or schema level — retaining all Unity Catalog benefits while eliminating managed storage charges

---

## Optimization Priority Matrix

After running all analyses, prioritize by effort vs impact:

| Priority | Finding | Typical Savings | Effort |
|----------|---------|----------------|--------|
| **1** | Jobs on ALL_PURPOSE clusters → JOBS compute | 60-70% on those workloads | Low (config change) |
| **2** | Always-on clusters with low utilization | Scale to zero during idle hours | Low-Medium |
| **3** | Idle clusters without auto-termination | 100% of idle time cost | Low (set auto-terminate) |
| **4** | Streaming jobs → `Trigger.AvailableNow` | 50-80% on those workloads | Medium (change trigger mode) |
| **5** | Micro-batch on ALL_PURPOSE → Continuous job | 60-70% rate reduction | Medium (refactor trigger) |
| **6** | Failing jobs burning compute | 100% of failed run cost | Varies (fix root cause) |
| **7** | SQL warehouse undersizing (disk spill) | 20-40% per spilling query | Low-Medium (resize warehouse) |
| **8** | Over-provisioned clusters (low CPU/memory) | 30-50% instance cost | Medium (test new size) |
| **9** | Memory-optimized instances with low memory use | 20-40% (switch to compute family) | Medium |
| **10** | Delta table optimization (OPTIMIZE, clustering) | 10-50% DBU reduction per query | Medium |
| **11** | Classic compute → Serverless | Varies, often cheaper + no management | Medium-High |
| **12** | DBR upgrades | 10-30% from engine improvements | Medium (regression testing) |
| **13** | Untagged resources | No direct savings, but enables accountability | Low |
| **14** | Managed storage → customer storage | Up to 30x on storage costs | Low-Medium |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not filtering on `usage_date` | Always include `usage_date` filter for partition pruning |
| Joining `list_prices` without time range | Must include `price_start_time`/`price_end_time` in join |
| Looking for `job_id` in billing for shared clusters | Jobs on existing ALL_PURPOSE clusters have `job_id = NULL` in billing — use `lakeflow_job_task_run_timeline.compute_ids` instead |
| Using averages alone for right-sizing | Always check P95 and max — average 30% CPU with P95 of 90% means the cluster IS needed at peak |
| Ignoring swap in memory analysis | `mem_swap_percent > 0` means OOM risk even if `mem_used_percent` looks fine |
| Recommending per-run job clusters for micro-batch workloads | If a job runs every few seconds, cluster startup time makes per-run clusters impractical — recommend continuous job mode instead |
| Comparing only DBU rates | Instance type determines DBUs/hour — switching to smaller instance changes DBU consumption, not just the rate |
| Starting cost analysis from clusters/jobs | Always start from `system.billing.usage` — it is the only source of truth for cost. Clusters and jobs are workload containers, not billing units |
| Ignoring disk spill in SQL warehouse analysis | Spill = warehouse too small. Queries still succeed but run slower and cost more DBUs |
| Assuming all streaming jobs need real-time | Most streaming workloads have SLAs of 5-15 minutes, not sub-second. `Trigger.AvailableNow` is almost always sufficient |

---

## System Tables Reference

| Table | Key Columns | Use For |
|-------|-------------|---------|
| `system.billing.usage` | `usage_date`, `sku_name`, `usage_quantity`, `usage_metadata.*`, `custom_tags` | Cost attribution, spend trends |
| `system.billing.list_prices` | `sku_name`, `cloud`, `pricing.default`, `price_start_time` | Dollar cost calculation |
| `system.compute.clusters` | `cluster_id`, `cluster_name`, `dbr_version`, `driver_node_type`, `worker_node_type`, `cluster_source` | Cluster config and metadata |
| `system.compute.node_timeline` | `cluster_id`, `driver`, `cpu_*_percent`, `mem_used_percent`, `mem_swap_percent`, `network_*_bytes` | Utilization metrics for right-sizing |
| `system.lakeflow.jobs` | `job_id`, `name`, `tags` | Job metadata |
| `system.lakeflow.job_run_timeline` | `job_id`, `run_id`, `result_state`, `period_start_time` | Job success/failure rates |
| `system.lakeflow.job_task_run_timeline` | `job_id`, `run_id`, `compute_ids`, `compute`, `result_state` | Job-to-cluster mapping, task-level analysis |
| `system.query.history` | `warehouse_id`, `statement_text`, `total_duration_ms`, `bytes_read`, `rows_produced`, `spilled_local_bytes` | SQL query cost, spill detection, warehouse sizing |
| `system.storage.predictive_optimization_operations_history` | `table_name`, `operation_type`, `operation_status` | Delta table maintenance tracking |

**Note on `compute_ids` vs `compute`:**
- `compute_ids`: Array of cluster/warehouse IDs (available for most historical data). Search with `ARRAY_CONTAINS(compute_ids, '<ID>')`.
- `compute`: Array of structs with `type`, `cluster_id`, `warehouse_id` (available for data after late November 2025). Use `LATERAL VIEW EXPLODE(compute) AS c` then filter on `c.cluster_id`.

---

## Presentation Template

When presenting findings, structure as:

1. **Executive Summary** — Total spend, top 3 findings with estimated savings
2. **Spend Breakdown** — By product type, by workspace, trends
3. **Top Optimization Opportunities** — Ordered by savings potential
4. **Per-Cluster Deep Dives** — For the top 3-5 clusters by cost
5. **Recommended Actions** — Specific, actionable steps with estimated impact
