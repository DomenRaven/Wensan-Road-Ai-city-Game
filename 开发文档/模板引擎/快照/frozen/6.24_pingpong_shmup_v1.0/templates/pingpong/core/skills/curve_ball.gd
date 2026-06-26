extends RefCounted
class_name CurveBallSkill

## Prefabricated skill — next paddle hit applies extra curve angle (wired in ball.gd)

const BASE_COOLDOWN_SEC: float = 6.0
const ANGLE_MULT: float = 1.65

static var _armed: bool = false
static var _cooldown_timer: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("curve_ball")


static func get_cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("curve_ball")


static func try_activate() -> bool:
	if not is_enabled():
		return false
	if _cooldown_timer > 0.0 or _armed:
		return false
	_armed = true
	_cooldown_timer = get_cooldown_sec()
	return true


static func consume_pending() -> bool:
	if not _armed:
		return false
	_armed = false
	return true


static func get_angle_multiplier() -> float:
	return ANGLE_MULT


static func tick(delta: float) -> void:
	if _cooldown_timer > 0.0:
		_cooldown_timer = maxf(0.0, _cooldown_timer - delta)


static func is_ready() -> bool:
	return is_enabled() and _cooldown_timer <= 0.0 and not _armed


static func reset_for_match() -> void:
	_armed = false
	_cooldown_timer = 0.0
