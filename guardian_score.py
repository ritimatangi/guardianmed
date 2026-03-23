from datetime import datetime, timedelta
from database import get_dose_logs, get_all_medicines
from risk_engine import RiskEngine


class GuardianScoreEngine:
    """Calculate the Guardian Score (0-100) based on adherence, timing, and risk flags."""

    def calculate_score(self):
        logs = get_dose_logs(days=7)
        risk_engine = RiskEngine()
        risk_flags = risk_engine.run_all_checks()

        adherence = self._adherence_score(logs)
        timing = self._timing_score(logs)
        risk_penalty = self._risk_penalty(risk_flags)

        # Weighted: adherence 40%, timing 30%, risk 30%
        raw = (adherence * 0.4) + (timing * 0.3) + (risk_penalty * 0.3)
        score = max(0, min(100, int(round(raw))))

        # Determine level
        if score >= 80:
            level = "safe"
            color = "#1D9E75"
        elif score >= 50:
            level = "caution"
            color = "#BA7517"
        else:
            level = "at_risk"
            color = "#E24B4A"

        reasons = self._build_reasons(logs, risk_flags)

        return {
            "score": score,
            "level": level,
            "color": color,
            "reasons": reasons[:5],
            "breakdown": {
                "adherence": int(round(adherence)),
                "timing_accuracy": int(round(timing)),
                "risk_flags": int(round(risk_penalty))
            }
        }

    def _adherence_score(self, logs):
        """Score based on taken vs missed/late doses (0-100 scale)."""
        relevant = [l for l in logs if l['status'] != 'upcoming']
        if not relevant:
            return 100

        taken = sum(1 for l in relevant if l['status'] == 'taken')
        late = sum(1 for l in relevant if l['status'] == 'late')
        total = len(relevant)

        # Late counts as 50% credit
        return ((taken + late * 0.5) / total) * 100

    def _timing_score(self, logs):
        """Score based on how close to scheduled time doses were taken."""
        timed = [l for l in logs if l['status'] in ('taken', 'late') and l['taken_at']]
        if not timed:
            return 100

        total_penalty = 0
        for log in timed:
            try:
                scheduled = datetime.strptime(f"{log['date']} {log['scheduled_time']}:00", "%Y-%m-%d %H:%M:%S")
                taken = datetime.strptime(log['taken_at'], "%Y-%m-%d %H:%M:%S")
                diff_minutes = abs((taken - scheduled).total_seconds()) / 60

                # Penalty: 0 for on-time, up to 100 for 3+ hours late
                penalty = min(100, (diff_minutes / 180) * 100)
                total_penalty += penalty
            except (ValueError, TypeError):
                continue

        avg_penalty = total_penalty / len(timed) if timed else 0
        return max(0, 100 - avg_penalty)

    def _risk_penalty(self, risk_flags):
        """Convert risk flags into a score (100 = no risks, 0 = many high risks)."""
        if not risk_flags:
            return 100

        penalty = 0
        for flag in risk_flags:
            if flag.get('flag'):
                sev = flag.get('severity', 'low')
                if sev == 'high':
                    penalty += 25
                elif sev == 'medium':
                    penalty += 15
                else:
                    penalty += 5

        return max(0, 100 - penalty)

    def _build_reasons(self, logs, risk_flags):
        """Build human-readable reason strings."""
        reasons = []

        # Count missed per medicine in last 7 days
        missed_counts = {}
        for log in logs:
            if log['status'] == 'missed':
                name = log.get('medicine_name', 'Unknown')
                missed_counts[name] = missed_counts.get(name, 0) + 1

        for name, count in sorted(missed_counts.items(), key=lambda x: -x[1]):
            reasons.append(f"Missed {name} {count}x this week")

        # Late doses
        late_count = sum(1 for l in logs if l['status'] == 'late')
        if late_count > 0:
            reasons.append(f"{late_count} dose(s) taken late this week")

        # Risk flag reasons
        for flag in risk_flags:
            if flag.get('flag'):
                reasons.append(flag['reason'])

        return reasons
