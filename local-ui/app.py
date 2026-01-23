import os
import uuid
import glob
import json
import time
import queue
import shutil
import platform
import threading
import subprocess
import signal
from datetime import datetime

from flask import Flask, jsonify, request, render_template, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
RUNS = {}
RUNS_LOCK = threading.Lock()

app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def detect_setup_script():
    override = os.environ.get("SETUP_SCRIPT_PATH")
    if override and os.path.exists(override):
        return override

    arch = platform.machine().lower()
    candidates = []
    if "arm" in arch or "aarch" in arch:
        candidates.append(os.path.join(BASE_DIR, "..", "arm64", "local-scripts", "iot-greengrass-setup.py"))
    else:
        candidates.append(os.path.join(BASE_DIR, "..", "amd64", "local-scripts", "iot-greengrass-setup.py"))

    # Fallback: first available local-scripts directory
    candidates.extend(glob.glob(os.path.join(BASE_DIR, "..", "*", "local-scripts", "iot-greengrass-setup.py")))

    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)

    return None


def list_candidate_roots():
    roots = []
    snap_common = os.environ.get("SNAP_COMMON")
    if snap_common:
        roots.append(os.path.join(snap_common, "greengrass", "v2"))

    roots.extend(glob.glob("/var/snap/*/common/greengrass/v2"))
    roots.append("/tmp/greengrass/v2")

    seen = set()
    unique = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def resolve_root(root_override=None):
    if root_override:
        return root_override

    for candidate in list_candidate_roots():
        if os.path.exists(candidate):
            return candidate

    # Default to first candidate even if not present
    candidates = list_candidate_roots()
    return candidates[0] if candidates else "/tmp/greengrass/v2"


def tail_file(path, lines=200):
    if not os.path.exists(path):
        return []

    with open(path, "r", errors="replace") as f:
        data = f.readlines()
    return [line.rstrip("\n") for line in data[-lines:]]


def read_snap_logs(lines=200):
    if not shutil.which("snap"):
        return None, "snap not available"
    try:
        attempts = [
            ["snap", "logs", "iotconnect-gg-nucleus.greengrass-daemon", "-n", str(lines)],
            ["snap", "logs", "iotconnect-gg-nucleus", "-n", str(lines)],
            ["snap", "logs", "iotconnect-gg-nucleus.greengrass-daemon", "-n", "all"],
            ["snap", "logs", "iotconnect-gg-nucleus", "-n", "all"],
            ["snap", "logs", "iotconnect-gg-nucleus.greengrass-daemon"],
            ["snap", "logs", "iotconnect-gg-nucleus"],
        ]

        last_error = ""
        for cmd in attempts:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode == 0 and result.stdout.strip():
                output = [line.rstrip("\n") for line in result.stdout.splitlines() if line.strip()]
                return output[-lines:], None
            last_error = result.stderr.strip() or result.stdout.strip() or "snap logs returned no output"
        return None, last_error
    except Exception as exc:
        return None, str(exc)


def read_greengrass_logs(greengrass_root, lines=200):
    if is_snap_install(greengrass_root):
        snap_lines, error = read_snap_logs(lines=lines)
        if snap_lines is not None:
            return snap_lines, "snap", None
        return [], "snap", error or "snap logs returned no output"

    log_path = os.path.join(greengrass_root, "logs", "greengrass.log")
    try:
        return tail_file(log_path, lines=lines), "file", None
    except PermissionError:
        return [], "file", "Permission denied reading greengrass.log"
    except Exception as exc:
        return [], "file", str(exc)


