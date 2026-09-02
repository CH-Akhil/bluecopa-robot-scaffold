"""Tests for the robot generator. Runnable via pytest or `python tests/test_generate.py`."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bluecopa_robot.generator import (  # noqa: E402
    RobotSpec,
    generate,
    to_class_name,
    to_module_name,
)

WHEEL = "bluecopa_rpa_python-0.1.0-py3-none-any.whl"


def _spec(name="sample_robot", gcs=True):
    module = to_module_name(name)
    return RobotSpec(
        name=name,
        module=module,
        class_name=to_class_name(module),
        title="Sample Robot",
        description="a demo robot",
        gcs=gcs,
    )


def test_name_derivations():
    assert to_module_name("Invoice Splitter") == "invoice_splitter"
    assert to_module_name("2way-recon") == "r_2way_recon"
    assert to_class_name("invoice_splitter") == "InvoiceSplitterRobot"
    assert to_class_name("zip") == "ZipRobot"
    assert to_class_name("my_robot") == "MyRobot"  # already ends with Robot


def test_generate_with_gcs():
    with tempfile.TemporaryDirectory() as tmp:
        spec = _spec(gcs=True)
        robot = generate(spec, Path(tmp))

        expected = [
            "main.py", "__init__.py", "Dockerfile", "requirements.txt",
            ".gitignore", ".dockerignore", "README.md", "CLAUDE.md",
            f"libs/{WHEEL}",
            "rpa/__init__.py", "rpa/sample_robot.py", "rpa/gcs.py",
            "rpa/spec.json", "rpa/Exceptions/__init__.py",
            "secrets/config.sample.json", "secrets/params.sample.json",
            "docs/building-a-bluecopa-robot.md",
        ]
        for rel in expected:
            assert (robot / rel).exists(), f"missing {rel}"

        # wheel is a real binary, not empty
        assert (robot / "libs" / WHEEL).stat().st_size > 1000

        # no leftover placeholders / stray .tmpl files in any text file
        for p in robot.rglob("*"):
            if p.is_file() and p.suffix != ".whl":
                assert not p.name.endswith(".tmpl"), f"stray template file {p}"
                text = p.read_text(encoding="utf-8")
                assert "{{" not in text and "}}" not in text, f"unsubstituted placeholder in {p}"

        # class + module wired through
        assert "class SampleRobot(AbstractRobot)" in (robot / "rpa/sample_robot.py").read_text(encoding="utf-8")
        assert "from rpa.sample_robot import SampleRobot" in (robot / "main.py").read_text(encoding="utf-8")

        # gcs on → helper + dependency present
        assert "google-cloud-storage" in (robot / "requirements.txt").read_text(encoding="utf-8")


def test_generate_without_gcs():
    with tempfile.TemporaryDirectory() as tmp:
        robot = generate(_spec(gcs=False), Path(tmp))
        assert not (robot / "rpa" / "gcs.py").exists(), "gcs.py should be absent without --gcs"
        assert "google-cloud-storage" not in (robot / "requirements.txt").read_text(encoding="utf-8")
        # base is otherwise complete
        assert (robot / "main.py").exists()
        assert (robot / "docs/building-a-bluecopa-robot.md").exists()


def test_refuses_to_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        generate(_spec(), Path(tmp))
        try:
            generate(_spec(), Path(tmp))
        except FileExistsError:
            pass
        else:
            raise AssertionError("expected FileExistsError on second generate")


if __name__ == "__main__":
    test_name_derivations()
    test_generate_with_gcs()
    test_generate_without_gcs()
    test_refuses_to_overwrite()
    print("all tests passed")
