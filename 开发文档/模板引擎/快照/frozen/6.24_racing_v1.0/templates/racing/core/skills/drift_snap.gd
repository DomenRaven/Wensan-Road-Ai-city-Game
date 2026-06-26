extends RefCounted
class_name DriftSnapSkill

## Prefabricated drift — keeps forward speed while steering in corners

const TURN_SPEED_PENALTY: float = 0.82

static func is_enabled() -> bool:
	return GameConfig.has_skill("drift_snap")


static func apply_turn_penalty(base_factor: float, steering_input: float) -> float:
	if is_enabled():
		return 1.0
	if absf(steering_input) < 0.05:
		return 1.0
	return base_factor * TURN_SPEED_PENALTY
