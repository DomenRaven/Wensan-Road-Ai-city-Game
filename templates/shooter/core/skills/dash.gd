extends RefCounted

const BASE_COOLDOWN_SEC: float = 2.0
const DASH_DURATION_SEC: float = 0.18
const DASH_SPEED_MULT: float = 3.2

static var _cooldown_remaining: float = 0.0
static var _dash_remaining: float = 0.0
static var _dash_direction: Vector2 = Vector2.UP


static func is_enabled() -> bool:
	return GameConfig.has_skill("dash")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)
	if _dash_remaining > 0.0:
		_dash_remaining = maxf(0.0, _dash_remaining - delta)


static func is_active() -> bool:
	return _dash_remaining > 0.0


static func get_dash_velocity(base_speed: float) -> Vector2:
	if not is_active():
		return Vector2.ZERO
	return _dash_direction.normalized() * base_speed * DASH_SPEED_MULT


static func try_activate(move_direction: Vector2) -> bool:
	if not is_enabled() or _cooldown_remaining > 0.0 or _dash_remaining > 0.0:
		return false
	_dash_direction = move_direction if move_direction.length_squared() > 0.01 else Vector2.UP
	var scale: float = GameConfig.get_skill_cooldown_scale("dash")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	_dash_remaining = DASH_DURATION_SEC
	return true
