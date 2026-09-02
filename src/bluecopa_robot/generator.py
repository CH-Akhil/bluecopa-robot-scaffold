"""Generate a new robot folder from the packaged template tree.

Pure of any client specifics: no registry, repo, or ECR path is ever emitted.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

WHEEL_NAME = "bluecopa_rpa_python-0.1.0-py3-none-any.whl"
GCS_REQUIREMENT = "google-cloud-storage==2.16.0"

# Template files that must only be emitted for a --gcs robot (relative to the
# template root, with the trailing .tmpl stripped).
_GCS_ONLY = {"rpa/gcs.py"}


@dataclass
class RobotSpec:
    name: str          # raw name the user typed
    module: str        # snake_case folder + rpa module
    class_name: str    # PascalCase + "Robot"
    title: str         # human title for spec.json / README
    description: str    # one-line description
    gcs: bool          # include the GCS helper + dependency

    @property
    def replacements(self) -> dict:
        return {
            "robot_name": self.name,
            "robot_module": self.module,
            "RobotClass": self.class_name,
            "robot_title": self.title,
            "robot_description": self.description,
        }


def to_module_name(name: str) -> str:
    """snake_case module/folder name from arbitrary input."""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip()).strip("_").lower()
    if not s:
        raise ValueError("robot name must contain at least one letter or digit")
    if s[0].isdigit():
        s = "r_" + s
    return s


def to_class_name(module: str) -> str:
    """PascalCase class name (with a Robot suffix) from a module name."""
    parts = [p for p in module.split("_") if p]
    pascal = "".join(p.capitalize() for p in parts)
    return pascal if pascal.endswith("Robot") else pascal + "Robot"


def _substitute(text: str, replacements: dict) -> str:
    for key, value in replacements.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _template_root():
    return resources.files("bluecopa_robot") / "_templates"


def _iter_template_files(root):
    """Yield (posix_relpath_without_tmpl, traversable) for every template file."""
    stack = [(root, "")]
    while stack:
        node, prefix = stack.pop()
        for child in node.iterdir():
            rel = f"{prefix}{child.name}" if prefix else child.name
            if child.is_dir():
                stack.append((child, rel + "/"))
            else:
                out_rel = rel[:-5] if rel.endswith(".tmpl") else rel
                yield out_rel, child


def generate(spec: RobotSpec, dest_parent: Path) -> Path:
    """Create the robot folder under dest_parent. Returns the robot path."""
    robot_dir = dest_parent / spec.module
    if robot_dir.exists():
        raise FileExistsError(f"{robot_dir} already exists — choose another name or remove it")

    replacements = spec.replacements
    root = _template_root()

    for out_rel, node in _iter_template_files(root):
        if out_rel in _GCS_ONLY and not spec.gcs:
            continue
        # Substitute placeholders in path segments too (e.g. {{robot_module}}.py).
        out_rel_final = _substitute(out_rel, replacements)
        target = robot_dir / out_rel_final
        target.parent.mkdir(parents=True, exist_ok=True)
        text = node.read_text(encoding="utf-8")
        _write_text(target, _substitute(text, replacements))

    # Vendor the SDK wheel (binary — copied verbatim).
    libs = robot_dir / "libs"
    libs.mkdir(parents=True, exist_ok=True)
    wheel_src = resources.files("bluecopa_robot") / "_assets" / WHEEL_NAME
    (libs / WHEEL_NAME).write_bytes(wheel_src.read_bytes())

    # requirements.txt is generated (not templated) so the base stays truly empty.
    reqs = [GCS_REQUIREMENT] if spec.gcs else []
    header = "# Robot dependencies. The Bluecopa SDK wheel is installed from libs/ (see Dockerfile).\n"
    _write_text(robot_dir / "requirements.txt", header + ("\n".join(reqs) + "\n" if reqs else ""))

    return robot_dir


def _write_text(path: Path, text: str) -> None:
    """Write text with LF newlines (Path.write_text has no newline= on 3.9)."""
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
