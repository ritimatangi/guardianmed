from datetime import datetime, timedelta
from database import get_dose_logs


class PatternDetector:
    """Analyze 7-day dose history to detect adherence patterns."""

    def analyze(self):
        logs = get_dose_logs(days=7)
        today = datetime.now().date()

        weekly_adherence = self._weekly_adherence(logs, today)
        insights = self._generate_insights(logs, today)
        streak = self._adherence_streak(logs, today)
        trend = self._detect_trend(weekly_adherence)

        return {
            "weekly_adherence": weekly_adherence,
            "insights": insights,
            "streak": streak,
            "trend": trend
        }

    def _weekly_adherence(self, logs, today):
        """Calculate daily adherence % for the last 7 days (oldest first)."""
        daily = []
        for offset in range(-6, 1):
            day = today + timedelta(days=offset)
            day_str = day.isoformat()
            day_logs = [l for l in logs if l['date'] == day_str and l['status'] != 'upcoming']
            if not day_logs:
                daily.append(0)
                continue
            taken = sum(1 for l in day_logs if l['status'] in ('taken', 'late'))
            pct = int(round((taken / len(day_logs)) * 100))
            daily.append(pct)
        return daily

    def _generate_insights(self, logs, today):
        """Detect specific patterns in the dose log."""
        insights = []

        # 1. Most missed time of day
        missed_by_period = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
        for log in logs:
            if log['status'] == 'missed':
                try:
                    hour = int(log['scheduled_time'].split(":")[0])
                    if hour < 12:
                        missed_by_period["morning"] += 1
                    elif hour < 17:
                        missed_by_period["afternoon"] += 1
                    elif hour < 21:
                        missed_by_period["evening"] += 1
                    else:
                        missed_by_period["night"] += 1
                except (ValueError, AttributeError):
                    continue

        worst_period = max(missed_by_period, key=missed_by_period.get)
        if missed_by_period[worst_period] > 0:
            insights.append(f"Consistently misses {worst_period} doses")

        # 2. Weekend vs weekday
        weekday_logs = [l for l in logs if l['status'] != 'upcoming' and self._is_weekday(l['date'])]
        weekend_logs = [l for l in logs if l['status'] != 'upcoming' and not self._is_weekday(l['date'])]

        wd_rate = self._rate(weekday_logs)
        we_rate = self._rate(weekend_logs)

        if wd_rate > 0 and we_rate > 0:
            diff = wd_rate - we_rate
            if diff > 20:
                insights.append(f"Weekend adherence drops {int(diff)}%")
            elif diff < -20:
                insights.append(f"Weekday adherence drops {int(abs(diff))}%")

        # 3. Specific medicine patterns
        missed_by_med = {}
        total_by_med = {}
        for log in logs:
            if log['status'] == 'upcoming':
                continue
            name = log.get('medicine_name', 'Unknown')
            total_by_med[name] = total_by_med.get(name, 0) + 1
            if log['status'] == 'missed':
                missed_by_med[name] = missed_by_med.get(name, 0) + 1

        for name, missed in missed_by_med.items():
            total = total_by_med.get(name, 1)
            miss_rate = (missed / total) * 100
            if miss_rate > 40:
                insights.append(f"{name} frequently missed ({int(miss_rate)}% miss rate)")

        return insights if insights else ["Adherence patterns look stable"]

    def _adherence_streak(self, logs, today):
        """Count consecutive days of full adherence ending at today."""
        streak = 0
        for offset in range(0, -7, -1):
            day = today + timedelta(days=offset)
            day_str = day.isoformat()
            day_logs = [l for l in logs if l['date'] == day_str and l['status'] != 'upcoming']
            if not day_logs:
                break
            all_taken = all(l['status'] in ('taken', 'late') for l in day_logs)
            if all_taken:
                streak += 1
            else:
                break
        return streak

    def _detect_trend(self, weekly_adherence):
        """Simple trend: compare first half vs second half."""
        if len(weekly_adherence) < 4:
            return "stable"
        first_half = sum(weekly_adherence[:3]) / 3
        second_half = sum(weekly_adherence[4:]) / max(len(weekly_adherence[4:]), 1)

        diff = second_half - first_half
        if diff > 10:
            return "improving"
        elif diff < -10:
            return "declining"
        return "stable"

    def _is_weekday(self, date_str):
        try:
            return datetime.fromisoformat(date_str).weekday() < 5
        except (ValueError, TypeError):
            return True

    def _rate(self, logs):
        if not logs:
            return 0
        taken = sum(1 for l in logs if l['status'] in ('taken', 'late'))
        return (taken / len(logs)) * 100
