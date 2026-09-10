"""Cleansing rules (WEIGHTBOX_SPECS.md section 6.2).

``cleanse_gpus`` applies G1..G8, ``cleanse_models`` applies M1..M6. Each returns a
:class:`CleanResult`: the dimension-ready frame, the rejected rows, and a count
per rule (logged in the Phase 2 run summary).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src import lookups, transform


@dataclass
class CleanResult:
    frame: pd.DataFrame
    rejects: list[dict[str, str | None]] = field(default_factory=list)
    rule_counts: dict[str, int] = field(default_factory=dict)

    def bump(self, rule: str, n: int = 1) -> None:
        self.rule_counts[rule] = self.rule_counts.get(rule, 0) + n

    def reject(self, natural_key: str | None, rule: str, detail: str | None = None) -> None:
        self.rejects.append({"natural_key": natural_key, "rule": rule, "detail": detail})
        self.bump(rule)


_GPU_SPEC_COLS = [
    "mem_size", "mem_bus_width", "gpu_clock", "mem_clock", "unified_shader",
    "tmu", "rop", "mem_type", "gpu_chip",
]

_SUSPECT_INTEL_CHIPS = {"ARCTIC SOUND", "AQUA VANJARAM", "ALDEBARAN", "PONTE VECCHIO"}
_CONSUMER_TOKENS = ("GEFORCE", "RADEON RX", " RX ", "GTX", "RTX")


def _non_null_count(row: pd.Series, cols: list[str]) -> int:
    return sum(1 for c in cols if str(row.get(c) or "").strip() not in ("", "nan"))


def cleanse_gpus(ods: pd.DataFrame) -> CleanResult:
    out = CleanResult(frame=pd.DataFrame(), rule_counts={})
    df = ods.copy()

    # G1: release year to int, drop pre-2016 (null year kept)
    df["_release_year"] = df["release_year"].map(transform.to_float)
    pre = df["_release_year"].notna() & (df["_release_year"] < lookups.GPU_MIN_RELEASE_YEAR)
    for pn in df.loc[pre, "product_name"]:
        out.reject(pn, "pre_2016")
    df = df.loc[~pre].copy()

    # G6: de-duplicate on product_name, keep the most complete row
    df["_completeness"] = df.apply(lambda r: _non_null_count(r, _GPU_SPEC_COLS), axis=1)
    df["_year_sort"] = df["_release_year"].fillna(-1)
    df = df.sort_values(["_completeness", "_year_sort"], ascending=False)
    dupes = df["product_name"].duplicated(keep="first")
    for pn in df.loc[dupes, "product_name"]:
        out.reject(pn, "duplicate_product_name")
    df = df.loc[~dupes].copy()

    records: list[dict] = []
    for _, r in df.iterrows():
        pn = (str(r.get("product_name") or "")).strip()

        # G2: canonical memory type (with sibling inference already folded into the map lookup)
        mem = transform.canonical_mem_type(r.get("mem_type"))
        if mem is None:
            mem = _infer_mem_type_from_chip(df, r.get("gpu_chip"))
        if mem is None:
            out.reject(pn, "unknown_memory_type", str(r.get("mem_type")))
            continue
        mem_type, mem_family, data_rate = mem

        # G3: VRAM
        vram = transform.to_float(r.get("mem_size"))
        if not vram or vram <= 0:
            curated = lookups.CURATED_GPU_SPECS.get(
                transform._WS.sub(" ", pn).strip().upper()
            )
            vram = float(curated[1]) if curated else None
        if not vram or vram <= 0:
            out.reject(pn, "missing_vram")
            continue

        # G4: bus width
        bus_width, bus_estimated = transform.impute_bus_width(
            pn, mem_type, r.get("mem_bus_width")
        )

        # G5: memory clock
        mem_clock = transform.to_float(r.get("mem_clock"))
        if not mem_clock or mem_clock <= 0:
            mem_clock = _modal_mem_clock(df, mem_type)
        if not mem_clock or mem_clock <= 0:
            out.reject(pn, "missing_mem_clock")
            continue

        # G7: cross-field consistency
        suspect = _is_suspect(r.get("manufacturer"), r.get("gpu_chip"), pn, mem_family)

        bandwidth = transform.memory_bandwidth_gbs(mem_clock, bus_width, data_rate)
        if bandwidth is None:
            out.reject(pn, "insufficient_memory_specs")
            continue

        year = r["_release_year"]
        records.append(
            {
                "gpu_nk": f"{pn}|{int(year) if pd.notna(year) else 'NA'}",
                "product_name": pn,
                "manufacturer": (str(r.get("manufacturer") or "")).strip() or "Unknown",
                "gpu_chip": (str(r.get("gpu_chip") or "")).strip() or None,
                "gpu_architecture": transform.gpu_architecture(r.get("gpu_chip"), pn),
                "release_year": int(year) if pd.notna(year) else None,
                "vram_gb": vram,
                "vram_bucket": transform.vram_bucket(vram),
                "mem_bus_width_bit": bus_width,
                "mem_clock_mhz": mem_clock,
                "mem_type": mem_type,
                "mem_family": mem_family,
                "data_rate": data_rate,
                "memory_bandwidth_gbs": bandwidth,
                "bandwidth_is_estimated": bool(bus_estimated or suspect),
                "specs_suspect": bool(suspect),
            }
        )
        out.bump("gpu_accepted")
        if suspect:
            out.bump("specs_suspect_flagged")
        if bus_estimated:
            out.bump("bus_width_imputed")

    out.frame = pd.DataFrame.from_records(records)
    return out


def _infer_mem_type_from_chip(df: pd.DataFrame, chip: object) -> tuple[str, str, float] | None:
    c = (str(chip or "")).strip()
    if not c:
        return None
    siblings = df.loc[df["gpu_chip"].astype(str).str.strip() == c, "mem_type"]
    for raw in siblings:
        got = transform.canonical_mem_type(raw)
        if got is not None:
            return got
    return None


def _modal_mem_clock(df: pd.DataFrame, mem_type: str) -> float | None:
    clocks = (
        df["mem_clock"].map(transform.to_float).dropna()
    )
    clocks = clocks[clocks > 0]
    if clocks.empty:
        return None
    return float(clocks.median())


def _is_suspect(manufacturer: object, chip: object, product_name: str, mem_family: str) -> bool:
    mfr = (str(manufacturer or "")).strip().upper()
    chip_u = (str(chip or "")).strip().upper()
    pn_u = product_name.upper()
    if mfr in {"NVIDIA", "AMD", "ATI"} and chip_u in _SUSPECT_INTEL_CHIPS:
        return True
    if mem_family == "HBM" and any(tok in pn_u for tok in _CONSUMER_TOKENS):
        return True
    return False


_MODEL_SPEC_COLS = [
    "organization", "publication_date", "domain", "task", "parameters",
    "training_compute_flop", "confidence",
]


def cleanse_models(ods: pd.DataFrame) -> CleanResult:
    out = CleanResult(frame=pd.DataFrame(), rule_counts={})
    df = ods.copy()
    df["model"] = df["model"].astype(str).str.strip()

    # M1: unique natural key, keep the most complete row on collision
    df["_completeness"] = df.apply(lambda r: _non_null_count(r, _MODEL_SPEC_COLS), axis=1)
    df = df.sort_values("_completeness", ascending=False)
    dupes = df["model"].duplicated(keep="first")
    for name in df.loc[dupes, "model"]:
        out.reject(name, "duplicate_model")
    df = df.loc[~dupes].copy()

    records: list[dict] = []
    for _, r in df.iterrows():
        name = r["model"]

        # M2: publication date
        release_date = transform.parse_date(r.get("publication_date"))
        if release_date is None:
            out.reject(name, "bad_publication_date", str(r.get("publication_date")))
            continue
        month, quarter, year, decade = transform.calendar_parts(release_date)

        # M3: parameter count (null allowed)
        params = transform.plausible_parameter_count(r.get("parameters"))
        if params is None and transform.to_float(r.get("parameters")) is not None:
            out.bump("parameter_out_of_range")
        if params is None:
            out.bump("parameter_missing")

        # M4: domain
        domain = transform.primary_domain(r.get("domain"), r.get("task"))
        is_gen, unit = transform.is_generative_and_unit(domain)

        # M5: organization
        org = transform.normalize_org(r.get("organization"))
        country = transform.org_country(r.get("country_of_organization"))

        records.append(
            {
                "model_nk": name,
                "model_name": name,
                "organization": org,
                "organization_country": country,
                "primary_domain": domain,
                "is_generative": bool(is_gen),
                "throughput_unit": unit,
                "parameter_count": params,
                "parameter_bucket": transform.parameter_bucket(params),
                "training_compute_flop": transform.to_float(r.get("training_compute_flop")),
                "release_date": release_date,
                "release_month": month,
                "release_quarter": quarter,
                "release_year": year,
                "release_decade": decade,
                "confidence": (str(r.get("confidence") or "")).strip() or None,
                "source_dataset": "notable_ai_models",
            }
        )
        out.bump("model_accepted")

    out.frame = pd.DataFrame.from_records(records)
    return out
