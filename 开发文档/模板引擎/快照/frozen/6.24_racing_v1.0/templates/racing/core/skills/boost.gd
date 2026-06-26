extends RefCounted
class_name BoostSkill

## Prefabricated nitro boost — wired in track_runner.gd

const DURATION_SEC: float = 3.0
const BASE_COOLDOWN_SEC: float = 5.0
const SPEED_MULT: float = 1.65

static var _active_timer: float = 0.0
static var _cooldown_timer: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("boost")


static func get_cooldown_sec() -> float:
	return BASE_COOLDOWN_SEC * GameConfig.get_skill_cooldown_scale("boost")


static func try_activate() -> bool:
	if not is_enabled():
		return false
	if _cooldown_timer > 0.0 or _active_timer > 0.0:
		return false
	_active_timer = DURATION_SEC
	_cooldown_timer = get_cooldown_sec()
	return true


static func tick(delta: float) -> void:
	if _active_timer > 0.0:
		_active_timer = maxf(0.0, _active_timer - delta)
	if _cooldown_timer > 0.0:
		_cooldown_timer = maxf(0.0, _cooldown_timer - delta)


static func is_active() -> bool:
	return _active_timer > 0.0


static func is_ready() -> bool:
	return is_enabled() and _cooldown_timer <= 0.0 and _active_timer <= 0.0


static func get_speed_multiplier() -> float:
	return SPEED_MULT if is_active() else 1.0
