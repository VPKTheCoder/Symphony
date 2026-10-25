"""Timeline and listening-guide output for generated compositions."""

from __future__ import annotations

import json
from pathlib import Path

def _clock(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, rest = divmod(total, 60)
    return f"{minutes:02d}:{rest:02d}"


def build_timeline(composition) -> dict:
    form = composition.form
    profile = composition.profile
    module_lookup = profile.modules_by_name
    seconds_per_bar = form.meter_beats_per_bar * form.seconds_per_beat
    complexity_threshold = 0.70
    sections = []
    guide = []
    for section in form.sections:
        start = section.start_bar * seconds_per_bar
        end = section.end_bar * seconds_per_bar
        modules = [module.name for module in section.modules]
        moments = []
        for index, name in enumerate(modules):
            module = module_lookup[name]
            moment_time = start + (end - start) * ((index + 1) / (len(modules) + 1))
            details = []
            if section.name in {"intro", "theme", "development", "climax", "outro"}:
                signature_text = composition.variation_plan.signature_label
                details.append(signature_text)
                moments.append({
                    "type": "signature",
                    "description": signature_text,
                    "module": name,
                    "time": round(moment_time, 3),
                })
            if module.complexity >= complexity_threshold:
                details.append("complexity hotspot: rising rhythmic and register intensity")
                moments.append({"type": "complexity_hotspot", "module": name, "time": round(moment_time, 3)})
            if module.unsafe_count:
                details.append("unsafe: diminished color and violin tremolo")
                moments.append({"type": "unsafe", "module": name, "time": round(moment_time, 3)})
            if module.todo_count:
                details.append("TODO: brief sus4/rest interruption")
                moments.append({"type": "todo", "module": name, "time": round(moment_time, 3)})
            cadence = "resolved cadence" if module.test_coverage >= 0.55 else "open cadence"
            details.append(f"coverage: {cadence}")
            moments.append({
                "type": "coverage_cadence",
                "module": name,
                "decision": cadence,
                "time": round(moment_time, 3),
            })
            focus = {
                "intro": "listen for the opening texture",
                "theme": "listen for the main melody and module motif",
                "development": "listen for the build and changing textures",
                "climax": "listen for the full-band lift",
                "resolution": "listen for the cadence",
                "outro": "listen for the ending and fade",
            }[section.name]
            guide.append({
                "time": round(moment_time, 3),
                "module": name,
                "section": section.name,
                "what_to_listen_for": focus + "; " + ", ".join(details),
            })
        if not modules:
            signature_text = composition.variation_plan.signature_label
            focus = {
                "intro": "listen for the opening texture",
                "outro": "listen for the ending and fade",
            }.get(section.name, "listen for the transition")
            if section.name in {"intro", "theme", "development", "climax", "outro"}:
                moments.append({
                    "type": "signature",
                    "description": signature_text,
                    "module": "framing",
                    "time": round(start, 3),
                })
            guide.append({
                "time": round(start, 3),
                "module": "framing",
                "section": section.name,
                "what_to_listen_for": focus + (
                    f"; {signature_text}"
                    if section.name in {"intro", "theme", "development", "climax", "outro"}
                    else ""
                ),
            })
        sections.append({
            "name": section.name,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "start_label": _clock(start),
            "end_label": _clock(end),
            "modules": modules,
            "moments": moments,
        })
    return {
        "profile": profile.name,
        "repo_fingerprint": composition.variation_plan.repo_fingerprint,
        "style": composition.style.name,
        "seed": composition.seed,
        "tempo": form.tempo,
        "key": form.key.label,
        "meter": f"{form.meter[0]}/{form.meter[1]}",
        "hook": {
            "id": composition.variation_plan.hook_id,
            "contour": list(composition.variation_plan.hook_contour),
        },
        "signature": composition.variation_plan.signature_label,
        "coverage_source": profile.coverage_source,
        "sections": sections,
        "listening_guide": guide,
    }


def write_timeline(composition, output_prefix: str | Path) -> Path:
    prefix = Path(output_prefix)
    path = prefix.with_name(prefix.name + ".timeline.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_timeline(composition), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def format_listening_guide(timeline: dict) -> str:
    lines = [
        "Listening guide",
        f"{'Time':>8}  {'Section':12}  {'Module':28}  What to listen for",
        "-" * 110,
    ]
    for item in timeline["listening_guide"]:
        module = str(item["module"])
        lines.append(
            f"{_clock(item['time']):>8}  {item['section']:12}  {module[:28]:28}  "
            f"{item['what_to_listen_for']}"
        )
    return "\n".join(lines)
