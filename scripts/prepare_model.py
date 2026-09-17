"""Validate the explicitly selected artifact before tests and deployment."""
import base64
import hashlib
import json
from pathlib import Path


def prepare(root):
    selection = json.loads((root / 'selected_model.json').read_text(encoding='utf-8'))
    filename = selection['filename']
    if Path(filename).name != filename:
        raise ValueError('Model filename must be a basename')
    artifact = root / filename
    if not artifact.exists():
        chunk_dir = selection.get('chunks', 'model_chunks')
        if Path(chunk_dir).name != chunk_dir:
            raise ValueError('Model chunk directory must be a basename')
        parts = sorted((root / chunk_dir).glob('part-*.b64'))
        if not parts:
            raise ValueError('Selected model artifact is missing')
        payload = base64.b64decode(''.join(p.read_text(encoding='ascii').strip() for p in parts), validate=True)
        if hashlib.sha256(payload).hexdigest() != selection['sha256']:
            raise ValueError('Model chunks do not match the selected checkpoint')
        temporary = artifact.with_suffix('.pending')
        temporary.write_bytes(payload)
        temporary.replace(artifact)
    with artifact.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    if digest != selection['sha256']:
        raise ValueError('Selected model checksum mismatch')
    print(f"Verified selected model: {selection['model_version']}")


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[1] / 'plant_disease_detector' / 'deployment_artifacts')

