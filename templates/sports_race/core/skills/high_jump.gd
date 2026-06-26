extends RefCounted
class_name HighJumpSkill

## Prefabricated skill — jump logic wired in player_racer.gd

const JUMP_MULT: float = 1.35


static func is_enabled() -> bool:
	return GameConfig.has_skill("high_jump")


static func apply_velocity(base_velocity: float) -> float:
	if is_enabled():
		return base_velocity * JUMP_MULT
	return base_velocity
