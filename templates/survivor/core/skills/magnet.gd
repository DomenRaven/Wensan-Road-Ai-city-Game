extends RefCounted

const SKILL_RANGE_MULTIPLIER: float = 1.6


static func is_enabled() -> bool:
	return GameConfig.has_skill("magnet")


static func get_range_multiplier() -> float:
	if is_enabled():
		return SKILL_RANGE_MULTIPLIER
	return 1.0
