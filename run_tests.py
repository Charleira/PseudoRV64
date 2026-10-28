"""Launcher local com infraestrutura confiável e resultados por caso."""

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path


class Report:
    """Guarde resultados por ID, inclusive falhas anteriores ao corpo do teste."""

    def __init__(self):
        self.cases = {}
        self.errors = []

    def pytest_collection_finish(self, session):
        self.cases = {
            i.nodeid: {"result": "NOT_RUN", "reason": ""} for i in session.items
        }

    def pytest_collectreport(self, report):
        if report.failed:
            self.errors.append(str(report.longrepr))

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or report.failed:
            self.cases[report.nodeid] = {
                "result": "PASS" if report.passed else "FAIL",
                "reason": "" if report.passed else str(report.longrepr),
            }


def main():
    root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--implementation", type=Path, default=root)
    p.add_argument("--closed", action="store_true")
    p.add_argument("--collect-only", action="store_true")
    p.add_argument("--report", type=Path, default=Path("test-results.json"))
    args = p.parse_args()
    target = args.implementation.resolve()
    os.environ["MICROC_CODEGEN_DIR"] = str(target)
    sys.path.insert(0, str(target))
    import load_previous

    # A implementação avaliada usa as classes oficiais fornecidas pelo docente.
    for name in ("ir", "executor", "patterns"):
        spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    sys.path.insert(0, str(root / "tests"))
    import pytest

    paths = [str(root / "tests")]
    if args.closed:
        closed = root.parent / "tests"
        if not closed.is_dir():
            p.error("suíte fechada indisponível")
        paths.append(str(closed))
    # Registrar NOT_RUN na coleta distingue um caso ausente de um caso reprovado.
    report = Report()
    start = time.monotonic()
    status = pytest.main(
        ["-q", "--timeout=10", "--rootdir", str(root.parent), *paths]
        + (["--collect-only"] if args.collect_only else []),
        plugins=[report],
    )
    sources = list(root.glob("*.py")) + list((root / "tests").glob("*.py"))
    if args.closed:
        sources += list(closed.glob("*.py"))
    hashes = {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    args.report.write_text(
        json.dumps(
            {
                "status": int(status),
                "seconds": time.monotonic() - start,
                "python": sys.version,
                "pytest": pytest.__version__,
                "hashes": hashes,
                "collection_errors": report.errors,
                "cases": report.cases,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return int(status)


if __name__ == "__main__":
    raise SystemExit(main())
