"""Visible experiment bounds; legacy configurations retain comprehensive coverage."""

from typing import Any

from .encoders import SPECS
from .formats import format_variants
from .validation import quality_targets


def fixed_settings(config: dict[str, Any]) -> dict[str, list[int]]:
    encoders = config.get("encoders", ["libx265", "libsvtav1", "hevc_nvenc"]) or list(SPECS)
    if (
        not isinstance(encoders, list)
        or any(not isinstance(e, str) for e in encoders)
        or len(set(encoders)) != len(encoders)
    ):
        raise ValueError("encoders must be a list of unique encoder names")
    supplied = config.get("fixed_settings", {})
    if not isinstance(supplied, dict) or set(supplied) - set(encoders):
        raise ValueError("fixed_settings must map selected encoders to quality lists")
    settings = {}
    for name in encoders:
        if name not in SPECS:
            raise ValueError(f"Unsupported encoder config: {name}")
        _, initial, low, high, _ = SPECS[name]
        values = supplied.get(
            name,
            [
                initial,
                max(low, initial - 6) if name.endswith("_videotoolbox") else min(high, initial + 6),
            ],
        )
        if (
            not isinstance(values, list)
            or not values
            or len(values) > 8
            or any(type(q) is not int or not low <= q <= high for q in values)
            or len(set(values)) != len(values)
        ):
            raise ValueError(
                f"fixed_settings for {name} requires 1..8 unique integers in {low}..{high}"
            )
        settings[name] = values
    return settings


def experiment_plan(config: dict[str, Any]) -> dict[str, Any]:
    strategy = config.get("strategy", "tune")
    if strategy not in ("fixed", "tune"):
        raise ValueError("strategy must be fixed or tune")
    if strategy == "fixed":
        settings = fixed_settings(config)
        variants = format_variants(config)
        count = len(config["samples"]) * len(variants) * sum(map(len, settings.values()))
        return {
            "strategy": "fixed",
            "comparison": "fixed",
            "mode": config["mode"],
            "encoders": [
                {
                    "encoder": name,
                    "codec": SPECS[name][0],
                    "controls": SPECS[name][4],
                    "qualities": values,
                }
                for name, values in settings.items()
            ],
            "samples": config["samples"],
            "variants": variants,
            "quality_targets": [],
            "encode_repeats": config.get("encode_repeats", 1),
            "budget_minutes": config["budget_minutes"],
            "bounds": {
                "screens": 0,
                "tuning_attempts": 0,
                "validation_attempts": 0,
                "measured_encodes": count * config.get("encode_repeats", 1),
            },
            "estimate": {
                "seconds": None,
                "note": "Bounded synthetic capability checks precede footage measurements (up to 3 frames per combination, 10 seconds each, 30 seconds total within allowance). They do not measure quality or throughput. Remaining estimates update from measured encode/scoring/preparation times. Budget includes initialization and reserves report/review time; cleanup and final writes may slightly overrun. No target search or separate pilots. Additional scenes check the first-scene measured frontier.",
            },
        }
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
