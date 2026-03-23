import json
from datetime import datetime, timedelta
from database import get_db, get_dose_logs, get_all_medicines

DATA_DIR = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'data')


class RiskEngine:
    """Rule-based risk detection engine for medication safety."""

    def __init__(self):
        self.interactions = self._load_interactions()

    def _load_interactions(self):
        path = __import__('os').path.join(DATA_DIR, 'drug_interactions.json')
        try:
            with open(path, 'r') as f:
                return json.load(f).get('interactions', [])
        except FileNotFoundError:
            return []

    def run_all_checks(self):
        """Run all risk checks and return list of flags."""
        flags = []
        flags.extend(self.missed_streak_check())
        flags.extend(self.timing_conflict_check())
        flags.extend(self.drug_class_interaction_check())
        flags.extend(self.late_dose_check())
        return flags

    def missed_streak_check(self):
        """Flag if 2+ doses missed in the last 24 hours."""
        flags = []
        logs = get_dose_logs(days=2)
        now = datetime.now()
        cutoff = now - timedelta(hours=24)

        missed_recent = []
        for log in logs:
            log_date = datetime.fromisoformat(log['date'])
            if log_date.date() >= cutoff.date() and log['status'] == 'missed':
                missed_recent.append(log)

        if len(missed_recent) >= 2:
            med_names = list(set(l.get('medicine_name', 'Unknown') for l in missed_recent))
            flags.append({
                "flag": True,
                "reason": f"Missed {len(missed_recent)} doses in the last 24 hours ({', '.join(med_names[:3])})",
                "severity": "high"
            })
        return flags

    def timing_conflict_check(self):
        """Flag if two medicines are scheduled within 30 minutes of each other."""
        flags = []
        medicines = get_all_medicines()

        time_slots = []
        for med in medicines:
            times = json.loads(med['times']) if isinstance(med['times'], str) else med['times']
            for t in times:
                try:
                    parsed = datetime.strptime(t, "%H:%M")
                    time_slots.append((med['name'], parsed, t))
                except ValueError:
                    continue

        time_slots.sort(key=lambda x: x[1])
        seen_conflicts = set()

        for i in range(len(time_slots)):
            for j in range(i + 1, len(time_slots)):
                name_a, time_a, raw_a = time_slots[i]
                name_b, time_b, raw_b = time_slots[j]
                if name_a == name_b:
                    continue
                diff_minutes = abs((time_b - time_a).total_seconds()) / 60
                if diff_minutes <= 30:
                    key = tuple(sorted([name_a, name_b]))
                    if key not in seen_conflicts:
                        seen_conflicts.add(key)
                        flags.append({
                            "flag": True,
                            "reason": f"{name_a} ({raw_a}) and {name_b} ({raw_b}) are within 30 minutes",
                            "severity": "medium"
                        })
        return flags

    def drug_class_interaction_check(self):
        """Compare active medicines against known drug interactions."""
        flags = []
        medicines = get_all_medicines()
        med_names = [m['name'].lower() for m in medicines]
        seen = set()

        for interaction in self.interactions:
            a = interaction['drug_a'].lower()
            b = interaction['drug_b'].lower()
            if a in med_names and b in med_names:
                key = tuple(sorted([a, b]))
                if key not in seen:
                    seen.add(key)
                    flags.append({
                        "flag": True,
                        "reason": f"Interaction: {interaction['drug_a']} + {interaction['drug_b']} — {interaction['note']}",
                        "severity": interaction['severity']
                    })
        return flags

    def late_dose_check(self):
        """Flag doses taken 2+ hours late."""
        flags = []
        logs = get_dose_logs(days=2)

        late_count = 0
        for log in logs:
            if log['status'] == 'late' and log['taken_at']:
                try:
                    scheduled = datetime.strptime(f"{log['date']} {log['scheduled_time']}:00", "%Y-%m-%d %H:%M:%S")
                    taken = datetime.strptime(log['taken_at'], "%Y-%m-%d %H:%M:%S")
                    diff_hours = (taken - scheduled).total_seconds() / 3600
                    if diff_hours >= 2:
                        late_count += 1
                except (ValueError, TypeError):
                    continue

        if late_count > 0:
            flags.append({
                "flag": True,
                "reason": f"{late_count} dose(s) taken 2+ hours late in the last 48 hours",
                "severity": "medium" if late_count < 3 else "high"
            })
        return flags
