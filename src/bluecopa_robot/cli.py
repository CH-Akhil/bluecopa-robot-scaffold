"""`bluecopa-robot` command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .generator import RobotSpec, generate, to_class_name, to_module_name


def _prompt(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{question}{suffix}: ").strip()
    except EOFError:
        answer = ""
    return answer or default


def _prompt_yes_no(question: str, default: bool) -> bool:
    d = "Y/n" if default else "y/N"
    try:
        answer = input(f"{question} [{d}]: ").strip().lower()
    except EOFError:
        answer = ""
    if not answer:
        return default
    return answer in ("y", "yes")


def _cmd_new(args: argparse.Namespace) -> int:
    module = to_module_name(args.name)
    class_name = args.class_name or to_class_name(module)

    interactive = sys.stdin is not None and sys.stdin.isatty()
    title = args.title
    description = args.description
    gcs = args.gcs

    if interactive:
        title = title or _prompt("Robot title (shown in the setup form)", module.replace("_", " ").title())
        description = description or _prompt("One-line description", f"{title} robot")
        if gcs is None:
            gcs = _prompt_yes_no("Does this robot read/write GCS?", default=False)
    else:
        title = title or module.replace("_", " ").title()
        description = description or f"{title} robot"
        gcs = bool(gcs)

    spec = RobotSpec(
        name=args.name,
        module=module,
        class_name=class_name,
        title=title,
        description=description,
        gcs=bool(gcs),
    )

    dest_parent = Path(args.dir).resolve()
    try:
        robot_dir = generate(spec, dest_parent)
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    _print_next_steps(spec, robot_dir)
    return 0


def _print_next_steps(spec: RobotSpec, robot_dir: Path) -> None:
    print(f"\nCreated {spec.class_name} at {robot_dir}\n")
    print("Next steps:")
    print(f"  1. cd {robot_dir.name}")
    print("  2. python -m venv .venv  (use Python 3.9 to match the SDK wheel)")
    print("     .venv\\Scripts\\python -m pip install -r requirements.txt")
    print("     .venv\\Scripts\\python -m pip install libs/*.whl")
    print(f"  3. Implement run_robot in rpa/{spec.module}.py  (a runnable stub is there now)")
    print("  4. Define your setup fields in rpa/spec.json")
    print("  5. Test locally:")
    print("     python main.py run --config secrets/config.sample.json "
          "--params secrets/params.sample.json --input-file-path dummy "
          "--output-folder-path ./output")
    print("  6. Read docs/building-a-bluecopa-robot.md before deploying — it covers")
    print("     the runtime contract, config/spec traps, and the deploy checklist.")
    print("\n  (Deployment builds a Docker image and pushes it to an ECR repo your")
    print("   backend/infra team creates — see docs/building-a-bluecopa-robot.md §7.)\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bluecopa-robot",
        description="Scaffold a new Bluecopa RPA robot.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    new = sub.add_parser("new", help="Create a new robot folder")
    new.add_argument("name", help="Robot name (e.g. 'invoice_splitter' or \"Invoice Splitter\")")
    new.add_argument("--title", default=None, help="Title shown in the setup form")
    new.add_argument("--description", default=None, help="One-line description")
    new.add_argument("--class-name", default=None, dest="class_name",
                     help="Robot class name (default: derived, PascalCase + 'Robot')")
    new.add_argument("--dir", default=".", help="Parent directory to create the robot in (default: cwd)")
    gcs_group = new.add_mutually_exclusive_group()
    gcs_group.add_argument("--gcs", dest="gcs", action="store_true", default=None,
                           help="Include the GCS helper (rpa/gcs.py) + google-cloud-storage")
    gcs_group.add_argument("--no-gcs", dest="gcs", action="store_false",
                           help="Do not include the GCS helper (base, no storage deps)")
    new.set_defaults(func=_cmd_new)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
