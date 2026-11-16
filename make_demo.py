"""Create a completely synthetic workshop clip and matching test detections."""

import json
from math import cos, sin
from pathlib import Path

import cv2
import numpy as np


# ============================================
# 1. Demo background and synthetic people
# ============================================
def draw_person(frame, x, bottom_y, color):
    x = int(x)
    bottom_y = int(bottom_y)
    cv2.circle(frame, (x, bottom_y - 72), 11, color, -1)
    cv2.rectangle(frame, (x - 13, bottom_y - 60), (x + 13, bottom_y - 25), color, -1)
    cv2.line(frame, (x - 7, bottom_y - 25), (x - 9, bottom_y), color, 7)
    cv2.line(frame, (x + 7, bottom_y - 25), (x + 9, bottom_y), color, 7)
    cv2.line(frame, (x - 13, bottom_y - 52), (x - 24, bottom_y - 30), color, 5)
    cv2.line(frame, (x + 13, bottom_y - 52), (x + 24, bottom_y - 30), color, 5)
    return [x - 26, bottom_y - 85, x + 26, bottom_y + 2]


def background():
    frame = np.full((360, 640, 3), (40, 48, 57), dtype=np.uint8)
    cv2.rectangle(frame, (15, 82), (260, 350), (57, 64, 74), -1)
    cv2.rectangle(frame, (384, 82), (625, 350), (48, 68, 75), -1)
    cv2.rectangle(frame, (268, 82), (377, 350), (60, 58, 60), -1)
    cv2.rectangle(frame, (36, 118), (235, 143), (95, 110, 123), -1)
    cv2.rectangle(frame, (416, 116), (608, 143), (90, 103, 112), -1)
    for x in range(286, 370, 24):
        cv2.line(frame, (x, 165), (x, 346), (70, 70, 75), 1)
    cv2.putText(frame, 'ASSEMBLY', (75, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (205, 215, 225), 1)
    cv2.putText(frame, 'PACKAGING', (450, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (205, 215, 225), 1)
    return frame


# ============================================
# 2. Save video and fake detections (not YOLO)
# ============================================
def make_demo():
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    video_path = data_dir / 'demo_workshop.mp4'
    boxes_path = data_dir / 'demo_boxes.json'
    fps = 20
    total_frames = 240

    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (640, 360))
    if not writer.isOpened():
        raise RuntimeError('OpenCV could not create the demo video (MP4 encoder unavailable).')

    all_frames = []
    try:
        for frame_number in range(total_frames):
            seconds = frame_number / fps
            frame = background()
            boxes = []

            # Moving and stationary silhouettes; no real workers are filmed.
            examples = [
                (125 + 22 * sin(seconds * 0.9), 286, (230, 185, 115)),
                (203, 320, (120, 170, 220)),
                (438 + 17 * sin(seconds * 1.2), 288, (130, 225, 200)),
                (542, 326, (185, 160, 230)),
            ]
            if seconds >= 6:
                examples.append((320 + 20 * sin(seconds * 1.3), 306, (225, 190, 100)))

            for x, y, color in examples:
                boxes.append(draw_person(frame, x, y, color))
            cv2.putText(frame, 'SYNTHETIC TEST VIDEO - NOT CAMERA FOOTAGE', (14, 348),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
            all_frames.append(boxes)
            writer.write(frame)
    finally:
        writer.release()

    boxes_path.write_text(json.dumps({'frames': all_frames}), encoding='utf-8')
    print(f'Saved demo video: {video_path}')
    print(f'Saved demo boxes: {boxes_path}')


if __name__ == '__main__':
    make_demo()
