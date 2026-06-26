extends RefCounted

const BASE_COOLDOWN_SEC: float = 1.0
const PARRY_WINDOW_FRAMES: int = 8
const DAMAGE_REDUCTION: float = 0.35
const COUNTER_DAMAGE_MULT: float = 1.5

static var _cooldown_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("block_parry")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)


static func get_damage_multiplier(is_blocking: bool) -> float:
	if not is_blocking:
		return 1.0
	if is_enabled():
		return DAMAGE_REDUCTION
	return 0.55


static func try_parry(block_frames_held: int) -> bool:
	if not is_enabled() or _cooldown_remaining > 0.0:
		return false
	if block_frames_held > PARRY_WINDOW_FRAMES:
		return false
	var scale: float = GameConfig.get_skill_cooldown_scale("block_parry")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	return true


static func get_counter_damage(base_damage: int) -> int:
	return int(round(float(base_damage) * COUNTER_DAMAGE_MULT))
