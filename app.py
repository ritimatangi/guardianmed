from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
import json

from database import init_db, db_is_empty, seed_demo_data, seed_today_schedule
from database import (get_all_medicines, get_medicine, add_medicine,
                      update_medicine, delete_medicine, get_today_schedule,
                      log_dose, get_dose_logs, add_guardian_event, get_recent_events,
                      auto_miss_overdue)
from guardian_score import GuardianScoreEngine
from risk_engine import RiskEngine
from pattern_detector import PatternDetector
from ai_agent import AIAgent, generate_notifications
from ml_model import predict_miss_probability, get_feature_importance

app = Flask(__name__)

# ── Initialise DB on startup ──────────────────────────────
init_db()
if db_is_empty():
    seed_demo_data()
    print("✓ Demo data loaded")

# Ensure today's schedule exists
seed_today_schedule()
print("✓ Today's schedule initialized")


# ══════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('caregiver'))


@app.route('/elderly')
def elderly():
    return render_template('elderly.html')


@app.route('/caregiver')
def caregiver():
    return render_template('caregiver.html')


@app.route('/sos')
def sos():
    return render_template('sos.html')


@app.route('/add-medicine')
def add_medicine_page():
    med_id = request.args.get('id')
    med = None
    if med_id:
        med = get_medicine(int(med_id))
    return render_template('add_medicine.html', medicine=med)


# ══════════════════════════════════════════════════════════
# API ROUTES — MEDICINES
# ══════════════════════════════════════════════════════════

@app.route('/api/medicines', methods=['GET'])
def api_get_medicines():
    meds = get_all_medicines()
    return jsonify(meds)


@app.route('/api/medicines', methods=['POST'])
def api_add_medicine():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('dose'):
        return jsonify({"error": "name and dose are required"}), 400
    med_id = add_medicine(data)
    return jsonify({"id": med_id, "message": "Medicine added"}), 201


