#!/usr/bin/env python3
"""Update VoiceTest Lambda code from local asset folders.

This avoids requiring the CDK CLI just to push Lambda code changes.

Usage:
  python3 scripts/update_voice_tester_lambdas.py --region us-east-1

It zips these folders and updates the corresponding functions:
  - voice_tester/lambda/call_handler    -> VoiceTest-CallHandler
  - voice_tester/lambda/test_runner     -> VoiceTest-TestRunner
  - voice_tester/lambda/audio_processor -> VoiceTest-AudioProcessor
"""

from __future__ import annotations

import argparse
import io
import os
import time
import zipfile
from pathlib import Path

import boto3


def zip_dir(src_dir: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src_dir.rglob('*')):
            if p.is_dir():
                continue
            if p.name.startswith('.'):
                continue
            rel = p.relative_to(src_dir)
            z.write(p, rel.as_posix())
    return buf.getvalue()


def wait_lambda_updated(client, function_name: str, timeout_s: int = 120) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        cfg = client.get_function_configuration(FunctionName=function_name)
        status = cfg.get('LastUpdateStatus')
        if status == 'Successful':
            return
        if status == 'Failed':
            raise RuntimeError(cfg.get('LastUpdateStatusReason', 'Lambda update failed'))
        time.sleep(2)
    raise TimeoutError(f'Timeout waiting for {function_name} update')


def main() -> int:
    ap = argparse.ArgumentParser(description='Update VoiceTest Lambdas from local folders')
    ap.add_argument('--region', default=os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'us-east-1')
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    lambda_client = boto3.client('lambda', region_name=args.region)

    updates = [
        ('VoiceTest-CallHandler', root / 'voice_tester' / 'lambda' / 'call_handler'),
        ('VoiceTest-TestRunner', root / 'voice_tester' / 'lambda' / 'test_runner'),
        ('VoiceTest-AudioProcessor', root / 'voice_tester' / 'lambda' / 'audio_processor'),
    ]

    for fn, folder in updates:
        if not folder.exists():
            raise FileNotFoundError(folder)
        print(f'Updating {fn} from {folder}...')
        zip_bytes = zip_dir(folder)
        lambda_client.update_function_code(FunctionName=fn, ZipFile=zip_bytes)
        wait_lambda_updated(lambda_client, fn)
        print(f'  {fn}: updated')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
