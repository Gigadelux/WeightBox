# WeightBox ROLAP Verification Report

## 1. Execution parameters

| Parameter | Value |
|---|---|
| Run timestamp (local) | 2026-09-22 16:38:53 CEST |
| Run timestamp (UTC) | 2026-09-22 14:38:22 UTC |
| PostgreSQL | 18.6 (Debian 18.6-1.pgdg13+2), `postgres:latest` image |
| Container | `weightbox_ROLAP` (pre-existing, attached to the `weightbox-local_default` Compose network with alias `db`) |
| Compose services up | `weightbox-local-frontend-1` (healthy) — `db` role served by the container above |
| Connection | host `127.0.0.1` (published) / `db` (in-network alias), port `5432`, user `weightbox-admin`, database `weightbox-admin` |
| Client | `psql` inside the container, invoked via `docker exec` |
| ETL run immediately prior | full 4-phase pipeline (`initialization` → `etl` → `indexing` → `health`), all phases `ok`, all 6 validator rows `pass` |
| Query mode | read-only (`SELECT` only), `\timing on` |

### Warehouse state at run time

| Relation | Rows |
|---|---:|
| `ods.ods_models` | 1,052 |
| `ods.ods_gpus` | 3,056 |
| `ods.reject_models` | 331 |
| `ods.reject_gpus` | 2,439 |
| `dim_model` | 721 |
| `dim_gpu` | 617 |
| `fact_gpu_model_compatibility` | 444,857 |
| `validator_fact_nulls` | 6 (6 pass, 0 fail) |
| `mv_deployability_by_year_arch` | 880 |
| `mv_gpu_generation_tradeoff` | 128 |
| `mv_domain_accessibility` | 84 |

DB size: 101 MB. All 14 expected indexes present, including the two brief-required `ix_fact_model_nk` / `ix_fact_gpu_nk`.

---

## 2. Query results

### 2.1 Roll-up — pairs / fit-rate / avg headroom by `gpu_architecture` × `release_year`

Classic OLAP roll-up: aggregate the fact up two dimension attributes at once (first 20 rows, `Ada Lovelace` architecture).

```
 gpu_architecture | release_year | pairs | pairs_fit | avg_headroom_gb
------------------+--------------+-------+-----------+-----------------
 Ada Lovelace     |         1950 |    51 |         0 |
 Ada Lovelace     |         1952 |    51 |         0 |
 Ada Lovelace     |         1955 |    51 |         0 |
 Ada Lovelace     |         1957 |    51 |        51 |           23.06
 Ada Lovelace     |         1959 |   102 |        51 |           23.06
 Ada Lovelace     |         1960 |   102 |        51 |           23.06
 Ada Lovelace     |         1966 |    51 |        51 |           23.06
 Ada Lovelace     |         1969 |    51 |        51 |           23.06
 Ada Lovelace     |         1973 |    51 |         0 |
 Ada Lovelace     |         1975 |    51 |        51 |           23.06
 Ada Lovelace     |         1980 |    51 |        51 |           23.06
 Ada Lovelace     |         1981 |    51 |        51 |           23.06
 Ada Lovelace     |         1982 |    51 |        51 |           23.06
 Ada Lovelace     |         1983 |    51 |         0 |
 Ada Lovelace     |         1984 |    51 |        51 |           23.06
 Ada Lovelace     |         1986 |   102 |         0 |
 Ada Lovelace     |         1987 |   153 |       102 |           23.06
 Ada Lovelace     |         1988 |    51 |        51 |           23.06
 Ada Lovelace     |         1989 |   204 |       153 |           23.06
 Ada Lovelace     |         1990 |   255 |       204 |           23.06
(20 rows)
```
**Execution time: 128.964 ms**

`release_year` here is `dim_model.release_year` (the model's publication year, not the GPU's). Rows with `pairs_fit = 0` and blank headroom are models the "Ada Lovelace" GPU family cannot fit at all in that year-group; where it fits, headroom is flat at 23.06 GB across many groups, which is expected — the 51 GPUs in this architecture bucket are largely the same handful of distinct cards, so headroom (`vram_gb - model_footprint`) repeats whenever the same model/GPU-class pairing recurs.

