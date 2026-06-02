import ast
import pathlib

_DOMAIN_DIR = pathlib.Path(__file__).parent.parent / "src" / "domains"
_FORBIDDEN_PREFIXES = ("httpx", "typer", "asyncer", "crawler", "gateways")


def _imported_modules(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def test_domain_layer_has_no_outward_or_thirdparty_imports() -> None:
    offenders: dict[str, set[str]] = {}
    for py_file in _DOMAIN_DIR.rglob("*.py"):
        bad = {
            mod for mod in _imported_modules(py_file) if mod.split(".")[0] in _FORBIDDEN_PREFIXES
        }
        if bad:
            offenders[str(py_file)] = bad
    assert not offenders, f"domain layer imports forbidden modules: {offenders}"
