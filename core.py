"""Small, privacy-first helpers for person counting and zone analytics."""

import json
from dataclasses import dataclass, field
from math import hypot
from pathlib import Path

import cv2
import numpy as np


# ============================================
# 1. Workshop zones
# ============================================
def load_zones(file_path):
    path = Path(file_path)
    with path.open('r', encoding='utf-8') as file:
        settings = json.load(file)

    zones = settings.get('zones', [])
    if not zones:
        raise ValueError('The zones configuration must contain at least one zone.')

    names = set()
    for zone in zones:
        name = zone.get('name')
        points = zone.get('points', [])
        if not isinstance(name, str) or not name.isidentifier() or name in names:
            raise ValueError('Zone names must be unique snake_case identifiers.')
        if len(points) < 3:
            raise ValueError(f'Zone {name} needs at least 3 polygon points.')
        if any(len(point) != 2 or any(not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in point)
               for point in points):
            raise ValueError(f'Zone {name} must use normalized [x, y] points between 0 and 1.')
        names.add(name)

    return zones, int(settings.get('max_people', 4))


def zone_points(zone, width, height):
    points = [[round(x * width), round(y * height)] for x, y in zone['points']]
    return np.array(points, dtype=np.int32)


def get_zone(point, zones, width, height):
    for zone in zones:
        polygon = zone_points(zone, width, height)
        if cv2.pointPolygonTest(polygon, (float(point[0]), float(point[1])), False) >= 0:
            return zone['name']
    return 'outside'


def foot_point(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2)


# ============================================
# 2. Anonymous short-term tracking
# ============================================
@dataclass
class PersonTrack:
    box: tuple
    first_seen: float
    last_seen: float
    positions: list = field(default_factory=list)

    def add(self, box, now, window_seconds):
        self.box = tuple(box)
        self.last_seen = now
        self.positions.append((now, *foot_point(box)))
        self.positions = [p for p in self.positions if p[0] >= now - window_seconds]

    def movement_state(self, now, frame_width):
        if now - self.first_seen < 0.8 or len(self.positions) < 2:
            return 'uncertain'
        old = self.positions[0]
        new = self.positions[-1]
        distance = hypot(new[1] - old[1], new[2] - old[2])
        return 'moving' if distance >= max(12.0, frame_width * 0.025) else 'stationary'


class PersonTracker:
    """Session-only proximity tracker; IDs never leave memory or enter reports."""

    def __init__(self, max_missing=0.9, movement_window=1.5):
        self.tracks = {}
        self.next_id = 1
        self.max_missing = max_missing
        self.movement_window = movement_window

    def update(self, boxes, now, width, height):
        for track_id, track in list(self.tracks.items()):
            if now - track.last_seen > self.max_missing:
                del self.tracks[track_id]

        clean_boxes = []
        for box in boxes:
            x1, y1, x2, y2 = [int(v) for v in box]
            if x2 > x1 and y2 > y1:
                clean_boxes.append((x1, y1, x2, y2))

        # Match new detections to old positions by nearest footpoint.
        possible = []
        max_distance = min(width, height) * 0.17
        for index, box in enumerate(clean_boxes):
            point = foot_point(box)
            for track_id, track in self.tracks.items():
                old_point = foot_point(track.box)
                distance = hypot(point[0] - old_point[0], point[1] - old_point[1])
                if distance <= max_distance:
                    possible.append((distance, index, track_id))

        used_boxes = set()
        used_tracks = set()
        matched = {}
        for distance, index, track_id in sorted(possible):
            if index in used_boxes or track_id in used_tracks:
                continue
            used_boxes.add(index)
            used_tracks.add(track_id)
            matched[index] = track_id

        people = []
        for index, box in enumerate(clean_boxes):
            track_id = matched.get(index)
            if track_id is None:
                track_id = self.next_id
                self.next_id += 1
                self.tracks[track_id] = PersonTrack(box=box, first_seen=now, last_seen=now)
            track = self.tracks[track_id]
            track.add(box, now, self.movement_window)
            people.append({'box': box, 'state': track.movement_state(now, width)})

        return people


# ============================================
# 3. Counts and visual display
# ============================================
def get_counts(people, zones, width, height, max_people):
    counts = {
        'visible_people': len(people),
        'moving_people': 0,
        'stationary_people': 0,
        'uncertain_people': 0,
        **{zone['name']: 0 for zone in zones},
        'outside': 0,
    }
    for person in people:
        counts[f"{person['state']}_people"] += 1
        area = get_zone(foot_point(person['box']), zones, width, height)
        counts[area] += 1
    counts['crowd_alert'] = int(len(people) > max_people)
    return counts


def draw_frame(frame, people, zones, counts, max_people):
    height, width = frame.shape[:2]
    canvas = frame.copy()

    colors = [(255, 150, 25), (240, 95, 210), (100, 220, 165), (165, 165, 165)]
    overlay = canvas.copy()
    for i, zone in enumerate(zones):
        polygon = zone_points(zone, width, height)
        cv2.fillPoly(overlay, [polygon], colors[i % len(colors)])
    canvas = cv2.addWeighted(overlay, 0.12, canvas, 0.88, 0)

    for i, zone in enumerate(zones):
        polygon = zone_points(zone, width, height)
        color = colors[i % len(colors)]
        cv2.polylines(canvas, [polygon], True, color, 2)
        x, y = polygon[0]
        cv2.putText(canvas, f"{zone['name']}: {counts[zone['name']]}",
                    (int(x) + 6, max(92, int(y) + 22)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

    for person in people:
        x1, y1, x2, y2 = person['box']
        state = person['state']
        color = (80, 215, 105) if state == 'moving' else (160, 180, 255)
        if state == 'uncertain':
            color = (210, 210, 210)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(canvas, state.upper(), (x1, max(74, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)

    cv2.rectangle(canvas, (0, 0), (width, 66), (18, 27, 48), -1)
    cv2.putText(canvas, f"VISIBLE: {counts['visible_people']}  MOVING: {counts['moving_people']}",
                (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.67, (240, 240, 240), 2)
    cv2.putText(canvas, f"STATIONARY: {counts['stationary_people']}   LIMIT: {max_people}",
                (12, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (210, 215, 230), 1)
    if counts['crowd_alert']:
        cv2.putText(canvas, 'CROWD ALERT', (max(10, width - 185), 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.56, (50, 70, 245), 2)
    return canvas
