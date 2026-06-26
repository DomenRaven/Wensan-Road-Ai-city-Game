extends Node2D

const ENEMY_SCENE: PackedScene = preload("res://scenes/enemy.tscn")
const SurvivorWorld := preload("res://core/survivor_world.gd")
const POOL_SIZE: int = 48

signal wave_advanced(wave_index: int)

var _pool: Array[Area2D] = []
var _spawn_interval_ms: float = 4000.0
var _ring_min: float = 520.0
var _ring_max: float = 680.0
var _max_alive: int = 40
var _spawn_timer: float = 0.0
var _base_hp: int = 10
var _speed_min: float = 50.0
var _speed_max: float = 80.0
var _xp_value: int = 30
var _contact_damage: int = 5
var _wave_index: int = 1
var _time_remaining_ratio: float = 1.0
var _player_level: int = 1
var _enabled: bool = true
var _scale_from_level: int = 4
var _speed_bonus_per_level: float = 0.05
var _hp_bonus_per_level: float = 0.05

@onready var _enemies_root: Node2D = $Enemies


func _ready() -> void:
	_apply_tuning()
	_build_pool()


func _build_pool() -> void:
	for _i: int in POOL_SIZE:
		var enemy: Area2D = ENEMY_SCENE.instantiate() as Area2D
		enemy.visible = false
		enemy.process_mode = Node.PROCESS_MODE_DISABLED
		enemy.set_deferred("monitoring", false)
		enemy.set_deferred("monitorable", false)
		_enemies_root.add_child(enemy)
		if enemy.has_signal("destroyed"):
			enemy.destroyed.connect(_on_enemy_destroyed)
		_pool.append(enemy)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var spawn_cfg: Dictionary = tuning.get("spawn", {}) as Dictionary
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	var xp_cfg: Dictionary = tuning.get("xp", {}) as Dictionary
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	_spawn_interval_ms = float(spawn_cfg.get("interval_ms", _spawn_interval_ms))
	_ring_min = float(spawn_cfg.get("ring_min", _ring_min))
	_ring_max = float(spawn_cfg.get("ring_max", _ring_max))
	_max_alive = int(spawn_cfg.get("max_alive", _max_alive))
	_base_hp = int(enemy_cfg.get("base_hp", _base_hp))
	_speed_min = float(enemy_cfg.get("speed_min", enemy_cfg.get("speed", _speed_min)))
	_speed_max = float(enemy_cfg.get("speed_max", _speed_min + 30.0))
	_xp_value = int(xp_cfg.get("gem_value", _xp_value))
	_contact_damage = int(enemy_cfg.get("contact_damage", _contact_damage))
	_scale_from_level = int(level_cfg.get("enemy_scale_from_level", _scale_from_level))
	_speed_bonus_per_level = float(level_cfg.get("enemy_speed_bonus_per_level", _speed_bonus_per_level))
	_hp_bonus_per_level = float(level_cfg.get("enemy_hp_bonus_per_level", _hp_bonus_per_level))


func set_time_remaining_ratio(ratio: float) -> void:
	_time_remaining_ratio = clampf(ratio, 0.0, 1.0)
	var new_wave: int = 1 + int((1.0 - _time_remaining_ratio) * 7.0)
	if new_wave != _wave_index:
		_wave_index = new_wave
		wave_advanced.emit(_wave_index)


func set_player_level(level: int) -> void:
	_player_level = maxi(1, level)


func set_spawning_enabled(enabled: bool) -> void:
	_enabled = enabled


func get_wave_index() -> int:
	return _wave_index


func clear_all_enemies() -> void:
	for enemy: Area2D in _pool:
		if enemy.visible and enemy.has_method("deactivate"):
			enemy.call("deactivate")


func spawn_minions_near(center: Vector2, count: int) -> void:
	for _i: int in count:
		var angle: float = randf() * TAU
		var spawn_pos: Vector2 = center + Vector2(cos(angle), sin(angle)) * randf_range(40.0, 90.0)
		spawn_pos = SurvivorWorld.clamp_point(spawn_pos)
		var enemy: Area2D = _acquire_enemy()
		if enemy == null:
			continue
		enemy.global_position = spawn_pos
		if enemy.has_method("activate"):
			enemy.call(
				"activate",
				_scaled_hp(),
				randf_range(_scaled_speed_min(), _scaled_speed_max()),
				_xp_value,
				_contact_damage
			)


func _physics_process(delta: float) -> void:
	if not _enabled or get_tree().paused:
		return
	_spawn_timer += delta
	var factor: float = maxf(0.2, _time_remaining_ratio)
	var interval: float = (_spawn_interval_ms / 1000.0) * factor
	var alive: int = _count_alive()
	if _spawn_timer >= interval and alive < _max_alive:
		_spawn_timer = 0.0
		_spawn_enemy()


func _count_alive() -> int:
	var alive: int = 0
	for enemy: Area2D in _pool:
		if enemy.visible:
			alive += 1
	return alive


func _scaled_hp() -> int:
	var hp: float = float(_base_hp)
	if _player_level >= _scale_from_level:
		var extra_levels: int = _player_level - _scale_from_level + 1
		hp *= 1.0 + float(extra_levels) * _hp_bonus_per_level
	return maxi(1, int(round(hp)))


func _scaled_speed_min() -> float:
	var mult: float = 1.0
	if _player_level >= _scale_from_level:
		var extra_levels: int = _player_level - _scale_from_level + 1
		mult += float(extra_levels) * _speed_bonus_per_level
	return _speed_min * mult


func _scaled_speed_max() -> float:
	var mult: float = 1.0
	if _player_level >= _scale_from_level:
		var extra_levels: int = _player_level - _scale_from_level + 1
		mult += float(extra_levels) * _speed_bonus_per_level
	return _speed_max * mult


func _spawn_enemy() -> void:
	var player: Node2D = get_tree().get_first_node_in_group("player") as Node2D
	if player == null:
		return
	var angle: float = randf() * TAU
	var distance: float = randf_range(_ring_min, _ring_max)
	var spawn_pos: Vector2 = player.global_position + Vector2(cos(angle), sin(angle)) * distance
	spawn_pos = SurvivorWorld.clamp_point(spawn_pos)
	var enemy: Area2D = _acquire_enemy()
	if enemy == null:
		return
	enemy.global_position = spawn_pos
	if enemy.has_method("activate"):
		enemy.call(
			"activate",
			_scaled_hp(),
			randf_range(_scaled_speed_min(), _scaled_speed_max()),
			_xp_value,
			_contact_damage
		)


func _acquire_enemy() -> Area2D:
	for enemy: Area2D in _pool:
		if not enemy.visible:
			return enemy
	return null


func _on_enemy_destroyed(enemy: Area2D, xp_value: int) -> void:
	var arena: Node = get_parent()
	if arena != null and arena.has_method("spawn_xp_gem"):
		arena.call_deferred("spawn_xp_gem", enemy.global_position, xp_value)
	if enemy.has_method("deactivate"):
		enemy.call("deactivate")
