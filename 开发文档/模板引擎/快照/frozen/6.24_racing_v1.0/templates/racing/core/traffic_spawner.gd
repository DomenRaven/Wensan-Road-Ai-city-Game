extends Node2D

const NpcCarScene: PackedScene = preload("res://scenes/prefabs/npc_car.tscn")
const ObstacleScene: PackedScene = preload("res://scenes/prefabs/road_obstacle.tscn")

var _active: bool = false
var _spawn_delay_ms: float = 2000.0
var _spawn_timer_ms: float = 0.0
var _lap_count: int = 0
var _track_left: float = 50.0
var _track_right: float = 590.0
var _sprite_scale: float = 0.14
var _base_delay_ms: float = 2000.0
var _min_delay_ms: float = 500.0
var _delay_per_lap_ms: float = 200.0
var _obstacle_chance: float = 0.4
var _npc_speed_min: float = 75.0
var _npc_speed_max_base: float = 150.0
var _npc_speed_per_lap: float = 8.0
var _lateral_after_lap: int = 2
var _lateral_speed_max: float = 38.0
var _npc_yellow_path: String = ""
var _npc_blue_path: String = ""

@onready var _entities_root: Node2D = $Entities


func setup(
	track_left: float,
	track_right: float,
	sprite_scale: float,
	npc_yellow_path: String,
	npc_blue_path: String
) -> void:
	_track_left = track_left
	_track_right = track_right
	_sprite_scale = sprite_scale
	_npc_yellow_path = npc_yellow_path
	_npc_blue_path = npc_blue_path
	var tuning: Dictionary = GameConfig.get_tuning()
	var spawn_cfg: Dictionary = tuning.get("spawn", {}) as Dictionary
	_base_delay_ms = float(spawn_cfg.get("base_delay_ms", _base_delay_ms))
	_min_delay_ms = float(spawn_cfg.get("min_delay_ms", _min_delay_ms))
	_delay_per_lap_ms = float(spawn_cfg.get("delay_per_lap_ms", _delay_per_lap_ms))
	_obstacle_chance = clampf(float(spawn_cfg.get("obstacle_chance_after_lap1", _obstacle_chance)), 0.2, 0.7)
	_npc_speed_min = float(spawn_cfg.get("npc_speed_min", _npc_speed_min))
	_npc_speed_max_base = float(spawn_cfg.get("npc_speed_max_base", _npc_speed_max_base))
	_npc_speed_per_lap = float(spawn_cfg.get("npc_speed_per_lap", _npc_speed_per_lap))
	_lateral_after_lap = int(spawn_cfg.get("lateral_after_lap", _lateral_after_lap))
	_lateral_speed_max = float(spawn_cfg.get("lateral_speed_max", _lateral_speed_max))


func set_active(value: bool) -> void:
	_active = value


func set_lap_count(laps: int) -> void:
	_lap_count = laps


func reset_spawner() -> void:
	for child: Node in _entities_root.get_children():
		child.queue_free()
	_lap_count = 0
	_spawn_entity(0.0)
	_schedule_next_spawn()


func process_spawner(delta: float, player_speed: float) -> void:
	if not _active:
		return
	for child: Node in _entities_root.get_children():
		if child.has_method("update_motion"):
			child.call("update_motion", delta, player_speed)
	_spawn_timer_ms -= delta * 1000.0
	if _spawn_timer_ms <= 0.0:
		_spawn_entity(player_speed)
		_schedule_next_spawn()


func _schedule_next_spawn() -> void:
	var delay: float = maxf(_min_delay_ms, _base_delay_ms - float(_lap_count) * _delay_per_lap_ms)
	_spawn_delay_ms = delay
	_spawn_timer_ms = delay


func _spawn_entity(_player_speed: float) -> void:
	var spawn_x: float = randf_range(_track_left + 20.0, _track_right - 20.0)
	var use_obstacle: bool = _lap_count >= 1 and randf() > (1.0 - _obstacle_chance)
	if use_obstacle:
		var obstacle: Area2D = ObstacleScene.instantiate() as Area2D
		_entities_root.add_child(obstacle)
		obstacle.position = Vector2(spawn_x, -38.0)
	else:
		var npc: Area2D = NpcCarScene.instantiate() as Area2D
		_entities_root.add_child(npc)
		npc.position = Vector2(spawn_x, -38.0)
		var base_speed: float = randf_range(
			_npc_speed_min,
			_npc_speed_max_base + float(_lap_count) * _npc_speed_per_lap
		)
		var lateral: float = 0.0
		if _lap_count >= _lateral_after_lap:
			lateral = randf_range(-_lateral_speed_max, _lateral_speed_max)
		var yellow: bool = randf() > 0.5
		var sprite_path: String = _npc_yellow_path if yellow else _npc_blue_path
		var fallback: Color = Color(0.95, 0.85, 0.1, 1.0) if yellow else Color(0.2, 0.45, 0.95, 1.0)
		if npc.has_method("setup_from_theme"):
			npc.call(
				"setup_from_theme",
				base_speed,
				lateral,
				sprite_path,
				_track_left,
				_track_right,
				_sprite_scale,
				fallback,
				0.4
			)
