"""
GuardianMed — ML Adherence Risk Prediction Module (Rule-Based)
Predicts the probability of missing the next dose based on recent adherence patterns.
Uses a simple, interpretable rule-based approach instead of ML.
"""


def predict_miss_probability(missed_last_3_days, avg_delay_minutes, adherence_rate):
    """
    Predict the probability (0-100%) that the patient will miss
    their next dose based on recent behaviour.
    
    Uses a simple, interpretable rule-based approach:
    - probability = (missed_count / total_count) * 100
    - If no data: return 0.2 (20%) as safe default
    - Considers adherence rate and delay patterns

    Args:
        missed_last_3_days: int (0–3) — doses missed in last 3 days
        avg_delay_minutes: float — average delay in taking doses
        adherence_rate: float (0–100) — overall adherence percentage

    Returns:
        dict with probability, risk_level, and explanation
    """
    
    # Default: if no data available, assume low-moderate risk
    if adherence_rate == 0 and missed_last_3_days == 0 and avg_delay_minutes == 0:
        prob_pct = 20.0  # Safe default when no history
    else:
        # Base probability = inverse of adherence
        # If adherence is 100%, prob = 0%. If 50%, prob = 50%.
        base_prob = max(0, (100 - adherence_rate) / 100)
        
        # Adjust based on recent misses (more miss = higher risk)
        miss_factor = (missed_last_3_days / 3.0) if missed_last_3_days > 0 else 0
        
        # Adjust based on delay pattern (more delay = higher risk)
        delay_factor = min(1.0, (avg_delay_minutes / 60.0)) if avg_delay_minutes > 0 else 0
        
        # Combined probability: weighted average
        prob = (base_prob * 0.6) + (miss_factor * 0.25) + (delay_factor * 0.15)
        prob_pct = round(min(100, max(0, prob * 100)), 1)

    # Determine risk level
    if prob_pct >= 70:
        risk_level = "high"
        color = "#E24B4A"
        icon = "🔴"
        explanation = "High risk — patient is likely to miss the next dose. Immediate intervention recommended."
    elif prob_pct >= 40:
        risk_level = "medium"
        color = "#BA7517"
        icon = "🟡"
        explanation = "Moderate risk — some irregularity detected. Consider sending a reminder."
    else:
        risk_level = "low"
        color = "#1D9E75"
        icon = "🟢"
        explanation = "Low risk — patient is following the schedule well."

    return {
        "probability": prob_pct,
        "risk_level": risk_level,
        "color": color,
        "icon": icon,
        "explanation": explanation,
        "features_used": {
            "missed_last_3_days": missed_last_3_days,
            "avg_delay_minutes": round(avg_delay_minutes, 1),
            "adherence_rate": round(adherence_rate, 1)
        }
    }


def get_feature_importance():
    """Return feature importance (simplified version)."""
    return [
        {"feature": "adherence_rate", "importance": 60.0},
        {"feature": "missed_last_3_days", "importance": 25.0},
        {"feature": "avg_delay_minutes", "importance": 15.0}
    ]

print("✓ ML prediction system loaded (Rule-based, dynamic risk assessment)")
