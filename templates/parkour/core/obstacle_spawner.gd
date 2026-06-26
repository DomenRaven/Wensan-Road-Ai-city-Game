extends Node2D

const ObstacleScript := preload("res://core/obstacle.gd")
const OBSTACLE_SCENE: PackedScene = preload("res://scenes/prefabs/obstacle.tscn")

const GROUND_Y: float = 300.0
const SPAWN_X: float = 690.0

signal obstacle_hit_player

var _scroll_speed: float = 300.0
var _min_gap_ms: float = 2000.0
var _max_gap_ms: float = 4000.0
var _next_spawn_at_ms: int = 0
var _game_over: bool = false
var _playing: bool = false

@onready var _obstacles_root: Node2D = $Obstacles


func setup(scroll_speed: float, min_gap_ms: float, max_gap_ms: float) -> void:
	_scroll_speed = scroll_speed
	_min_gap_ms = min_gap_ms
	_max_gap_ms = max_gap_ms


func start_spawning() -> void:
	_playing = true
	_game_over = false
	_next_spawn_at_ms = Time.get_ticks_msec() + randi_range(1000, 2000)


func stop_spawning() -> void:
	_playing = false


func set_game_over(value: bool) -> void:
	_game_over = value
	if value:
		_playing = false


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed
	for child: Node in _obstacles_root.get_children():
		if child.has_method("set_scroll_speed"):
			child.call("set_scroll_speed", speed)


func clear_all() -> void:
	for child: Node in _obstacles_root.get_children():
		child.queue_free()


func _process(_delta: float) -> void:
	if not _playing or _game_over:
		return
	var now_ms: int = Time.get_ticks_msec()
	if now_ms < _next_spawn_at_ms:
		return
	_spawn_obstacle()
	var speed_scale: float = 300.0 / maxf(120.0, _scroll_speed)
	var gap_ms: int = randi_range(int(_min_gap_ms * speed_scale), int(_max_gap_ms * speed_scale))
	_next_spawn_at_ms = now_ms + gap_ms


func _spawn_obstacle() -> void:
	var variants: Array[int] = [0, 1, 2, 3]
	var variant: int = variants[randi() % variants.size()]
	var is_high: bool = variant >= 2
	var kind: int = ObstacleScript.ObstacleKind.TALL if is_high else ObstacleScript.ObstacleKind.LOW
	var y: float = GROUND_Y if is_high else GROUND_Y - 40.0
	var obs: Area2D = OBSTACLE_SCENE.instantiate() as Area2D
	_obstacles_root.add_child(obs)
	obs.position = Vector2(SPAWN_X, y)
	if obs.has_method("setup"):
		obs.call("setup", kind, _scroll_speed, variant)
	if obs.has_signal("player_hit"):
		obs.player_hit.connect(_on_obstacle_player_hit)


func _on_obstacle_player_hit() -> void:
	obstacle_hit_player.emit()