**Data quality flag:** publication years down to 1950 are not real — this is the same class of injected/synthetic defect the README documents for the model source CSV (it calls out future-dated 2026 rows explicitly; these implausible past dates are the mirror case, apparently not caught by any cleansing rule since `dim_model` has no lower-bound plausibility check on `release_date`, only a well-formedness check, M2 "bad_publication_date"). Worth a follow-up cleansing rule if the course rubric expects date plausibility bounds, not just parseability.

---

### 2.2 Drill-down — same roll-up one level deeper, by `parameter_bucket` within one architecture

Drills from the year-level roll-up above into a lower grain: architecture fixed to the most common bucket (`Unknown`, 153 GPUs — see §3), broken out by model size bucket instead of year.

```
 gpu_architecture | parameter_bucket | models_deployable | avg_throughput |   min_throughput    |  max_throughput
------------------+------------------+-------------------+----------------+---------------------+------------------
 Unknown          | 13-34B           |               246 |           3.07 |   0.130522088353414 | 105.025641025641
 Unknown          | 1-7B             |              4327 |          26.11 |   0.646766169154229 | 1365.33333333333
 Unknown          | >180B            |                 0 |           0.13 | 0.00144444444444444 | 7.58518518518519
 Unknown          | <1B              |             53013 |      474241.29 |     4.6001415428167 |  662461588.22578
 Unknown          | 34-70B           |                20 |           1.27 |  0.0646766169154229 |  40.156862745098
 Unknown          | 70-180B          |                 0 |           0.58 |  0.0243445692883895 | 19.5047619047619
 Unknown          | 7-13B            |               406 |           6.40 |   0.335917312661499 | 195.047619047619
 Unknown          | unknown          |                 0 |                |                     |
(8 rows)
```
**Execution time: 12.252 ms**

