"""Visible experiment bounds; legacy configurations retain comprehensive coverage."""

from typing import Any

from .encoders import SPECS
from .formats import format_variants
from .validation import quality_targets


def experiment_plan(config: dict[str, Any]) -> dict[str, Any]:
    comparison = config.get("comparison", "comprehensive")
    if comparison not in ("initial", "comprehensive"):
        raise ValueError("comparison must be initial or comprehensive")
    encoders = config.get("encoders", [])
    variants = format_variants(config)
    samples = config["samples"]
    targets = quality_targets(config)
    limit = config.get("initial_trial_limit", 12)
    if type(limit) is not int or not 1 <= limit <= 24:
        raise ValueError("initial_trial_limit must be an integer from 1 to 24")
    if comparison == "initial" and (
        not 1 <= len(encoders) <= 3
        or len(set(encoders)) != len(encoders)
        or len(samples) > 2
        or len(variants) > 1
        or len(targets) > 4
    ):
        raise ValueError(
            "Initial comparison requires 1..3 explicit encoders, at most 2 samples, "
            "1 variant and 4 targets. Choose comprehensive for wider coverage; nothing is silently narrowed."
        )
    unknown = [name for name in encoders if name not in SPECS]
    if unknown:
        raise ValueError(f"Unsupported encoder config: {unknown}")
    finalists = 4 if config["mode"] == "quick" else 8
    passes = 2 if config["mode"] == "quick" else 4
    count = len(encoders) or len(SPECS)
    repeats = config.get("encode_repeats", 1)
    tuning = len(variants) * len(samples) ** 2 * min(count, finalists) * passes * len(targets)
    validation = 2 * len(variants) * len(targets) * len(config.get("validation_samples", []))
    return {
        "comparison": comparison,
        "mode": config["mode"],
        "encoders": [
            {"encoder": name, "codec": SPECS[name][0], "controls": SPECS[name][4]}
            for name in encoders
        ],
        "encoder_selection": "explicit" if encoders else "all installed configured adapters",
        "samples": samples,
        "validation_samples": config.get("validation_samples", []),
        "variants": variants,
        "quality_targets": targets,
        "encode_repeats": repeats,
        "budget_minutes": config["budget_minutes"],
        "bounds": {
            "screens": len(variants) * len(samples) * count,
            "tuning_attempts": min(tuning, limit) if comparison == "initial" else tuning,
            "validation_attempts": validation,
            "measured_encodes": (
                (min(tuning, limit) if comparison == "initial" else tuning) + validation
            )
            * repeats,
        },
        "estimate": {
            "seconds": None,
            "note": "Unknown until actual pilots; adaptive work may stop early. Bounds include failed attempts. "
            "Pilots, screens, hashing, references, scoring and review generation are additional work. "
            "The encoding budget starts after initialization. Overnight describes patience, not a deadline.",
        },
    }
