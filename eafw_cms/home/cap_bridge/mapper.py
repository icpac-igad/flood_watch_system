"""Map FloodWatch risk levels to CAP severity/urgency/certainty fields."""

RISK_TO_CAP = {
    "emergency": {"severity": "Extreme", "urgency": "Immediate", "certainty": "Observed"},
    "alarm":     {"severity": "Severe",  "urgency": "Expected",  "certainty": "Likely"},
    "warning":   {"severity": "Moderate", "urgency": "Future",   "certainty": "Possible"},
    "normal":    {"severity": "Minor",   "urgency": "Past",      "certainty": "Unlikely"},
}


def get_cap_fields(risk_level):
    """Map FloodWatch risk level to CAP severity/urgency/certainty."""
    return RISK_TO_CAP.get(risk_level.lower(), RISK_TO_CAP["normal"])
