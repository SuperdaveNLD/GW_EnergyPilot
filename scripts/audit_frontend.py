#!/usr/bin/env python3
"""Audit the active GW EnergyPilot frontend import graph and runtime risk surface."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
INIT = INTEGRATION / "__init__.py"

IMPORT_RE = re.compile(r'^\s*import\s+["\'](?P<path>\./[^"\']+)["\']\s*;', re.MULTILINE)
PANEL_RE = re.compile(r'PANEL_MODULE\s*=.*?/(?P<name>gw-energy-pilot[^?"\']+\.js)')

PATTERNS: dict[str, re.Pattern[str]] = {
    "render_wrappers": re.compile(r"(?:prototype\._render\s*=|energyPilot\w*Render)"),
    "shadowroot_innerhtml": re.compile(r"shadowRoot\.innerHTML\s*="),
    "innerhtml_writes": re.compile(r"\.innerHTML\s*="),
    "insert_adjacent_html": re.compile(r"insertAdjacentHTML"),
    "queue_render": re.compile(r"\._queueRender\s*\("),
    "request_animation_frame": re.compile(r"requestAnimationFrame"),
    "set_timeout": re.compile(r"setTimeout"),
    "set_interval": re.compile(r"setInterval"),
    "resize_observer": re.compile(r"ResizeObserver"),
    "mutation_observer": re.compile(r"MutationObserver"),
    "scroll_writes": re.compile(r"(?:scrollTop|scrollLeft)\s*="),
    "scroll_reads": re.compile(r"(?:scrollTop|scrollLeft)"),
    "prevent_default": re.compile(r"preventDefault\s*\("),
    "stop_propagation": re.compile(r"stopPropagation\s*\("),
    "pointer_events": re.compile(r'["\'](?:pointerdown|pointermove|pointerup|pointercancel|pointerleave)["\']'),
    "touch_events": re.compile(r'["\'](?:touchstart|touchmove|touchend|touchcancel)["\']'),
    "wheel_events": re.compile(r'["\']wheel["\']'),
    "pointer_capture": re.compile(r"setPointerCapture|releasePointerCapture"),
    "css_animation": re.compile(r"(?:^|[;{\s])animation(?:-[a-z-]+)?\s*:", re.MULTILINE),
    "css_transition": re.compile(r"(?:^|[;{\s])transition(?:-[a-z-]+)?\s*:", re.MULTILINE),
    "css_transform": re.compile(r"(?:^|[;{\s])transform\s*:", re.MULTILINE),
    "css_filter": re.compile(r"(?:^|[;{\s])(?:backdrop-)?filter\s*:", re.MULTILINE),
    "css_fixed": re.compile(r"position\s*:\s*fixed"),
    "css_overflow": re.compile(r"overflow(?:-[xy])?\s*:", re.MULTILINE),
    "touch_action": re.compile(r"touch-action\s*:"),
}


@dataclass(frozen=True)
class ModuleAudit:
    path: str
    size_bytes: int
    imports: tuple[str, ...]
    counts: dict[str, int]


def active_entrypoint() -> Path:
    source = INIT.read_text(encoding="utf-8")
    match = PANEL_RE.search(source)
    if not match:
        raise RuntimeError("Unable to resolve PANEL_MODULE from __init__.py")
    path = FRONTEND / match.group("name")
    if not path.is_file():
        raise RuntimeError(f"Active frontend entrypoint does not exist: {path}")
    return path


def local_imports(path: Path, source: str) -> tuple[Path, ...]:
    result: list[Path] = []
    for match in IMPORT_RE.finditer(source):
        raw = match.group("path").split("?", 1)[0]
        imported = (path.parent / raw).resolve()
        try:
            imported.relative_to(FRONTEND.resolve())
        except ValueError as err:
            raise RuntimeError(f"Frontend import escapes frontend directory: {path} -> {raw}") from err
        if not imported.is_file():
            raise RuntimeError(f"Missing active frontend import: {path} -> {raw}")
        result.append(imported)
    return tuple(result)


def walk_graph(entrypoint: Path) -> tuple[list[Path], dict[Path, tuple[Path, ...]]]:
    ordered: list[Path] = []
    imports_by_path: dict[Path, tuple[Path, ...]] = {}
    state: dict[Path, str] = {}

    def visit(path: Path) -> None:
        marker = state.get(path)
        if marker == "visiting":
            raise RuntimeError(f"Circular active frontend import detected at {path}")
        if marker == "done":
            return
        state[path] = "visiting"
        source = path.read_text(encoding="utf-8")
        imports = local_imports(path, source)
        imports_by_path[path] = imports
        for imported in imports:
            visit(imported)
        state[path] = "done"
        ordered.append(path)

    visit(entrypoint)
    return ordered, imports_by_path


def audit_module(path: Path, imports: tuple[Path, ...]) -> ModuleAudit:
    source = path.read_text(encoding="utf-8")
    counts = {name: len(pattern.findall(source)) for name, pattern in PATTERNS.items()}
    return ModuleAudit(
        path=str(path.relative_to(ROOT)),
        size_bytes=len(source.encode("utf-8")),
        imports=tuple(str(item.relative_to(ROOT)) for item in imports),
        counts=counts,
    )


def markdown(entrypoint: Path, modules: list[ModuleAudit]) -> str:
    totals: Counter[str] = Counter()
    for module in modules:
        totals.update(module.counts)

    lines = [
        "# Active frontend audit",
        "",
        f"- Entrypoint: `{entrypoint.relative_to(ROOT)}`",
        f"- Active JavaScript modules: **{len(modules)}**",
        f"- Active source size: **{sum(item.size_bytes for item in modules):,} bytes**",
        f"- Render-wrapper signals: **{totals['render_wrappers']}**",
        f"- Full ShadowRoot replacements: **{totals['shadowroot_innerhtml']}**",
        f"- Explicit render requests: **{totals['queue_render']}**",
        f"- CSS animation declarations: **{totals['css_animation']}**",
        f"- CSS transition declarations: **{totals['css_transition']}**",
        f"- CSS transform declarations: **{totals['css_transform']}**",
        f"- CSS filter/backdrop-filter declarations: **{totals['css_filter']}**",
        f"- ResizeObserver references: **{totals['resize_observer']}**",
        f"- Scroll-position writes: **{totals['scroll_writes']}**",
        "",
        "## Per-module risk surface",
        "",
        "| Module | bytes | render | innerHTML | queue | animation | transition | transform | filter | rAF | timer | ResizeObserver | scroll writes | pointer | preventDefault |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    fields = (
        "render_wrappers",
        "innerhtml_writes",
        "queue_render",
        "css_animation",
        "css_transition",
        "css_transform",
        "css_filter",
        "request_animation_frame",
        "set_timeout",
        "resize_observer",
        "scroll_writes",
        "pointer_events",
        "prevent_default",
    )
    for module in modules:
        if not any(module.counts[field] for field in fields):
            continue
        values = " | ".join(str(module.counts[field]) for field in fields)
        lines.append(f"| `{module.path}` | {module.size_bytes} | {values} |")

    lines.extend(
        [
            "",
            "## Totals",
            "",
            "```json",
            json.dumps(dict(sorted(totals.items())), indent=2, sort_keys=True),
            "```",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, help="Write the complete audit as JSON")
    parser.add_argument("--markdown", type=Path, help="Write the Markdown report")
    args = parser.parse_args()

    entrypoint = active_entrypoint()
    ordered, imports_by_path = walk_graph(entrypoint)
    modules = [audit_module(path, imports_by_path[path]) for path in ordered]
    report = markdown(entrypoint, modules)
    print(report)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "entrypoint": str(entrypoint.relative_to(ROOT)),
                    "modules": [asdict(module) for module in modules],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
