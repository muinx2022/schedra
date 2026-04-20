import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
CELERY_DIR = BACKEND_DIR / ".celery"
RESET = "\033[0m"
BACKEND_COLOR = "\033[96m"
FRONTEND_COLOR = "\033[93m"
WORKER_COLOR = "\033[95m"
BEAT_COLOR = "\033[92m"
SYSTEM_COLOR = "\033[90m"


def stream_output(prefix: str, process: subprocess.Popen[str], color: str) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"{color}[{prefix}]{RESET} {line.rstrip()}")


def ensure_backend_ready() -> None:
    env_file = BACKEND_DIR / ".env"
    env_example = BACKEND_DIR / ".env.example"
    if not env_file.exists() and env_example.exists():
        shutil.copyfile(env_example, env_file)

    subprocess.run(
        [sys.executable, "manage.py", "migrate"],
        cwd=BACKEND_DIR,
        check=True,
    )


def build_backend_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CELERY_TASK_ALWAYS_EAGER", "false")
    env.setdefault("CELERY_BROKER_URL", "filesystem://")
    env.setdefault("CELERY_RESULT_BACKEND", "")

    if env["CELERY_BROKER_URL"].startswith("filesystem://"):
        broker_root = CELERY_DIR / "broker"
        broker_queue = broker_root / "queue"
        broker_in = broker_queue
        broker_out = broker_queue
        broker_processed = broker_root / "processed"
        for path in (broker_in, broker_out, broker_processed):
            path.mkdir(parents=True, exist_ok=True)
        env.setdefault("CELERY_FILESYSTEM_BROKER_ROOT", str(broker_root))
        env.setdefault("CELERY_FILESYSTEM_BROKER_QUEUE", str(broker_queue))
        env.setdefault("CELERY_FILESYSTEM_BROKER_IN", str(broker_in))
        env.setdefault("CELERY_FILESYSTEM_BROKER_OUT", str(broker_out))
        env.setdefault("CELERY_FILESYSTEM_BROKER_PROCESSED", str(broker_processed))
        env.setdefault("CELERY_BEAT_SCHEDULE_FILENAME", str(CELERY_DIR / "beat-schedule"))

    return env


def terminate(process: subprocess.Popen[str] | None) -> None:
    if not process or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    print(f"{SYSTEM_COLOR}Preparing backend...{RESET}")
    ensure_backend_ready()
    backend_env = build_backend_env()

    frontend_env = os.environ.copy()
    frontend_env["NUXT_BACKEND_BASE"] = frontend_env.get("NUXT_BACKEND_BASE", "http://127.0.0.1:8000")
    frontend_env["NUXT_HOST"] = frontend_env.get("NUXT_HOST", "0.0.0.0")
    frontend_env["NUXT_PORT"] = frontend_env.get("NUXT_PORT", "443")
    frontend_env["NUXT_HTTPS"] = frontend_env.get("NUXT_HTTPS", "true")

    print(f"{SYSTEM_COLOR}Starting backend on http://127.0.0.1:8000{RESET}")
    backend = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "8000"],
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    print(f"{SYSTEM_COLOR}Starting Celery worker{RESET}")
    worker = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "config", "worker", "--loglevel=info", "--pool=solo"],
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    print(f"{SYSTEM_COLOR}Starting Celery beat{RESET}")
    beat = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "config", "beat", "--loglevel=info"],
        cwd=BACKEND_DIR,
        env=backend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
    frontend_url = "https://socialman.com" if frontend_env["NUXT_PORT"] == "443" else f"https://socialman.com:{frontend_env['NUXT_PORT']}"
    print(f"{SYSTEM_COLOR}Starting frontend on {frontend_url}{RESET}")
    frontend = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
        env=frontend_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    threads = [
        threading.Thread(target=stream_output, args=("backend", backend, BACKEND_COLOR), daemon=True),
        threading.Thread(target=stream_output, args=("worker", worker, WORKER_COLOR), daemon=True),
        threading.Thread(target=stream_output, args=("beat", beat, BEAT_COLOR), daemon=True),
        threading.Thread(target=stream_output, args=("frontend", frontend, FRONTEND_COLOR), daemon=True),
    ]
    for thread in threads:
        thread.start()

    print(f"{SYSTEM_COLOR}Login: demo@example.com / demo12345{RESET}")
    print(f"{SYSTEM_COLOR}Press Ctrl+C to stop both services.{RESET}")

    try:
        while True:
            if backend.poll() is not None:
                terminate(worker)
                terminate(beat)
                terminate(frontend)
                return backend.returncode or 0
            if worker.poll() is not None:
                terminate(beat)
                terminate(frontend)
                terminate(backend)
                return worker.returncode or 0
            if beat.poll() is not None:
                terminate(worker)
                terminate(frontend)
                terminate(backend)
                return beat.returncode or 0
            if frontend.poll() is not None:
                terminate(worker)
                terminate(beat)
                terminate(backend)
                return frontend.returncode or 0
            signal.pause() if hasattr(signal, "pause") else threading.Event().wait(0.5)
    except KeyboardInterrupt:
        print(f"\n{SYSTEM_COLOR}Stopping services...{RESET}")
        terminate(frontend)
        terminate(beat)
        terminate(worker)
        terminate(backend)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
