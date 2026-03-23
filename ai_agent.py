"""
GuardianMed — Agentic AI Module
Provides proactive AI suggestions based on real patient history and trust-gated actions.
"""

import json
from datetime import datetime
from database import get_dose_logs, get_all_medicines, get_today_schedule
from guardian_score import GuardianScoreEngine
from risk_engine import RiskEngine


# ══════════════════════════════════════════════════════════
# AGENTIC AI SUGGESTIONS ENGINE
# ══════════════════════════════════════════════════════════

class AIAgent:
    """Rule-based agentic AI that generates proactive suggestions."""

    def __init__(self):
        self.score_engine = GuardianScoreEngine()
        self.risk_engine = RiskEngine()

    def generate_suggestions(self):
        """Analyze current state and generate actionable AI suggestions."""
        suggestions = []
        score_data = self.score_engine.calculate_score()
        risk_flags = self.risk_engine.run_all_checks()
        logs = get_dose_logs(days=7)
        schedule = get_today_schedule()

        # ── 1. Missed dose analysis ───────────────────────
        missed_total = sum(1 for l in logs if l['status'] == 'missed')
        if missed_total >= 3:
            suggestions.append({
                "id": "sug_missed_doses",
                "icon": "🚨",
                "severity": "high",
                "title": "Multiple Missed Doses Detected",
                "description": f"Patient missed {missed_total} doses in the last 7 days. Recommend doctor consultation.",
                "action": "Notify caregiver and schedule doctor appointment",
                "action_type": "notify_caregiver",
                "requires_approval": True
            })

        # ── 2. Low adherence alert ────────────────────────
        if score_data['breakdown']['adherence'] < 60:
            suggestions.append({
                "id": "sug_low_adherence",
                "icon": "📉",
                "severity": "high",
                "title": "Low Adherence Alert",
                "description": f"Adherence is at {score_data['breakdown']['adherence']}%. Suggest caregiver intervention.",
                "action": "Send alert to caregiver with adherence report",
                "action_type": "send_alert",
                "requires_approval": True
            })

        # ── 3. Score declining ────────────────────────────
        if score_data['score'] < 50:
            suggestions.append({
                "id": "sug_critical_score",
                "icon": "⚠️",
                "severity": "high",
                "title": "Guardian Score Critical",
                "description": f"Score is {score_data['score']}/100 — at risk level. Immediate attention needed.",
                "action": "Generate health summary report for doctor",
                "action_type": "generate_report",
                "requires_approval": True
            })

        # ── 4. Risk interaction detected ──────────────────
        high_risks = [f for f in risk_flags if f.get('severity') == 'high' and f.get('flag')]
        if high_risks:
            suggestions.append({
                "id": "sug_drug_interaction",
                "icon": "💊",
                "severity": "high",
                "title": "Drug Interaction Warning",
                "description": high_risks[0]['reason'],
                "action": "Alert pharmacist and caregiver about interaction",
                "action_type": "alert_pharmacist",
                "requires_approval": True
            })

        # ── 5. Evening dose pattern ───────────────────────
        evening_missed = sum(1 for l in logs
                           if l['status'] == 'missed'
                           and l.get('scheduled_time', '00:00') >= '18:00')
        if evening_missed >= 2:
            suggestions.append({
                "id": "sug_evening_pattern",
                "icon": "🌙",
                "severity": "medium",
                "title": "Evening Dose Pattern",
                "description": f"Patient consistently misses evening doses ({evening_missed} times this week).",
                "action": "Set extra evening reminder notification",
                "action_type": "set_reminder",
                "requires_approval": False
            })

        # ── 6. Timing improvement suggestion ─────────────
        late_count = sum(1 for l in logs if l['status'] == 'late')
        if late_count >= 3:
            suggestions.append({
                "id": "sug_timing",
                "icon": "⏰",
                "severity": "medium",
                "title": "Timing Improvement Needed",
                "description": f"{late_count} doses taken late this week. Suggest adjusting alarm schedule.",
                "action": "Reschedule reminder times based on patient's routine",
                "action_type": "adjust_schedule",
                "requires_approval": False
            })

        # ── 7. Positive reinforcement ─────────────────────
        if score_data['score'] >= 80:
            suggestions.append({
                "id": "sug_positive",
                "icon": "🌟",
                "severity": "low",
                "title": "Great Adherence!",
                "description": "Patient is maintaining excellent adherence. Keep up the good work!",
                "action": "Send encouragement message to patient",
                "action_type": "send_encouragement",
                "requires_approval": False
            })

        # ── 8. Upcoming dose reminder ─────────────────────
        upcoming = [s for s in schedule if s['status'] == 'upcoming']
        if upcoming:
            nxt = upcoming[0]
            suggestions.append({
                "id": "sug_upcoming",
                "icon": "🔔",
                "severity": "low",
                "title": "Upcoming Dose Reminder",
                "description": f"{nxt['name']} {nxt['dose']} is due at {nxt['scheduled_time']}.",
                "action": "Send push notification to patient",
                "action_type": "push_notification",
                "requires_approval": False
            })

        # Always return at least one suggestion
        if not suggestions:
            suggestions.append({
                "id": "sug_all_good",
                "icon": "✅",
                "severity": "low",
                "title": "All Systems Normal",
                "description": "No actionable items detected. Patient is on track.",
                "action": "Continue monitoring",
                "action_type": "none",
                "requires_approval": False
            })

        return suggestions

    def approve_action(self, suggestion_id):
        """Simulate approving an AI-suggested action."""
        action_results = {
            "sug_missed_doses": "✅ Caregiver notified. Doctor appointment scheduling initiated.",
            "sug_low_adherence": "✅ Alert sent to caregiver with weekly adherence report.",
            "sug_critical_score": "✅ Health summary report generated and shared with Dr. Sharma.",
            "sug_drug_interaction": "✅ Pharmacist alerted. Caregiver notified about interaction risk.",
            "sug_evening_pattern": "✅ Extra evening reminder set for 5:30 PM daily.",
            "sug_timing": "✅ Reminder schedule adjusted based on patient's routine.",
            "sug_positive": "✅ Encouragement message sent to patient.",
            "sug_upcoming": "✅ Push notification sent to patient.",
            "sug_all_good": "✅ Monitoring continues."
        }
        return action_results.get(suggestion_id, "✅ Action approved and executed.")


