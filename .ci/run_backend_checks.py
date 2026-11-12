"""Run existing backend tests with synthetic settings and a process guard."""

import os
from pathlib import Path
import sys


class OfflineViolation(RuntimeError):
    pass


def main():
    backend = Path(__file__).resolve().parents[1] / "backend"
    root = backend.parent

    if Path.cwd().resolve() != backend:
        print("CI_SETUP_ERROR: run from backend/", file=sys.stderr)
        return 2

    for path in (root / ".env", backend / ".env"):
        if path.exists() or path.is_symlink():
            print("CI_SETUP_ERROR: dotenv file present", file=sys.stderr)
            return 2

    synthetic = {
        "DATABASE_URL": "sqlite://",
        "APP_ENV": "test",
        "OPENAI_API_KEY": "",
        "OPENAI_MODEL": "gpt-4o",
        "ZAPIER_WEBHOOK_SECRET": "",
        "GHL_API_TOKEN": "",
        "GHL_LOCATION_ID": "ci-location",
        "GHL_PIPELINE_ID": "ci-pipeline",
        "GHL_PIPELINE_STAGE_ID": "ci-stage",
        "GHL_YELP_SOURCE": "YELP",
        "HCP_API_KEY": "",
        "GHL_LOOKUP_TIMEOUT_SECONDS": "1.5",
        "KB_PATH": str(backend / "data" / "fast_glass_kb.json"),
        "LOG_LEVEL": "INFO",
    }
    replaced = {key.casefold() for key in synthetic}
    for key in tuple(os.environ):
        if key.casefold() in replaced or key.startswith("PYTEST_"):
            del os.environ[key]
    os.environ.update(synthetic)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(backend))

    blocked = []
    prohibited = {
        "socket.connect",
        "socket.bind",
        "socket.sendto",
        "socket.sendmsg",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
    }

    def audit(event, args):
        if event in prohibited:
            blocked.append(event)
            raise OfflineViolation(
                "CI_OFFLINE_BLOCKED: " + event
                + " (destination and arguments redacted)"
            )

    sys.addaudithook(audit)

    try:
        import pytest

        result = int(pytest.main([
            "-q",
            "-p", "pytest_asyncio.plugin",
            "-p", "no:cacheprovider",
            "--tb=short",
            "tests",
        ]))
    except Exception as exc:
        print(
            "CI_RUNNER_ERROR: " + type(exc).__name__,
            file=sys.stderr,
        )
        result = 2

    if blocked:
        print(
            "CI_OFFLINE_BLOCKED: count=" + str(len(blocked))
            + "; events=" + ",".join(sorted(set(blocked))),
            file=sys.stderr,
        )
        return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
