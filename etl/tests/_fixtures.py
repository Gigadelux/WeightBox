"""Tiny synthetic source files, written from dicts keyed by the real CSV headers
so the fixtures stay in step with the ODS column contract.
"""

from __future__ import annotations

import csv
from pathlib import Path

from SQL.tables.ods import GPU_CSV_HEADERS, MODEL_CSV_HEADERS

# 7 models: 4 usable, 1 non-generative, 1 duplicate name, 1 with no Parameters
# but a size recoverable from its own name, 1 with no Parameters and no
# recoverable name (discarded).
MODEL_ROWS: list[dict[str, str]] = [
    {
        "Model": "Test-LLM-7B", "Organization": "OpenAI", "Publication date": "2024-03-14",
        "Domain": "Language", "Task": "Language modeling", "Parameters": "7000000000",
        "Training compute (FLOP)": "1e23", "Confidence": "Confident",
        "Country (of organization)": "United States",
    },
    {
        "Model": "Test-LLM-70B", "Organization": "Meta AI", "Publication date": "2024-07-01",
        "Domain": "Multimodal,Language,Vision", "Task": "Chat", "Parameters": "70000000000",
        "Confidence": "Likely",
    },
    {
        "Model": "Test-Diffusion-XL", "Organization": "Stability AI",
        "Publication date": "2023-11-20", "Domain": "Image generation",
        "Task": "Text-to-image", "Parameters": "3500000000",
    },
    {
        "Model": "Test-Vision-Net", "Organization": "Google", "Publication date": "2021-06-01",
        "Domain": "Vision", "Task": "Image classification", "Parameters": "300000000",
    },
    {
        "Model": "Test-Unknown-Params", "Organization": "Anthropic",
        "Publication date": "2025-01-09", "Domain": "Language", "Task": "Chat",
        "Parameters": "",
    },
    {
        "Model": "Test-Recovered-13B", "Organization": "Anthropic",
        "Publication date": "2025-02-11", "Domain": "Language", "Task": "Chat",
        "Parameters": "",
    },
    {
        "Model": "Test-LLM-7B", "Organization": "OpenAI", "Publication date": "2024-03-14",
        "Domain": "Language", "Task": "", "Parameters": "",
    },
]

# 6 GPUs: 3 usable, 1 pre-2016, 1 junk memType, 1 duplicate product name.
GPU_ROWS: list[dict[str, str]] = [
    {
        "manufacturer": "NVIDIA", "productName": "GeForce RTX 3070", "releaseYear": "2020",
        "memSize": "8", "memBusWidth": "256", "gpuClock": "1500", "memClock": "1750",
        "memType": "GDDR6", "gpuChip": "GA104", "bus": "PCIe 4.0 x16",
    },
    {
        "manufacturer": "NVIDIA", "productName": "GeForce RTX 4090", "releaseYear": "2022",
        "memSize": "24", "memBusWidth": "", "gpuClock": "2235", "memClock": "1313",
        "memType": " GDDR6X", "gpuChip": "AD102", "bus": "PCIe 4.0 x16",
    },
    {
        "manufacturer": "AMD", "productName": "Radeon RX 6800", "releaseYear": "2020",
        "memSize": "16", "memBusWidth": "256", "gpuClock": "1815", "memClock": "2000",
        "memType": "GDDR6", "gpuChip": "Navi 21", "bus": "PCIe 4.0 x16",
    },
    {
        "manufacturer": "NVIDIA", "productName": "GeForce GTX 780", "releaseYear": "2013",
        "memSize": "3", "memBusWidth": "384", "gpuClock": "863", "memClock": "1502",
        "memType": "GDDR5", "gpuChip": "GK110", "bus": "PCIe 3.0 x16",
    },
    {
        "manufacturer": "Intel", "productName": "Mystery GPU 9000", "releaseYear": "2021",
        "memSize": "8", "memBusWidth": "128", "gpuClock": "1200", "memClock": "1500",
        "memType": "VRAM", "gpuChip": "", "bus": "PCIe 4.0 x16",
    },
    {
        "manufacturer": "NVIDIA", "productName": "GeForce RTX 3070", "releaseYear": "2020",
        "memSize": "8", "memBusWidth": "", "gpuClock": "", "memClock": "",
        "memType": "GDDR6", "gpuChip": "", "bus": "",
    },
]


def _write(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})


def write_fixture_csvs(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    models = directory / "notable_ai_models.csv"
    gpus = directory / "gpu_specs_v7.csv"
    _write(models, MODEL_CSV_HEADERS, MODEL_ROWS)
    _write(gpus, GPU_CSV_HEADERS, GPU_ROWS)
    return models, gpus
