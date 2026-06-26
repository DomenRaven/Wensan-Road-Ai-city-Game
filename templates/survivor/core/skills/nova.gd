extends RefCounted

const BASE_COOLDOWN_SEC: float = 12.0
const NOVA_RADIUS: float = 120.0
const NOVA_DAMAGE: int = 25

static var _cooldown_remaining: float = 0.0


static func is_enabled() -> bool:
	return GameConfig.has_skill("nova")


static func tick(delta: float) -> void:
	if _cooldown_remaining > 0.0:
		_cooldown_remaining = maxf(0.0, _cooldown_remaining - delta)


static func try_burst(origin: Vector2, tree: SceneTree) -> bool:
	if not is_enabled():
		return false
	if _cooldown_remaining > 0.0:
		return false
	var scale: float = GameConfig.get_skill_cooldown_scale("nova")
	_cooldown_remaining = BASE_COOLDOWN_SEC * scale
	_damage_enemies_in_radius(origin, tree)
	return true


static func _damage_enemies_in_radius(origin: Vector2, tree: SceneTree) -> void:
	var radius_sq: float = NOVA_RADIUS * NOVA_RADIUS
	for enemy: Node in tree.get_nodes_in_group("enemy"):
		if not enemy is Node2D:
			continue
		var enemy_node: Node2D = enemy as Node2D
		if enemy_node.global_position.distance_squared_to(origin) <= radius_sq:
			if enemy_node.has_method("take_damage"):
				enemy_node.call("take_damage", NOVA_DAMAGE)


static func get_cooldown_remaining() -> float:
	return _cooldown_remaining