# ══════════════════════════════════════════════════════════
# NOTIFICATION SIMULATION
# ══════════════════════════════════════════════════════════

def generate_notifications():
    """Generate simulated push notifications based on current state."""
    notifications = []
    schedule = get_today_schedule()
    score_data = GuardianScoreEngine().calculate_score()

    # Upcoming dose notifications
    upcoming = [s for s in schedule if s['status'] == 'upcoming']
    if upcoming:
        nxt = upcoming[0]
        notifications.append({
            "type": "reminder",
            "icon": "💊",
            "title": "Medicine Time Reminder",
            "message": f"Time to take {nxt['name']} ({nxt['dose']}) — scheduled at {nxt['scheduled_time']}",
            "time": datetime.now().strftime("%H:%M")
        })

    # Missed dose alerts
    missed_today = [s for s in schedule if s['status'] == 'missed']
    if missed_today:
        notifications.append({
            "type": "alert",
            "icon": "⚠️",
            "title": "Missed Dose Alert",
            "message": f"You missed {len(missed_today)} dose(s) today. Please take action.",
            "time": datetime.now().strftime("%H:%M")
        })

    # Score alert
    if score_data['score'] < 60:
        notifications.append({
            "type": "warning",
            "icon": "🚨",
            "title": "Guardian Score Low",
            "message": f"Your Guardian Score dropped to {score_data['score']}. Take your medicines on time.",
            "time": datetime.now().strftime("%H:%M")
        })

    return notifications