def detect_processes():
    try:
        result = subprocess.run(["pgrep", "-af", "Greengrass.jar"], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        processes = []
        for line in lines:
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[0].isdigit():
                processes.append({"pid": int(parts[0]), "cmd": parts[1]})
        return processes
    except Exception:
        return []


def find_greengrass_jar(greengrass_root):
    candidates = [
        os.path.join(greengrass_root, "alts", "current", "distro", "lib", "Greengrass.jar"),
        os.path.join(greengrass_root, "lib", "Greengrass.jar"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def start_greengrass(greengrass_root):
    jar_path = find_greengrass_jar(greengrass_root)
    if not jar_path:
        return False, "Greengrass.jar not found."

    cmd = [
        "java",
        f"-Droot={greengrass_root}",
        "-Dlog.store=FILE",
        "-jar",
        jar_path,
    ]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Greengrass started."
    except Exception as exc:
        return False, f"Failed to start Greengrass: {exc}"


def is_snap_install(greengrass_root):
    if greengrass_root.startswith("/var/snap/"):
        return True
    return os.path.exists("/var/snap/iotconnect-gg-nucleus")


def stop_greengrass():
    processes = detect_processes()
    if not processes:
        return True, "No Greengrass processes found."
    errors = []
    for proc in processes:
        try:
            os.kill(proc["pid"], signal.SIGTERM)
        except PermissionError:
            errors.append("Permission denied sending SIGTERM")
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        return False, "; ".join(errors)
    return True, "Stop signal sent."


def kill_greengrass():
    processes = detect_processes()
    if not processes:
        return True, "No Greengrass processes found."
    errors = []
    for proc in processes:
        try:
            os.kill(proc["pid"], signal.SIGKILL)
        except PermissionError:
            errors.append("Permission denied sending SIGKILL")
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        return False, "; ".join(errors)
    return True, "Kill signal sent."


def run_snap_command(action):
    if action not in {"start", "stop", "restart"}:
        return False, "Unsupported snap action."
    try:
        result = subprocess.run(
            ["snap", action, "iotconnect-gg-nucleus"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0:
            return True, f"snap {action} iotconnect-gg-nucleus succeeded."
        detail = result.stderr.strip() or result.stdout.strip() or "snap command failed."
        return False, detail
    except Exception as exc:
        return False, f"snap command error: {exc}"


def parse_deployment_status(log_lines):
    status = "unknown"
    detail = "No deployment signals found."

    for line in reversed(log_lines):
        if "Deployment" in line and "failed" in line.lower():
            status = "failed"
            detail = line
            break
        if "Deployment" in line and "successful" in line.lower():
            status = "successful"
            detail = line
            break
        if "deployment" in line.lower() and "starting" in line.lower():
            status = "in_progress"
            detail = line
            break

    return status, detail


def find_last_error(log_lines):
    for line in reversed(log_lines):
        if "ERROR" in line or "Exception" in line:
            return line
    return ""


def start_run(cmd, env=None, input_data=None):
    run_id = str(uuid.uuid4())
    record = {
        "id": run_id,
        "cmd": cmd,
        "status": "running",
        "startedAt": _now_iso(),
        "finishedAt": None,
        "returnCode": None,
        "log": [],
    }

    def _worker():
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
        )

        if input_data:
            try:
                process.stdin.write(input_data)
                process.stdin.flush()
                process.stdin.close()
            except Exception:
                pass

        try:
            for line in process.stdout:
                with RUNS_LOCK:
                    record["log"].append(line.rstrip("\n"))
        finally:
            process.wait()
            with RUNS_LOCK:
                record["status"] = "completed" if process.returncode == 0 else "failed"
                record["returnCode"] = process.returncode
                record["finishedAt"] = _now_iso()

    with RUNS_LOCK:
        RUNS[run_id] = record

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    return run_id


@app.route("/")
def index():
    setup_script = detect_setup_script()
    return render_template("index.html", setup_script=setup_script)


@app.route("/api/roots")
def api_roots():
    return jsonify({"roots": list_candidate_roots()})


@app.route("/api/status")
def api_status():
    root = request.args.get("root")
    greengrass_root = resolve_root(root)

    log_path = os.path.join(greengrass_root, "logs", "greengrass.log")
    try:
        log_lines = tail_file(log_path, lines=300)
    except Exception:
        log_lines = []
    deployment_state, deployment_detail = parse_deployment_status(log_lines)
    last_error = find_last_error(log_lines)
    processes = detect_processes()

    return jsonify({
        "root": greengrass_root,
        "exists": os.path.exists(greengrass_root),
        "logPath": log_path,
        "logExists": os.path.exists(log_path),
        "process": {
            "running": len(processes) > 0,
            "entries": processes,
        },
        "deployment": {
            "state": deployment_state,
            "detail": deployment_detail,
        },
        "lastError": last_error,
        "updatedAt": _now_iso(),
        "snapInstall": is_snap_install(greengrass_root),
    })


@app.route("/api/process/action", methods=["POST"])
def api_process_action():
    payload = request.get_json(silent=True) or {}
    action = (payload.get("action") or "").strip().lower()
    greengrass_root = resolve_root(payload.get("greengrassRoot"))

    if action not in {"start", "stop", "restart", "kill", "snap-start", "snap-stop", "snap-restart"}:
        return jsonify({"error": "unsupported action"}), 400

    if action == "start":
        if is_snap_install(greengrass_root):
            return jsonify({"error": "Snap install detected. Use Snap Start/Stop/Restart."}), 409
        if detect_processes():
            return jsonify({"message": "Greengrass already running."})
        success, detail = start_greengrass(greengrass_root)
        return jsonify({"message": detail}), (200 if success else 500)

    if action == "stop":
        if is_snap_install(greengrass_root):
            return jsonify({"error": "Snap install detected. Use Snap Start/Stop/Restart."}), 409
        success, detail = stop_greengrass()
        if not success and "Permission denied" in detail:
            return jsonify({"error": f"{detail}. Try running the UI with sudo or use Snap Stop."}), 403
        return jsonify({"message": detail}), (200 if success else 500)

    if action == "restart":
        if is_snap_install(greengrass_root):
            return jsonify({"error": "Snap install detected. Use Snap Start/Stop/Restart."}), 409
        stop_greengrass()
        time.sleep(1)
        success, detail = start_greengrass(greengrass_root)
        return jsonify({"message": detail}), (200 if success else 500)

    if action == "kill":
        if is_snap_install(greengrass_root):
            return jsonify({"error": "Snap install detected. Use Snap Start/Stop/Restart."}), 409
        success, detail = kill_greengrass()
        if not success and "Permission denied" in detail:
            return jsonify({"error": f"{detail}. Try running the UI with sudo or use Snap Stop."}), 403
        return jsonify({"message": detail}), (200 if success else 500)

    if action in {"snap-start", "snap-stop", "snap-restart"}:
        snap_action = action.split("-", 1)[1]
        success, detail = run_snap_command(snap_action)
        if not success and "permission" in detail.lower():
            return jsonify({"error": f"{detail}. Try running the UI with sudo."}), 403
        return jsonify({"message": detail}), (200 if success else 500)

    return jsonify({"error": "unsupported action"}), 400


@app.route("/api/logs")
def api_logs():
    try:
        root = request.args.get("root")
        greengrass_root = resolve_root(root)
        lines = int(request.args.get("lines", "200"))
        mode = request.args.get("mode", "auto").lower()
        log_path = os.path.join(greengrass_root, "logs", "greengrass.log")
        if mode != "manual" and is_snap_install(greengrass_root):
            return jsonify({
                "root": greengrass_root,
                "logPath": log_path,
                "lines": [],
                "source": "snap",
                "error": "Log fetch disabled in auto mode for snap installs to avoid password prompts. Use Refresh to load logs.",
            })
        log_lines, source, error = read_greengrass_logs(greengrass_root, lines=lines)
        return jsonify({
            "root": greengrass_root,
            "logPath": log_path,
            "lines": log_lines,
            "source": source,
            "error": error,
        })
    except Exception as exc:
        return jsonify({
            "root": None,
            "logPath": None,
            "lines": [],
            "source": None,
            "error": str(exc),
        }), 500


@app.route("/api/runs")
def api_runs():
    with RUNS_LOCK:
        runs = list(RUNS.values())
    return jsonify({"runs": runs})


@app.route("/api/runs/<run_id>")
def api_run_detail(run_id):
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        return jsonify({"error": "run not found"}), 404
    return jsonify(record)


@app.route("/api/onboard/connection-kit", methods=["POST"])
def api_onboard_connection_kit():
    ensure_dirs()

    kit_file = request.files.get("kit")
    kit_dir = request.form.get("kitDir")
    greengrass_root = request.form.get("greengrassRoot")

    if not kit_file:
        return jsonify({"error": "missing kit file"}), 400

    filename = f"{uuid.uuid4()}_{kit_file.filename}"
    kit_path = os.path.join(UPLOAD_DIR, filename)
    kit_file.save(kit_path)

    script_path = detect_setup_script()
    if not script_path:
        return jsonify({"error": "setup script not found"}), 500

    cmd = ["python3", script_path, "--connection-kit", kit_path]
    if kit_dir:
        cmd.extend(["--kit-dir", kit_dir])

    env = os.environ.copy()
    if greengrass_root:
        env["SNAP_COMMON"] = os.path.dirname(os.path.dirname(greengrass_root))

    run_id = start_run(cmd, env=env)
    return jsonify({"runId": run_id})


@app.route("/api/onboard/manual", methods=["POST"])
def api_onboard_manual():
    payload = request.get_json(silent=True) or {}

    access_key = (payload.get("accessKey") or "").strip()
    secret_key = (payload.get("secretKey") or "").strip()
    region = (payload.get("region") or "").strip()
    device_name = (payload.get("deviceName") or "").strip()
    greengrass_root = (payload.get("greengrassRoot") or "").strip()

    if not all([access_key, secret_key, region, device_name]):
        return jsonify({"error": "missing required fields"}), 400

    script_path = detect_setup_script()
    if not script_path:
        return jsonify({"error": "setup script not found"}), 500

    cmd = ["python3", script_path]
    input_data = "\n".join([access_key, secret_key, region, device_name]) + "\n"

    env = os.environ.copy()
    if greengrass_root:
        env["SNAP_COMMON"] = os.path.dirname(os.path.dirname(greengrass_root))

    run_id = start_run(cmd, env=env, input_data=input_data)
    return jsonify({"runId": run_id})


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


def main():
    ensure_dirs()
    port = int(os.environ.get("PORT", "5055"))
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
