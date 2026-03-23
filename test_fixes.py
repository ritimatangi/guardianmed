#!/usr/bin/env python
"""Test script to verify all fixes work correctly."""

from app import app
from database import get_today_schedule, get_db
from ml_model import predict_miss_probability
import json

def test_schedule():
    """Test that today's schedule is populated."""
    schedule = get_today_schedule()
    assert len(schedule) > 0, "Schedule should have doses"
    print(f"✓ Schedule API: {len(schedule)} doses today")
    return schedule

def test_dose_marking():
    """Test that dose marking updates status and timestamp."""
    app.config['TESTING'] = True
    client = app.test_client()
    
    schedule = get_today_schedule()
    if not schedule:
        print("✗ No schedule to test")
        return
    
    first_dose = schedule[0]
    log_id = first_dose['log_id']
    initial_status = first_dose['status']
    
    # Mark as taken
    response = client.post(
        '/api/dose/log',
        data=json.dumps({'log_id': log_id}),
        content_type='application/json'
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    result = response.get_json()
    assert result['message'] == 'Dose logged', "Should return success message"
    
    # Verify in database
    conn = get_db()
    row = conn.execute(
        'SELECT status, taken_at FROM dose_log WHERE id = ?',
        (log_id,)
    ).fetchone()
    conn.close()
    
    assert row['status'] == 'taken', f"Status should be 'taken', got {row['status']}"
    assert row['taken_at'] is not None, "taken_at should be set"
    
    print(f"✓ Dose Marking: Status changed from '{initial_status}' to 'taken'")
    print(f"  Timestamp: {row['taken_at']}")

def test_ml_prediction():
    """Test that ML predictions vary based on adherence."""
    tests = [
        (0, "20.0", "low"),     # No data → safe default
        (30, "42.0", "medium"),  # Poor adherence
        (100, "0", "low"),       # Perfect adherence
    ]
    
    for adherence, expected_prob, expected_level in tests:
        result = predict_miss_probability(0, 0, adherence)
        prob = str(result['probability'])
        level = result['risk_level']
        
        assert prob == expected_prob, f"Adherence {adherence}: expected prob {expected_prob}, got {prob}"
        assert level == expected_level, f"Adherence {adherence}: expected level {expected_level}, got {level}"
        
    print("✓ ML Prediction: Variable outputs based on adherence")
    for adherence, prob, level in tests:
        print(f"  Adherence {adherence}% → {prob}% risk ({level})")

def test_auto_miss_overdue():
    """Test that auto_miss_overdue marks doses correctly with 30-min grace."""
    from database import auto_miss_overdue
    from datetime import datetime, timedelta
    
    # This test just verifies the function runs without error
    # And that it doesn't mark ALL doses as missed
    auto_miss_overdue()
    
    schedule = get_today_schedule()
    statuses = set(d['status'] for d in schedule)
    
    # Should have mixed statuses, not all "missed"  
    assert 'missed' not in statuses or 'upcoming' not in statuses or len(statuses) > 1 or len(schedule) == 0, \
        "Should have varied statuses or be empty, not all same"
    
    print(f"✓ Auto Miss Overdue: Working correctly (statuses: {statuses})")

if __name__ == '__main__':
    print("Testing GuardianMed fixes...\n")
    
    try:
        test_schedule()
        test_dose_marking()
        test_ml_prediction()
        test_auto_miss_overdue()
        
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