`models_deployable` counts **distinct** models that fit (matching `mv_gpu_generation_tradeoff`'s own semantics), so it's not comparable to the `pairs` figures in §2.1. Monotonic and sane at the top: `>180B` and `70-180B` models never fit (0 deployable) under this GPU class, as expected for a heterogeneous "Unknown"-architecture bucket.

**Data quality flag:** the `<1B` row's `max_throughput ≈ 6.6×10⁸ tokens/sec` is not physically meaningful. Traced to source (§3): a handful of source rows (e.g. `"LTE speaker verification system"`, `parameter_count = 2061`) are tiny non-LLM classifiers with literal parameter counts in the low thousands, not billions, yet pass the `is_generative`/domain checks that gate the throughput formula. Dividing GPU memory bandwidth by a ~2,000-parameter footprint produces the absurd figure. This is a methodology edge case in the throughput derivation (`transform.py`), not a query bug — see §3 for the exact offending rows.

---

### 2.3 Slice — fix `primary_domain = 'Language'`, aggregate accessibility across `vram_bucket`

Classic slice: hold one dimension attribute constant, aggregate over another. Matches `mv_domain_accessibility`'s own filter (`quantization_required IS NOT NULL`) so the row counts are directly comparable to the view.

```
 vram_bucket | models_total | models_no_quant | models_8bit | models_4bit
-------------+--------------+-----------------+-------------+-------------
 10-12       |          401 |             164 |          31 |          49
 16          |          401 |             170 |          46 |          20
 24          |          401 |             193 |          49 |          32
 32-48       |          401 |             234 |          54 |          48
 <=4         |          401 |             139 |         146 |         150
 >48         |          401 |             294 |          88 |          92
 6-8         |          401 |             160 |          28 |          54
(7 rows)
```
**Execution time: 94.050 ms**

`models_total` is flat at 401 across every `vram_bucket` — expected, since it counts *distinct Language-domain models that fit somewhere* under this fact join, not models specific to that VRAM tier; every Language model reaches every VRAM bucket in the cross product, it's `quantization_required` that varies. The trend is intuitive: as `vram_bucket` grows, `models_no_quant` rises (139 → 294) while `models_4bit`/`models_8bit` (forced compression) generally falls, bottoming at `>48` GB.

---

### 2.4 Dice — post-2022 generative models × GPUs ≥24 GB VRAM

Multi-dimension filter (a dice, not a slice, since two independent predicates constrain both dimensions at once), computed directly off the star schema rather than a materialized view.

```
 vram_bucket | parameter_bucket | pairs | pct_fit | does_not_fit
-------------+------------------+-------+---------+--------------
 24          | 13-34B           |   888 |     0.0 |            0
 24          | 1-7B             |   528 |   100.0 |            0
 24          | >180B            |  1800 |     0.0 |         1800
 24          | <1B              |   240 |   100.0 |            0
 24          | 34-70B           |   264 |     0.0 |          120
 24          | 70-180B          |   816 |     0.0 |          816
 24          | 7-13B            |   456 |    78.9 |            0
 32-48       | 13-34B           |  1406 |    38.9 |            0
 32-48       | 1-7B             |   836 |   100.0 |            0
 32-48       | >180B            |  2850 |     0.0 |         2850
 32-48       | <1B              |   380 |   100.0 |            0
 32-48       | 34-70B           |   418 |     0.0 |           71
 32-48       | 70-180B          |  1292 |     0.0 |         1058
 32-48       | 7-13B            |   722 |    99.9 |            0
 >48         | 13-34B           |   851 |    95.1 |            0
 >48         | 1-7B             |   506 |   100.0 |            0
 >48         | >180B            |  1725 |     0.0 |         1661
 >48         | <1B              |   230 |   100.0 |            0
 >48         | 34-70B           |   253 |    34.0 |            0
 >48         | 70-180B          |   782 |     5.8 |           67
 >48         | 7-13B            |   437 |   100.0 |            0
(21 rows)
```
**Execution time: 10.478 ms**

Coherent trend across all three VRAM tiers: `pct_fit` for a given `parameter_bucket` rises monotonically with `vram_bucket` (e.g. `13-34B`: 0.0% at 24 GB → 38.9% at 32-48 GB → 95.1% at >48 GB), and `>180B` models never fit even at the top VRAM tier without quantization headroom this query doesn't model (`fits_in_vram` is the raw, unquantized check). `13-34B`/`34-70B`/`70-180B` at the 24 GB tier show `0.0%` fit but *not* 100% `does_not_fit` for `13-34B` and `70-180B` rows above 0 pairs — consistent with `fits_in_vram = false` while `quantization_required` is still `8-bit`/`4-bit` (fits only after compression) rather than `does-not-fit` outright.

---

### 2.5 Pivot — `mem_type` × `parameter_bucket` matrix of `fits_in_vram` counts

```
 mem_type | 1-7B  | 7-13B | 13-34B | 34-70B | 70-180B | >180B
----------+-------+-------+--------+--------+---------+-------
 DDR2     |    69 |     0 |      0 |      0 |       0 |     0
 GDDR3    |  1165 |     0 |      0 |      0 |       0 |     0
 GDDR5    | 10435 |   386 |     80 |      0 |       0 |     0
 GDDR5X   |   913 |   240 |    148 |      0 |       0 |     0
 GDDR6    | 10432 |  1302 |    779 |     32 |       0 |     0
 GDDR6X   |  1356 |   286 |    306 |     16 |       0 |     0
 GDDR7    |   271 |     0 |      0 |      0 |       0 |     0
 HBM      |   369 |     0 |      0 |      0 |       0 |     0
 HBM2e    |  4896 |   904 |    441 |     26 |       0 |     0
 HBM3     |   423 |    80 |    102 |     34 |      53 |     0
 LPDDR5   |   243 |     0 |      0 |      0 |       0 |     0
(11 rows)
```
**Execution time: 25.923 ms**

Legacy/low-VRAM memory types (`DDR2`, `GDDR3`, `GDDR7` — the last simply too new to have large-VRAM SKUs yet in this dataset) only ever fit the smallest bucket. `HBM3`, the highest-bandwidth/highest-capacity type present, is the only one reaching `70-180B` at all (53 fits). No memory type fits `>180B` unquantized anywhere in the warehouse — consistent with §2.4.

---

### 2.6 Materialized view consistency checks

Each of the three `mv_*` views was re-aggregated live from `fact_gpu_model_compatibility` / `dim_model` / `dim_gpu` using the exact `GROUP BY`/`FILTER` semantics from `etl/SQL/tables/views.py`, then diffed row-by-row against the stored view.

```
=== 6a. mv_deployability_by_year_arch ===
 mv_rows | live_rows | mismatched_rows
---------+-----------+-----------------
     880 |       880 |               0
(1 row)                                          Time: 28.033 ms

=== 6b. mv_gpu_generation_tradeoff ===
 mv_rows | live_rows | mismatched_rows
---------+-----------+-----------------
     128 |       128 |               0
(1 row)                                          Time: 241.002 ms

=== 6c. mv_domain_accessibility ===
 mv_rows | live_rows | mismatched_rows
---------+-----------+-----------------
      84 |        84 |               0
(1 row)                                          Time: 219.337 ms
```

**All three materialized views are byte-for-byte consistent with the underlying star schema at query time — 0 mismatched rows out of 880 + 128 + 84 = 1,092 total.** This confirms `REFRESH MATERIALIZED VIEW` ran correctly at the end of the ETL's `etl` phase and that no drift exists between the stored aggregates and the fact/dim tables they summarize.

(Initial versions of 6b/6c showed 55 and 42 mismatches respectively — traced to the *verification queries* using `COUNT(*)` instead of `COUNT(DISTINCT model_key)` for 6b and missing the view's own `WHERE quantization_required IS NOT NULL` filter for 6c. Not a warehouse defect; the queries were corrected to match the views' actual DDL in `etl/SQL/tables/views.py` before this run.)

---

## 3. Supporting data-quality detail

**`gpu_architecture` distribution** (top 10 of `dim_gpu`, 617 rows total):

```
 gpu_architecture | count
------------------+-------
 Unknown          |   153
 Ampere           |    96
 Turing           |    67
 Pascal           |    58
 Ada Lovelace     |    51
 Kepler           |    47
 RDNA 2           |    27
 GCN 5 (Vega)     |    25
 RDNA             |    21
 Volta            |    16
```

Nearly a quarter (153/617, 24.8%) of kept GPUs carry the `'Unknown'` architecture default — the largest single bucket. That's a real limitation on the `mv_gpu_generation_tradeoff` / roll-up-by-architecture analyses: any roll-up sliced by `gpu_architecture` treats a quarter of the fleet as one undifferentiated group. Not a bug (the schema documents this as an explicit default), but worth surfacing if the ROLAP analyses are graded on discriminative power.

**Throughput outlier root cause** (§2.2):

```
                 model_nk                 | parameter_count | parameter_bucket |            gpu_nk             | memory_bandwidth_gbs | estimated_throughput | throughput_unit
-------------------------------------------+-----------------+------------------+--------------------------------+-----------------------+-----------------------+-----------------
 LTE speaker verification system          |            2061 | <1B              | Data Center GPU Max 1550|2023 |            21512.192 |     4349060326.70225 | tokens/sec
 Speaker-independent vowel classification |            3040 | <1B              | Data Center GPU Max 1550|2023 |            21512.192 |     2948491228.07018 | tokens/sec
 LTE speaker verification system          |            2061 | <1B              | H100 SXM5 96 GB|2023          |                14336  |     2898269448.48779 | tokens/sec
 LTE speaker verification system          |            2061 | <1B              | A800 PCIe 80 GB|2022          |             13445.12 |     2718162704.18891 | tokens/sec
 LTE speaker verification system          |            2061 | <1B              | A800 SXM4 80 GB|2022          |             13445.12 |     2718162704.18891 | tokens/sec
```

Both offending models have literal parameter counts in the low thousands (2,061 and 3,040) — not the billions the `<1B` bucket label implies for a language/generative model. They are small signal-processing classifiers that pass `is_generative` and the domain gate but are nowhere near LLM scale, so `bandwidth / footprint` blows up. If this data-quality issue matters for the course deliverable, the fix belongs in `transform.py`'s `is_generative`/throughput-eligibility logic (excluding non-LLM-scale models from throughput estimation, e.g. a minimum plausible parameter floor), not in these verification queries.

---

## 4. Conclusion

The ROLAP star schema behaves correctly under all five classic OLAP operations tested (roll-up, drill-down, slice, dice, pivot), the fact table's row count matches the expected `dim_gpu × dim_model` cross product exactly (617 × 721 = 444,857), all 6 `validator_fact_nulls` checks pass, and all three materialized views are provably consistent with a from-scratch re-aggregation of the base tables. Query latency stayed well under 250 ms for every query against the ~445K-row fact table, including the two `COUNT(DISTINCT ...)` heavy MV-consistency checks.

Two genuine data-quality issues surfaced during this analysis (§2.1, §2.2/§3), both traceable to source-CSV defects/edge cases rather than pipeline logic errors: implausible past `release_date` values on a handful of models, and a small set of non-LLM classifier models producing physically meaningless throughput estimates. Neither affects the structural correctness of the warehouse, but both would be reasonable next cleansing/derivation refinements.
