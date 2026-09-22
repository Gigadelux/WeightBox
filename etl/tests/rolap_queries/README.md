# ROLAP verification queries

Read-only SQL, one file per classic OLAP operation (roll-up, drill-down,
slice, dice, pivot) plus three materialized-view consistency checks, run
against the star schema to verify it behaves as designed. Not part of the
`pytest` suite; run manually against a populated warehouse. Results and
analysis: [`docs/ROLAP_TEST_REPORT.md`](../../../docs/ROLAP_TEST_REPORT.md).

```bash
# against the db service in docker-compose.yml
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f etl/tests/rolap_queries/01_rollup_architecture_year.sql

# all of them in order, with timing
for f in etl/tests/rolap_queries/0*.sql; do
    echo "=== $f ==="
    docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\timing on' -f "$f"
done
```

| File | Operation |
|---|---|
| `01_rollup_architecture_year.sql` | Roll-up: `gpu_architecture` x `release_year` |
| `02_drilldown_parameter_bucket.sql` | Drill-down: `parameter_bucket` within one architecture |
| `03_slice_language_domain.sql` | Slice: `primary_domain = 'Language'` fixed |
| `04_dice_recent_generative_high_vram.sql` | Dice: post-2022 generative models x >=24GB GPUs |
| `05_pivot_memtype_parameter_bucket.sql` | Pivot: `mem_type` x `parameter_bucket` matrix |
| `06a_mv_consistency_deployability.sql` | `mv_deployability_by_year_arch` vs live re-aggregation |
| `06b_mv_consistency_gpu_generation_tradeoff.sql` | `mv_gpu_generation_tradeoff` vs live re-aggregation |
| `06c_mv_consistency_domain_accessibility.sql` | `mv_domain_accessibility` vs live re-aggregation |
