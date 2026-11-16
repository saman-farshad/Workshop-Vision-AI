from core import PersonTracker, get_counts, get_zone, load_zones


ZONES = [
    {'name': 'left', 'points': [[0, 0], [0.5, 0], [0.5, 1], [0, 1]]},
    {'name': 'right', 'points': [[0.5, 0], [1, 0], [1, 1], [0.5, 1]]},
]


def test_zone_occupancy():
    people = [
        {'box': (10, 10, 30, 80), 'state': 'moving'},
        {'box': (70, 10, 90, 80), 'state': 'stationary'},
    ]
    counts = get_counts(people, ZONES, 100, 100, max_people=1)
    assert counts['left'] == 1
    assert counts['right'] == 1
    assert counts['visible_people'] == 2
    assert counts['crowd_alert'] == 1


def test_tracker_moving_and_stationary():
    tracker = PersonTracker()
    for i in range(18):
        t = i / 10
        people = tracker.update([(10 + i * 2, 10, 30 + i * 2, 80), (110, 10, 130, 80)], t, 200, 100)
    assert people[0]['state'] == 'moving'
    assert people[1]['state'] == 'stationary'
    assert len(tracker.tracks) == 2


def test_tracker_no_personal_data_exports():
    tracker = PersonTracker()
    people = tracker.update([(10, 10, 30, 80)], 0, 200, 100)
    assert set(people[0]) == {'box', 'state'}
    assert 'track_id' not in people[0]


def test_zones_from_config():
    zones, max_people = load_zones('config/zones.json')
    assert max_people == 4
    assert get_zone((100, 260), zones, 640, 360) == 'assembly'
    assert get_zone((500, 260), zones, 640, 360) == 'packaging'
