#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -r plant_disease_detector/requirements.txt
# The evaluated checkpoint is stored as repository-sized base64 chunks so the
# connected GitHub publisher can transfer it without truncating a binary blob.
MODEL_DIR="plant_disease_detector/deployment_artifacts"
if [ -d "$MODEL_DIR/model_chunks" ] && [ ! -f "$MODEL_DIR/plant_disease_model_efficientnet_b0.pth" ]; then
  python - "$MODEL_DIR" <<'PY'
import base64
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
parts = sorted(root.joinpath("model_chunks").glob("*.b64"))
encoded = "".join(part.read_text(encoding="ascii") for part in parts)
root.joinpath("plant_disease_model_efficientnet_b0.pth").write_bytes(base64.b64decode(encoded))
PY
fi
npm --prefix plant_disease_detector_frontend ci
npm --prefix plant_disease_detector_frontend run build
python plant_disease_detector/manage.py collectstatic --noinput

