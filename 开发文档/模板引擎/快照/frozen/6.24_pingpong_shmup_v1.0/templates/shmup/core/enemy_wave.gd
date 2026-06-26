extends Node2D

signal wave_cleared(wave_index: int)
signal enemy_destroyed(score_value: int)

const ENEMY_SCENE: PackedScene = preload("res://scenes/enemy.tscn")

var _wave_index: int = 0
var _spawned_this_wave: int = 0
var _alive_count: int = 0
var _spawn_timer: float = 0.0
var _wave_active: bool = false
var _enemy_count: int = 6
var _spawn_interval_ms: int = 1200
var _spawn_x_positions: Array[float] = [100.0, 220.0, 340.0, 460.0, 540.0, 580.0]

@onready var _enemies_root: Node2D = $Enemies


func _ready() -> void:
	_apply_tuning()
	call_deferred("start_next_wave")


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var wave_cfg: Dictionary = tuning.get("wave", {}) as Dictionary
	var spawn_cfg: Dictionary = tuning.get("spawn", {}) as Dictionary
	_enemy_count = int(wave_cfg.get("enemy_count", _enemy_count))
	_spawn_interval_ms = int(spawn_cfg.get("interval_ms", _spawn_interval_ms))


func start_next_wave() -> void:
	_wave_index += 1
	_spawned_this_wave = 0
	_spawn_timer = 0.0
	_wave_active = true


func get_wave_index() -> int:
	return _wave_index


func _process(delta: float) -> void:
	if not _wave_active:
		return
	if _spawned_this_wave < _enemy_count:
		_spawn_timer += delta
		if _spawn_timer >= float(_spawn_interval_ms) / 1000.0:
			_spawn_timer = 0.0
			_spawn_enemy()
			_spawned_this_wave += 1
	elif _alive_count <= 0:
		_wave_active = false
		wave_cleared.emit(_wave_index)


func _spawn_enemy() -> void:
	var enemy: Area2D = ENEMY_SCENE.instantiate() as Area2D
	var x_index: int = _spawned_this_wave % _spawn_x_positions.size()
	var spawn_x: float = _spawn_x_positions[x_index]
	enemy.position = Vector2(spawn_x, -40.0)
	if enemy.has_signal("destroyed"):
		enemy.destroyed.connect(_on_enemy_destroyed)
	_enemies_root.add_child(enemy)
	_alive_count += 1


func _on_enemy_destroyed(_enemy: Area2D) -> void:
	_alive_count = maxi(0, _alive_count - 1)
	enemy_destroyed.emit(100)
