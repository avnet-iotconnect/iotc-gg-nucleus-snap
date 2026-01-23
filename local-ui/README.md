# Greengrass Local Assistant

A local web UI that guides IOTCONNECT onboarding (connection kit or manual) and monitors Greengrass status and deployments on the same machine.

## Prerequisites

- Python 3.8+
- Greengrass snap installed (for real deployments)
- Optional: set `SETUP_SCRIPT_PATH` if you want to point to a custom `iot-greengrass-setup.py`

## Install

```bash
cd /home/mlamp/dev/edge/greengrass/aws-greengrass-snap/local-ui
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 app.py
```

Then open: `http://127.0.0.1:5055`

## Notes

- The UI runs entirely on `127.0.0.1` and keeps runs/logs in memory only.
- For Greengrass root detection, the app checks `SNAP_COMMON`, common snap paths, and `/tmp/greengrass/v2`.
- The manual onboarding flow pipes credentials to the existing setup script; nothing is persisted.
