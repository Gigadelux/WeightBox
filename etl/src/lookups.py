"""Static reference data for cleansing and transformation.

Sources: WEIGHTBOX_SPECS.md Appendix B (memory technology, curated GPU specs) and
Appendix C (domain to generative / throughput unit).
"""

from __future__ import annotations

# raw memType (trimmed, upper, internal whitespace collapsed) -> (mem_type, mem_family, data_rate)
MEM_TYPE_TABLE: dict[str, tuple[str, str, float]] = {
    "DDR": ("DDR", "DDR", 2),
    "SDR": ("DDR", "DDR", 2),
    "EDO": ("DDR", "DDR", 2),
    "FPM": ("DDR", "DDR", 2),
    "DDR2": ("DDR2", "DDR", 2),
    "DDR3": ("GDDR3", "GDDR", 2),
    "DDR4": ("GDDR3", "GDDR", 2),
    "GDDR2": ("GDDR3", "GDDR", 2),
    "GDDR3": ("GDDR3", "GDDR", 2),
    "GDDR4": ("GDDR4", "GDDR", 2),
    "GDDR5": ("GDDR5", "GDDR", 4),
    "GDDR5X": ("GDDR5X", "GDDR", 8),
    "GDDR6": ("GDDR6", "GDDR", 8),
    "GDDR6X": ("GDDR6X", "GDDR", 16),
    "GDDR7": ("GDDR7", "GDDR", 16),
    "HBM": ("HBM", "HBM", 2),
    "HBM2": ("HBM2e", "HBM", 2),
    "HBM2E": ("HBM2e", "HBM", 2),
    "HBM3": ("HBM3", "HBM", 2),
    "HBM3E": ("HBM3", "HBM", 2),
    "LPDDR4X": ("LPDDR5", "LPDDR", 4),
    "LPDDR5": ("LPDDR5", "LPDDR", 4),
}

JUNK_MEM_TOKENS: frozenset[str] = frozenset(
    {"VRAM", "DRAM", "SGR", "SGRAM", "CDRAM", "EDRAM", "", "NAN", "NONE", "N/A", "UNKNOWN"}
)

# Modal bus width by canonical mem_type, used when the source row omits it.
MODAL_BUS_WIDTH_BY_MEM_TYPE: dict[str, int] = {
    "DDR": 128,
    "DDR2": 128,
    "GDDR3": 256,
    "GDDR4": 256,
    "GDDR5": 256,
    "GDDR5X": 256,
    "GDDR6": 256,
    "GDDR6X": 384,
    "GDDR7": 256,
    "HBM": 4096,
    "HBM2e": 4096,
    "HBM3": 5120,
    "LPDDR5": 128,
}

# gpu_chip / product_name substring (upper) -> architecture. First match wins.
ARCH_PATTERNS: list[tuple[str, str]] = [
    ("GB20", "Blackwell"),
    ("GB10", "Blackwell"),
    ("AD10", "Ada Lovelace"),
    ("GH100", "Hopper"),
    ("GH200", "Hopper"),
    ("GA10", "Ampere"),
    ("GA100", "Ampere"),
    ("TU10", "Turing"),
    ("TU11", "Turing"),
    ("GV100", "Volta"),
    ("GP10", "Pascal"),
    ("GM20", "Maxwell"),
    ("GK", "Kepler"),
    ("NAVI 4", "RDNA 4"),
    ("NAVI 3", "RDNA 3"),
    ("NAVI 2", "RDNA 2"),
    ("NAVI 1", "RDNA"),
    ("NAVI 3X", "RDNA 3"),
    ("VEGA", "GCN 5 (Vega)"),
    ("POLARIS", "GCN 4 (Polaris)"),
    ("BATTLEMAGE", "Arc Battlemage"),
    ("ALCHEMIST", "Arc Alchemist"),
    ("BMG", "Arc Battlemage"),
    ("DG2", "Arc Alchemist"),
    ("RTX 50", "Blackwell"),
    ("RTX 40", "Ada Lovelace"),
    ("RTX 30", "Ampere"),
    ("RTX 20", "Turing"),
    ("GTX 16", "Turing"),
    ("GTX 10", "Pascal"),
    ("RX 90", "RDNA 4"),
    ("RX 7", "RDNA 3"),
    ("RX 6", "RDNA 2"),
    ("RX 5", "RDNA"),
    ("ARC A", "Arc Alchemist"),
    ("ARC B", "Arc Battlemage"),
]

# Curated product_name (upper, spaces collapsed) -> (bus_width_bit, vram_gb).
# Only the cards whose memBusWidth the source CSV omits. Products that already
# carry a real bus width and VRAM (the 2022+ desktop and datacentre parts) are
# left out on purpose: the loader uses the source value and this map would never
# fire for them.
CURATED_GPU_SPECS: dict[str, tuple[int, float]] = {
    "GEFORCE RTX 4060 TI": (128, 8),
    "GEFORCE RTX 3090": (384, 24),
    "GEFORCE RTX 3080": (320, 10),
    "GEFORCE RTX 3070": (256, 8),
    "GEFORCE RTX 3060": (192, 12),
    "GEFORCE RTX 2080 TI": (352, 11),
    "GEFORCE GTX 1080 TI": (352, 11),
    "GEFORCE GTX 1080": (256, 8),
    "GEFORCE GTX 1060": (192, 6),
    "RADEON RX 6900 XT": (256, 16),
    "RADEON RX 6800 XT": (256, 16),
    "RADEON RX 6800": (256, 16),
    "RADEON RX 6700 XT": (192, 12),
    "A100 PCIE 40 GB": (5120, 40),
    "A100 PCIE 80 GB": (5120, 80),
    "A100 SXM4 40 GB": (5120, 40),
    "A100 SXM4 80 GB": (5120, 80),
}

