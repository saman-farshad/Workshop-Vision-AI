"""Integration smoke test using synthetic images, never real camera footage."""

import csv
import subprocess
import sys
from pathlib import Path


def test_synthetic_video_pipeline(tmp_path):
    # Real-time model weights are not needed for this deterministic demo.
    result = subprocess.run(
        [sys.executable, 'monitor.py', '--detector', 'demo', '--no-window',
         '--max-frames', '55', '--report', str(tmp_path / 'demo_counts.csv')],
        capture_output=True, text=True, check=True,
    )
    assert 'Processed frames: 55' in result.stdout
    with (tmp_path / 'demo_counts.csv').open(newline='', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) >= 2
    assert all(row['visible_people'] == '4' for row in rows)
    assert 'track_id' not in rows[0]
    assert 'image' not in rows[0]
