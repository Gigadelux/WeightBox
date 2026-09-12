"""Pure derivation functions.

Scalar in, scalar out, no I/O. The dimension-level derivations feed
``cleansing`` and the dimension builders; the fact-level ones
(``fits_in_vram`` ... ``estimated_throughput``) mirror the SQL in
``SQL.queries.fact_build`` and exist here so the arithmetic is unit-testable.
"""

from __future__ import annotations

import datetime as dt
import math
import re

from src import lookups

_WS = re.compile(r"\s+")


def _clean_str(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    return s


def to_float(value: object) -> float | None:
    s = _clean_str(value)
    if s is None:
        return None
    s = s.replace(",", "")
    try:
        f = float(s)
    except ValueError:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


# GPU memory

def canonical_mem_type(raw: object) -> tuple[str, str, float] | None:
    s = _clean_str(raw)
    if s is None:
        return None
    key = _WS.sub(" ", s).strip().upper().replace(" ", "")
    if key in lookups.JUNK_MEM_TOKENS:
        return None
    return lookups.MEM_TYPE_TABLE.get(key)


def impute_bus_width(
    product_name: object, mem_type: str | None, source_bus: object
) -> tuple[int | None, bool]:
    """Return (bus_width_bit, is_estimated)."""
    src = to_float(source_bus)
    if src and src > 0:
        return int(src), False

    pn = _clean_str(product_name)
    if pn:
        key = _WS.sub(" ", pn).strip().upper()
        curated = lookups.CURATED_GPU_SPECS.get(key)
        if curated:
            return curated[0], True

    if mem_type and mem_type in lookups.MODAL_BUS_WIDTH_BY_MEM_TYPE:
        return lookups.MODAL_BUS_WIDTH_BY_MEM_TYPE[mem_type], True

    return None, True


def memory_bandwidth_gbs(
    mem_clock_mhz: object, bus_width_bit: object, data_rate: object
) -> float | None:
    clk = to_float(mem_clock_mhz)
    bus = to_float(bus_width_bit)
    rate = to_float(data_rate)
    if not clk or not bus or not rate:
        return None
    return clk * bus * rate / 8000.0


def gpu_architecture(gpu_chip: object, product_name: object) -> str:
    haystacks = [
        _WS.sub(" ", (_clean_str(x) or "")).strip().upper()
        for x in (gpu_chip, product_name)
    ]
    for pattern, arch in lookups.ARCH_PATTERNS:
        if any(pattern in h for h in haystacks):
            return arch
    return "Unknown"


def vram_bucket(vram_gb: object) -> str:
    v = to_float(vram_gb) or 0.0
    if v <= 4:
        return "<=4"
    if v <= 8:
        return "6-8"
    if v <= 12:
        return "10-12"
    if v <= 16:
        return "16"
    if v <= 24:
        return "24"
    if v <= 48:
        return "32-48"
    return ">48"


# Model

def calendar_parts(d: dt.date) -> tuple[int, int, int, int]:
    quarter = (d.month - 1) // 3 + 1
    decade = d.year - (d.year % 10)
    return d.month, quarter, d.year, decade


def parse_date(value: object) -> dt.date | None:
    s = _clean_str(value)
    if s is None:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m", "%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def primary_domain(domain: object, task: object) -> str:
    raw = _clean_str(domain)
    if raw:
        parts = {p.strip() for p in raw.split(",") if p.strip()}
        for candidate in lookups.DOMAIN_PRIORITY:
            if candidate in parts:
                return candidate
        first = next(iter(parts), None)
        if first:
            return first if first in lookups.DOMAIN_GENERATIVE else "Other"

    t = (_clean_str(task) or "").lower()
    for keyword, mapped in lookups.TASK_DOMAIN_HINTS:
        if keyword in t:
            return mapped
    return "Other"


def is_generative_and_unit(domain: str) -> tuple[bool, str | None]:
    return lookups.DOMAIN_GENERATIVE.get(domain, (False, None))


def parameter_bucket(params: float | None) -> str:
    if params is None:
        return "unknown"
    b = params / 1e9
    if b < 1:
        return "<1B"
    if b < 7:
        return "1-7B"
    if b < 13:
        return "7-13B"
    if b < 34:
        return "13-34B"
    if b < 70:
        return "34-70B"
    if b < 180:
        return "70-180B"
    return ">180B"


def normalize_org(org: object) -> str:
    s = _clean_str(org)
    if s is None:
        return "Unknown"
    return lookups.ORG_ALIASES.get(s.upper(), s)


def org_country(source_country: object) -> str:
    """Country from the source `Country (of organization)` column: first
    comma-segment, verbose UN-style name shortened."""
    s = _clean_str(source_country)
    if s is None:
        return "Unknown"
    first = s.split(",")[0].strip()
    return lookups.COUNTRY_NORMALISE.get(first, first) or "Unknown"


def plausible_parameter_count(value: object) -> float | None:
    f = to_float(value)
    if f is None:
        return None
    if f < lookups.PARAMETER_MIN or f > lookups.PARAMETER_MAX:
        return None
    return f


# "<n>B"/"M"/"T" size tokens, plus the "<experts>x<n>B" MoE shorthand (e.g.
# "Mixtral-8x7B" -> 8 * 7B). Requires the letter to sit directly against the
# number so "GPT-4", "Llama-3.1" etc. never match.
_PARAM_SIZE_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*([BMT])(?![A-Za-z])"
    r"|(?<![A-Za-z0-9])(\d+(?:\.\d+)?)\s*([BMT])(?![A-Za-z])"
)
_SIZE_MULTIPLIER: dict[str, float] = {"M": 1e6, "B": 1e9, "T": 1e12}