ORG_ALIASES: dict[str, str] = {
    "GOOGLE": "Google DeepMind",
    "DEEPMIND": "Google DeepMind",
    "GOOGLE DEEPMIND": "Google DeepMind",
    "GOOGLE BRAIN": "Google DeepMind",
    "GOOGLE RESEARCH": "Google DeepMind",
    "META": "Meta AI",
    "META AI": "Meta AI",
    "FACEBOOK": "Meta AI",
    "FACEBOOK AI RESEARCH": "Meta AI",
    "FAIR": "Meta AI",
    "OPENAI": "OpenAI",
    "MICROSOFT": "Microsoft",
    "MICROSOFT RESEARCH": "Microsoft",
    "ANTHROPIC": "Anthropic",
    "MISTRAL AI": "Mistral AI",
    "MISTRAL": "Mistral AI",
    "ALIBABA": "Alibaba",
    "ALIBABA GROUP": "Alibaba",
    "QWEN TEAM": "Alibaba",
    "DEEPSEEK": "DeepSeek",
    "DEEPSEEK-AI": "DeepSeek",
    "ZHIPU AI": "Zhipu AI",
    "Z.AI": "Zhipu AI",
    "Z.AI (ZHIPU AI)": "Zhipu AI",
    "XAI": "xAI",
    "STABILITY AI": "Stability AI",
    "NVIDIA": "NVIDIA",
    "COHERE": "Cohere",
    "AI21 LABS": "AI21 Labs",
    "MOONSHOT AI": "Moonshot AI",
    "TENCENT": "Tencent",
    "BAIDU": "Baidu",
    "HUGGING FACE": "Hugging Face",
    "ELEUTHERAI": "EleutherAI",
    "ALLEN INSTITUTE FOR AI": "Allen Institute for AI",
    "AI2": "Allen Institute for AI",
}

# Verbose "Country (of organization)" values -> short form. The source column is
# populated for every row that has a country, so this only tidies the spelling of
# the handful of UN-style long names; it is not a per-organisation guess table.
COUNTRY_NORMALISE: dict[str, str] = {
    "United States of America": "United States",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "Korea (Republic of)": "South Korea",
    "Korea (Democratic People's Republic of)": "North Korea",
    "Russian Federation": "Russia",
    "Iran (Islamic Republic of)": "Iran",
    "Viet Nam": "Vietnam",
    "Taiwan, Province of China": "Taiwan",
}

DOMAIN_PRIORITY: list[str] = [
    "Language",
    "Multimodal",
    "Image generation",
    "Video",
    "Speech",
    "Audio",
    "Vision",
    "Games",
    "Biology",
    "Robotics",
    "Recommendation",
    "Mathematics",
    "Other",
]

# primary_domain -> (is_generative, throughput_unit or None)
DOMAIN_GENERATIVE: dict[str, tuple[bool, str | None]] = {
    "Language": (True, "tokens/sec"),
    "Multimodal": (True, "tokens/sec"),
    "Speech": (True, "tokens/sec"),
    "Audio": (True, "tokens/sec"),
    "Video": (True, "tokens/sec"),
    "Image generation": (True, "images/sec"),
    "Vision": (False, None),
    "Games": (False, None),
    "Biology": (False, None),
    "Robotics": (False, None),
    "Recommendation": (False, None),
    "Mathematics": (False, None),
    "Other": (False, None),
}

# keyword in Task (lower) -> domain, used only when Domain is missing.
TASK_DOMAIN_HINTS: list[tuple[str, str]] = [
    ("language modeling", "Language"),
    ("text generation", "Language"),
    ("chat", "Language"),
    ("question answering", "Language"),
    ("translation", "Language"),
    ("code generation", "Language"),
    ("image generation", "Image generation"),
    ("text-to-image", "Image generation"),
    ("video generation", "Video"),
    ("speech recognition", "Speech"),
    ("text-to-speech", "Speech"),
    ("speech synthesis", "Speech"),
    ("object detection", "Vision"),
    ("image classification", "Vision"),
    ("segmentation", "Vision"),
    ("recommendation", "Recommendation"),
    ("protein", "Biology"),
    ("game", "Games"),
    ("robot", "Robotics"),
]

# Numeric assumptions (Appendix D).
BYTES_PER_WEIGHT: dict[str, float] = {"fp16": 2.0, "int8": 1.0, "int4": 0.5}
OVERHEAD_FACTOR: float = 1.20

PARAMETER_MIN: float = 1e3
PARAMETER_MAX: float = 5e12

GPU_MIN_RELEASE_YEAR: int = 2016
