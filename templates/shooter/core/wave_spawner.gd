extends Node2D

signal wave_cleared(wave_index: int)
signal enemy_destroyed(score_value: int)
signal all_waves_cleared

const ENEMY_SCENE: PackedScene = preload("res://scenes/enemy.tscn")
const OFFSCREEN_MARGIN: float = 32.0
const SPAWN_INTERVAL_SEC: float = 0.35

var _wave_index: int = 0
var _target_waves: int = 3
var _enemies_per_wave: int = 8
var _spawned_this_wave: int = 0
var _alive_count: int = 0
var _spawn_timer: float = 0.0
var _wave_active: bool = false
var _spawn_x_positions: Array[float] = [80.0, 160.0, 240.0, 320.0, 400.0, 480.0, 560.0]

@onready var _enemies_root: Node2D = $Enemies


func _ready() -> void:
	_apply_tuning()
	call_deferred("start_next_wave")


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var wave_cfg: Dictionary = tuning.get("wave", {}) as Dictionary
	_target_waves = int(wave_cfg.get("count", _target_waves))
	_enemies_per_wave = int(wave_cfg.get("enemies_per_wave", _enemies_per_wave))


func start_next_wave() -> void:
	if _wave_index >= _target_waves:
		all_waves_cleared.emit()
		return
	_wave_index += 1
	_spawned_this_wave = 0
	_spawn_timer = 0.0
	_wave_active = true


func get_wave_index() -> int:
	return _wave_index


func get_target_waves() -> int:
	return _target_waves


func _process(delta: float) -> void:
	if not _wave_active:
		return
	if _spawned_this_wave < _enemies_per_wave:
		_spawn_timer += delta
		if _spawn_timer >= SPAWN_INTERVAL_SEC:
			_spawn_timer = 0.0
			_spawn_enemy()
			_spawned_this_wave += 1
	elif _alive_count <= 0:
		_wave_active = false
		wave_cleared.emit(_wave_index)
		if _wave_index >= _target_waves:
			all_waves_cleared.emit()
		else:
			call_deferred("start_next_wave")


func _spawn_enemy() -> void:
	var enemy: Area2D = ENEMY_SCENE.instantiate() as Area2D
	var x_index: int = _spawned_this_wave % _spawn_x_positions.size()
	var spawn_x: float = _spawn_x_positions[x_index]
	enemy.position = Vector2(spawn_x, -OFFSCREEN_MARGIN)
	if enemy.has_signal("destroyed"):
		enemy.destroyed.connect(_on_enemy_destroyed)
	_enemies_root.add_child(enemy)
	_alive_count += 1


func _on_enemy_destroyed(_enemy: Area2D) -> void:
	_alive_count = maxi(0, _alive_count - 1)
	enemy_destroyed.emit(100)
