#!/usr/bin/env python3
"""Apply the small, deterministic config delta required by the isolated eval profile."""
import argparse

import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    with open(args.path, encoding="utf-8") as stream:
        config = yaml.safe_load(stream) or {}
    local = config.setdefault("providers", {}).setdefault("local", {})
    models = local.setdefault("models", {})
    for model in ("qwen3.5-2b", "qwen3.5-2b-lora"):
        entry = models.setdefault(model, {})
        entry["context_length"] = 65536
    config.setdefault("model", {})["max_tokens"] = 2048
    # Typed/no-algebra runs need no model-visible tools. Untyped runs opt back into hermes-cli
    # explicitly at invocation time. This lets local endpoints without auto tool choice use the
    # same Hermes conversation shell.
    config.setdefault("platform_toolsets", {})["cli"] = []
    enabled = config.setdefault("plugins", {}).setdefault("enabled", [])
    if "typed-bridge" not in enabled:
        enabled.append("typed-bridge")
    for entry in config.setdefault("auxiliary", {}).values():
        if isinstance(entry, dict) and entry.get("provider") == "custom":
            entry["model"] = "qwen3.5-2b"
            entry["context_length"] = 65536
            entry["max_tokens"] = 2048
    with open(args.path, "w", encoding="utf-8") as stream:
        yaml.safe_dump(config, stream, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    main()
