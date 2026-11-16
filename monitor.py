"""Workshop Vision AI: anonymous counts from a camera, video or synthetic demo."""

import argparse
import csv
import json
import os
import time
from pathlib import Path

import cv2

from core import PersonTracker, draw_frame, get_counts, load_zones


# ============================================
# 1. Detection sources
# ============================================
def load_demo_boxes(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError('Demo boxes not found. Run: python make_demo.py')
    with path.open('r', encoding='utf-8') as file:
        data = json.load(file)
    return data['frames']


def get_yolo_model(model_name):
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError('Ultralytics is not installed. Run: pip install -r requirements.txt') from error
    try:
        return YOLO(model_name)
    except Exception as error:
        raise RuntimeError(f'YOLO model could not load: {error}. First run needs internet.') from error


def detect_people(frame, model, confidence):
    results = model.predict(frame, classes=[0], conf=confidence, verbose=False)
    if not results or results[0].boxes is None:
        return []
    return results[0].boxes.xyxy.cpu().numpy().astype(int).tolist()


def get_video_source(source):
    # '0' = first camera; '1' = second camera. Other strings are video paths/streams.
    return int(source) if source.isdigit() else source


# ============================================
# 2. Run monitoring and collect aggregate data
# ============================================
def run(args):
    zones, max_people = load_zones(args.zones)

    if args.detector == 'demo':
        if Path(args.source).name != 'demo_workshop.mp4':
            raise ValueError('Demo detector works only with data/demo_workshop.mp4.')
        demo_boxes = load_demo_boxes('data/demo_boxes.json')
        model = None
    else:
        demo_boxes = None
        model = get_yolo_model(args.model)

    video_source = get_video_source(args.source)
    cap = (cv2.VideoCapture(video_source, cv2.CAP_DSHOW)
           if isinstance(video_source, int) and os.name == 'nt'
           else cv2.VideoCapture(video_source))
    if not cap.isOpened():
        raise RuntimeError(f'Could not open video source: {args.source}')

    camera = isinstance(video_source, int) or str(video_source).lower().startswith(('rtsp://', 'http://', 'https://'))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or fps > 240:
        fps = 20.0

    tracker = PersonTracker()
    rows = []
    frame_number = 0
    start_time = time.monotonic()
    next_sample = 0.0
    last_counts = None
    first_preview_done = False
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path = Path('assets/demo_preview.png')

    print(f'Source: {args.source} | detector: {args.detector} | press Q to quit')
    print('No camera frames, faces, or track IDs are saved.')

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            if args.max_frames and frame_number >= args.max_frames:
                break

            height, width = frame.shape[:2]
            seconds = time.monotonic() - start_time if camera else frame_number / fps

            if demo_boxes is not None:
                if frame_number >= len(demo_boxes):
                    break
                boxes = demo_boxes[frame_number]
            else:
                boxes = detect_people(frame, model, args.confidence)

            people = tracker.update(boxes, seconds, width, height)
            counts = get_counts(people, zones, width, height, max_people)
            last_counts = counts

            if seconds >= next_sample:
                rows.append({'time_seconds': round(seconds, 2), **counts})
                next_sample = seconds + args.sample_seconds

            if not args.no_window or (args.demo_preview and demo_boxes is not None and not first_preview_done and frame_number >= 120):
                display = draw_frame(frame, people, zones, counts, max_people)
                if args.demo_preview and demo_boxes is not None and not first_preview_done and frame_number >= 120:
                    preview_path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(preview_path), display)
                    first_preview_done = True
                if not args.no_window:
                    try:
                        cv2.imshow('Workshop Vision AI - press Q', display)
                        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
                            break
                    except cv2.error as error:
                        raise RuntimeError('Unable to open the display window. Try --no-window.') from error

            frame_number += 1
    finally:
        cap.release()
        if not args.no_window:
            cv2.destroyAllWindows()

    headers = ['time_seconds', 'visible_people', 'moving_people', 'stationary_people',
               'uncertain_people', *[zone['name'] for zone in zones], 'outside', 'crowd_alert']
    with report_path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f'Processed frames: {frame_number}')
    print(f'Saved aggregate CSV: {report_path}')
    if last_counts:
        print(f'Last visible count: {last_counts["visible_people"]}')
    if first_preview_done:
        print(f'Saved synthetic preview: {preview_path}')


def parse_args():
    parser = argparse.ArgumentParser(description='Anonymous workshop people/zone monitor.')
    parser.add_argument('--source', default='data/demo_workshop.mp4', help='Video path, 0 for webcam, or stream URL')
    parser.add_argument('--detector', choices=['demo', 'yolo'], default='demo')
    parser.add_argument('--zones', default='config/zones.json')
    parser.add_argument('--model', default='yolo11n.pt')
    parser.add_argument('--confidence', type=float, default=0.4)
    parser.add_argument('--sample-seconds', type=float, default=1.0)
    parser.add_argument('--report', default='data/reports/latest_report.csv')
    parser.add_argument('--no-window', action='store_true', help='Process without video display')
    parser.add_argument('--demo-preview', action='store_true', help='Save preview of synthetic demo only')
    parser.add_argument('--max-frames', type=int, default=0)
    args = parser.parse_args()
    if args.sample_seconds <= 0:
        parser.error('--sample-seconds must be positive')
    if not 0 < args.confidence <= 1:
        parser.error('--confidence must be between 0 and 1')
    if args.demo_preview and args.detector != 'demo':
        parser.error('--demo-preview is supported only for synthetic demo')
    return args


if __name__ == '__main__':
    try:
        run(parse_args())
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as error:
        raise SystemExit(f'ERROR: {error}') from error
