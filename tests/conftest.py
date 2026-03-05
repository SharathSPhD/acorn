"""Root test configuration for ACORN."""
import ast
import pathlib
import pytest


def pytest_collect_file(parent, file_path):  # noqa: ARG001  # pyright: ignore[reportUnusedParameter]
    """Fail collection if any production module is missing __pattern__."""
    if file_path.suffix == ".py" and file_path.stat().st_size > 0:
        # Only check api/ and memory/ modules, not tests or __init__
        rel = file_path.relative_to(pathlib.Path(__file__).parent.parent)
        parts = rel.parts
        if parts[0] not in ("api", "memory"):
            return None
        if file_path.name.startswith("_"):
            return None
        src = file_path.read_text()
        if not src.strip():
            return None
        try:
            tree = ast.parse(src)
        except SyntaxError:
            return None
        has_pattern = any(
            isinstance(n, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "__pattern__"
                for t in n.targets
            )
            for n in ast.walk(tree)
        )
        if not has_pattern:
            raise pytest.PytestCollectionWarning(
                f"Production module missing __pattern__: {rel}"
            )
    return None