@app.route('/api/medicines/<int:med_id>', methods=['PUT'])
def api_update_medicine(med_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    update_medicine(med_id, data)
    return jsonify({"message": "Medicine updated"})


@app.route('/api/medicines/<int:med_id>', methods=['DELETE'])
def api_delete_medicine(med_id):
    delete_medicine(med_id)
    return jsonify({"message": "Medicine deactivated"})


# ══════════════════════════════════════════════════════════
# API ROUTES — SCHEDULE & DOSE LOGGING
# ══════════════════════════════════════════════════════════

@app.route('/api/schedule/today', methods=['GET'])
def api_today_schedule():
    auto_miss_overdue()  # Mark overdue doses as missed
    schedule = get_today_schedule()
    return jsonify(schedule)


@app.route('/api/dose/log', methods=['POST'])
def api_log_dose():
    data = request.get_json()
    log_id = data.get('log_id')
    if not log_id:
        return jsonify({"error": "log_id is required"}), 400

    # Record previous score
    engine = GuardianScoreEngine()
    old_score = engine.calculate_score()['score']

    log_dose(log_id, 'taken')

    # Calculate new score and record event
    new_result = engine.calculate_score()
    add_guardian_event('dose_taken', f'Dose logged as taken',
                       old_score, new_result['score'],
                       new_result['reasons'][:3])

    return jsonify({"message": "Dose logged", "guardian_score": new_result})


@app.route('/api/dose/miss', methods=['POST'])
def api_miss_dose():
    data = request.get_json()
    log_id = data.get('log_id')
    if not log_id:
        return jsonify({"error": "log_id is required"}), 400

    engine = GuardianScoreEngine()
    old_score = engine.calculate_score()['score']

    log_dose(log_id, 'missed')

    new_result = engine.calculate_score()
    add_guardian_event('dose_missed', f'Dose logged as missed',
                       old_score, new_result['score'],
                       new_result['reasons'][:3])

    return jsonify({"message": "Dose marked as missed", "guardian_score": new_result})


# ══════════════════════════════════════════════════════════
# API ROUTES — ANALYTICS
# ══════════════════════════════════════════════════════════

@app.route('/api/guardian-score', methods=['GET'])
def api_guardian_score():
    engine = GuardianScoreEngine()
    result = engine.calculate_score()
    return jsonify(result)


@app.route('/api/behaviour/patterns', methods=['GET'])
def api_patterns():
    detector = PatternDetector()
    result = detector.analyze()
    return jsonify(result)


@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    risk_engine = RiskEngine()
    flags = risk_engine.run_all_checks()
    active_flags = [f for f in flags if f.get('flag')]
    return jsonify(active_flags)


# ══════════════════════════════════════════════════════════
# API ROUTES — PATIENT INFO
# ══════════════════════════════════════════════════════════

PATIENT = {
    "name": "Rajesh Kumar",
    "age": 72,
    "gender": "Male",
    "blood_group": "B+",
    "conditions": ["Diabetes", "Hypertension", "High Cholesterol"]
}

@app.route('/api/patient', methods=['GET'])
def api_get_patient():
    return jsonify(PATIENT)


# ══════════════════════════════════════════════════════════
# API ROUTES — AI AGENT SUGGESTIONS
# ══════════════════════════════════════════════════════════

@app.route('/api/ai/suggestions', methods=['GET'])
def api_ai_suggestions():
    agent = AIAgent()
    suggestions = agent.generate_suggestions()
    return jsonify(suggestions)


@app.route('/api/ai/approve', methods=['POST'])
def api_ai_approve():
    data = request.get_json()
    suggestion_id = data.get('suggestion_id')
    if not suggestion_id:
        return jsonify({"error": "suggestion_id required"}), 400
    agent = AIAgent()
    result = agent.approve_action(suggestion_id)
    return jsonify({"message": result})


# ══════════════════════════════════════════════════════════
# API ROUTES — NOTIFICATIONS
# ══════════════════════════════════════════════════════════

@app.route('/api/notifications', methods=['GET'])
def api_notifications():
    return jsonify(generate_notifications())


# ══════════════════════════════════════════════════════════
# API ROUTES — ML PREDICTION
# ══════════════════════════════════════════════════════════

@app.route('/api/ml/predict', methods=['GET'])
def api_ml_predict():
    """Predict probability of missing next dose using ML model."""
    logs = get_dose_logs(days=3)
    schedule = get_today_schedule()

    # Extract features from live data
    missed_3d = sum(1 for l in logs if l['status'] == 'missed')
    late_logs = [l for l in logs if l['status'] == 'late' and l.get('taken_at') and l.get('scheduled_time')]
    if late_logs:
        delays = []
        for l in late_logs:
            try:
                sh, sm = l['scheduled_time'].split(':')
                taken_parts = l['taken_at'].split(' ')[1].split(':')
                delay = (int(taken_parts[0]) - int(sh)) * 60 + (int(taken_parts[1]) - int(sm))
                delays.append(max(0, delay))
            except (ValueError, IndexError):
                pass
        avg_delay = sum(delays) / len(delays) if delays else 0
    else:
        avg_delay = 0

    total = len(logs) if logs else 1
    taken_count = sum(1 for l in logs if l['status'] in ('taken', 'late'))
    adherence = round((taken_count / total) * 100, 1)

    result = predict_miss_probability(min(missed_3d, 3), avg_delay, adherence)
    result['feature_importance'] = get_feature_importance()
    return jsonify(result)


# ══════════════════════════════════════════════════════════
# API ROUTES — PATIENT HISTORY
# ══════════════════════════════════════════════════════════

@app.route('/api/patient/history', methods=['GET'])
def api_patient_history():
    """Return recent dose actions for the patient history feed."""
    auto_miss_overdue()
    schedule = get_today_schedule()
    history = []
    status_icons = {'taken': '✅', 'missed': '❌', 'late': '⏰', 'upcoming': '🔵'}
    for entry in schedule:
        item = {
            'time': entry['scheduled_time'],
            'medicine': entry['name'],
            'dose': entry['dose'],
            'status': entry['status'],
            'icon': status_icons.get(entry['status'], '⚪'),
        }
        if entry['status'] == 'taken' and entry.get('taken_at'):
            item['detail'] = f"Taken at {entry['taken_at'].split(' ')[-1][:5]}"
        elif entry['status'] == 'missed':
            item['detail'] = 'Missed — no action taken'
        elif entry['status'] == 'late' and entry.get('taken_at'):
            item['detail'] = f"Taken late at {entry['taken_at'].split(' ')[-1][:5]}"
        elif entry['status'] == 'upcoming':
            item['detail'] = f"Scheduled at {entry['scheduled_time']}"
        else:
            item['detail'] = ''
        history.append(item)
    return jsonify(history)


# ══════════════════════════════════════════════════════════
# API ROUTES — AI CHAT
# ══════════════════════════════════════════════════════════

@app.route('/api/ai/chat', methods=['POST'])
def api_ai_chat():
    data = request.get_json()
    message = data.get('message', '').strip().lower()

    if not message:
        return jsonify({"reply": "Please ask me something about your medicines.",
                        "reasoning": ["No message received"]})

    # Rule-based AI responses
    reasoning = []
    reply = ""

    # Score query
    if any(kw in message for kw in ['score', 'guardian', 'how am i', 'how are things']):
        engine = GuardianScoreEngine()
        result = engine.calculate_score()
        reasoning.append(f"Fetched Guardian Score: {result['score']}")
        reasoning.append(f"Level: {result['level']}")

        if result['score'] >= 80:
            reply = f"Your Guardian Score is {result['score']} — you're doing great! Keep taking your medicines on time."
        elif result['score'] >= 50:
            reply = f"Your Guardian Score is {result['score']} — not bad, but there's room for improvement. {result['reasons'][0] if result['reasons'] else ''}"
        else:
            reply = f"Your Guardian Score is {result['score']} — this needs attention. {result['reasons'][0] if result['reasons'] else ''}"

    # Next medicine query
    elif any(kw in message for kw in ['next', 'upcoming', 'what should i take']):
        schedule = get_today_schedule()
        upcoming = [s for s in schedule if s['status'] == 'upcoming']
        reasoning.append(f"Found {len(upcoming)} upcoming doses today")

        if upcoming:
            nxt = upcoming[0]
            reply = f"Your next medicine is {nxt['name']} ({nxt['dose']}) at {nxt['scheduled_time']}."
            reasoning.append(f"Next: {nxt['name']} at {nxt['scheduled_time']}")
        else:
            reply = "You have no more upcoming medicines today. Great job!"

    # "Did I take" query
    elif 'did i take' in message or 'have i taken' in message:
        schedule = get_today_schedule()
        # Try to extract medicine name
        med_names = [s['name'].lower() for s in schedule]
        found_med = None
        for name in med_names:
            if name in message:
                found_med = name
                break

        if found_med:
            med_logs = [s for s in schedule if s['name'].lower() == found_med]
            taken = [s for s in med_logs if s['status'] == 'taken']
            reasoning.append(f"Checked dose log for {found_med}")
            if taken:
                reply = f"Yes, you took {found_med.title()} today at {taken[0].get('taken_at', 'an earlier time')}."
            else:
                pending = [s for s in med_logs if s['status'] in ('upcoming', 'missed')]
                if pending:
                    reply = f"No, you haven't taken {found_med.title()} yet. It's scheduled for {pending[0]['scheduled_time']}."
                else:
                    reply = f"I don't see {found_med.title()} in today's schedule."
        else:
            reasoning.append("Could not identify specific medicine name")
            reply = "Which medicine are you asking about? Try saying the medicine name."

    # Mark as taken
    elif 'mark' in message and 'taken' in message:
        schedule = get_today_schedule()
        med_names = [s['name'].lower() for s in schedule]
        found_med = None
        for name in med_names:
            if name in message:
                found_med = name
                break

        if found_med:
            upcoming_logs = [s for s in schedule
                           if s['name'].lower() == found_med and s['status'] == 'upcoming']
            if upcoming_logs:
                log_dose(upcoming_logs[0]['log_id'], 'taken')
                reply = f"Done! I've marked {found_med.title()} as taken."
                reasoning.append(f"Marked {found_med} log_id={upcoming_logs[0]['log_id']} as taken")
            else:
                reply = f"{found_med.title()} has already been taken or isn't scheduled now."
                reasoning.append(f"No upcoming logs for {found_med}")
        else:
            reply = "Which medicine should I mark as taken? Please say the name."
            reasoning.append("Medicine name not found in message")

    # Feeling sick
    elif any(kw in message for kw in ['sick', 'unwell', 'not feeling', 'feel bad', 'pain']):
        risk_engine = RiskEngine()
        flags = risk_engine.run_all_checks()
        high_flags = [f for f in flags if f.get('severity') == 'high' and f.get('flag')]
        reasoning.append(f"Checked risk flags — {len(high_flags)} high severity")

        reply = "I'm sorry you're not feeling well. "
        if high_flags:
            reply += f"I notice some medication concerns: {high_flags[0]['reason']}. "
        reply += "Please contact your caregiver or doctor. You can also use the Emergency (SOS) button."

    # Medicines list
    elif any(kw in message for kw in ['medicines', 'medication', 'what am i taking', 'my meds']):
        meds = get_all_medicines()
        reasoning.append(f"Retrieved {len(meds)} active medicines")
        med_list = ", ".join(f"{m['name']} {m['dose']}" for m in meds)
        reply = f"You're currently taking: {med_list}."

    # General help
    else:
        reply = ("I can help you with:\n"
                 "• Check your Guardian Score\n"
                 "• Find your next medicine\n"
                 "• Check if you took a medicine\n"
                 "• Mark a medicine as taken\n"
                 "• List your medicines\n"
                 "Try asking: 'What is my guardian score?' or 'What is my next medicine?'")
        reasoning.append("No specific intent matched — showing help")

    return jsonify({"reply": reply, "reasoning": reasoning})


# ══════════════════════════════════════════════════════════
if __name__ == '__main__':
    app.run(debug=True, port=5001)