def parameter_count_from_name(name: object) -> float | None:
    """Best-effort parameter count encoded directly in the model name itself
    (`"Llama-3.1-Nemotron-70B-Instruct"` -> 70e9, `"Mixtral-8x7B"` -> 56e9).
    Used only as a fallback when the source `Parameters` cell is blank; takes
    the last size token found, returns `None` if the name carries none."""
    s = _clean_str(name)
    if s is None:
        return None
    last: float | None = None
    for m in _PARAM_SIZE_RE.finditer(s):
        if m.group(3):  # MoE shorthand: experts x per-expert size
            last = float(m.group(1)) * float(m.group(2)) * _SIZE_MULTIPLIER[m.group(3)]
        else:
            last = float(m.group(4)) * _SIZE_MULTIPLIER[m.group(5)]
    return last


# Fact-level arithmetic (mirrors SQL.queries.fact_build)

def model_footprint_gb(param_count: float | None, precision: str) -> float | None:
    if param_count is None:
        return None
    bpw = lookups.BYTES_PER_WEIGHT[precision]
    return param_count * bpw * lookups.OVERHEAD_FACTOR / 1e9


def fits_in_vram(footprint_fp16: float | None, vram_gb: float) -> bool | None:
    if footprint_fp16 is None:
        return None
    return footprint_fp16 <= vram_gb


def vram_headroom_gb(footprint_fp16: float | None, vram_gb: float) -> float | None:
    if footprint_fp16 is None:
        return None
    return vram_gb - footprint_fp16


def quantization_required(param_count: float | None, vram_gb: float) -> str | None:
    if param_count is None:
        return None
    if model_footprint_gb(param_count, "fp16") <= vram_gb:
        return "none"
    if model_footprint_gb(param_count, "int8") <= vram_gb:
        return "8-bit"
    if model_footprint_gb(param_count, "int4") <= vram_gb:
        return "4-bit"
    return "does-not-fit"


def estimated_throughput(
    is_generative: bool,
    param_count: float | None,
    bandwidth_gbs: float | None,
    footprint_fp16: float | None,
) -> float | None:
    if not is_generative or param_count is None or not bandwidth_gbs or not footprint_fp16:
        return None
    return bandwidth_gbs / footprint_fp16
