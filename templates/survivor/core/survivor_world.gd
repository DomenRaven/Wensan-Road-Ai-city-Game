extends RefCounted

const DEFAULT_SIZE: Vector2 = Vector2(3000.0, 3000.0)
const DEFAULT_MARGIN: float = 24.0


static func get_size() -> Vector2:
	var tuning: Dictionary = GameConfig.get_tuning()
	if not tuning.has("world") or not tuning["world"] is Dictionary:
		return DEFAULT_SIZE
	var world_cfg: Dictionary = tuning["world"] as Dictionary
	return Vector2(
		float(world_cfg.get("width", DEFAULT_SIZE.x)),
		float(world_cfg.get("height", DEFAULT_SIZE.y))
	)


static func get_center() -> Vector2:
	return get_size() * 0.5


static func get_margin() -> float:
	var tuning: Dictionary = GameConfig.get_tuning()
	if not tuning.has("world") or not tuning["world"] is Dictionary:
		return DEFAULT_MARGIN
	var world_cfg: Dictionary = tuning["world"] as Dictionary
	return float(world_cfg.get("margin", DEFAULT_MARGIN))


static func get_grid_step() -> float:
	var tuning: Dictionary = GameConfig.get_tuning()
	if not tuning.has("world") or not tuning["world"] is Dictionary:
		return 100.0
	var world_cfg: Dictionary = tuning["world"] as Dictionary
	return float(world_cfg.get("grid_step", 100.0))


static func clamp_point(point: Vector2) -> Vector2:
	var size: Vector2 = get_size()
	var margin: float = get_margin()
	return Vector2(
		clampf(point.x, margin, size.x - margin),
		clampf(point.y, margin, size.y - margin)
	)
