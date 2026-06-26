extends Node2D

const CollectibleScript := preload("res://core/collectible.gd")
const COLLECTIBLE_SCENE: PackedScene = preload("res://scenes/prefabs/collectible.tscn")

const GROUND_Y: float = 300.0

signal collectible_collected(kind: int)

var _scroll_speed: float = 300.0
var _min_gap_ms: float = 1500.0
var _max_gap_ms: float = 3500.0
var _next_spawn_at_ms: int = 0
var _game_over: bool = false
var _playing: bool = false

@onready var _root: Node2D = $Collectibles


func setup(scroll_speed: float, min_gap_ms: float, max_gap_ms: float) -> void:
	_scroll_speed = scroll_speed
	_min_gap_ms = min_gap_ms
	_max_gap_ms = max_gap_ms


func start_spawning() -> void:
	_playing = true
	_game_over = false
	_next_spawn_at_ms = Time.get_ticks_msec() + randi_range(2000, 4000)


func stop_spawning() -> void:
	_playing = false


func set_game_over(value: bool) -> void:
	_game_over = value
	if value:
		_playing = false


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed
	for child: Node in _root.get_children():
		if child.has_method("set_scroll_speed"):
			child.call("set_scroll_speed", speed)


func clear_all() -> void:
	for child: Node in _root.get_children():
		child.queue_free()


func _process(_delta: float) -> void:
	if not _playing or _game_over:
		return
	var now_ms: int = Time.get_ticks_msec()
	if now_ms < _next_spawn_at_ms:
		return
	_spawn_collectible()
	var speed_scale: float = 300.0 / maxf(120.0, _scroll_speed)
	var gap_ms: int = randi_range(int(_min_gap_ms * speed_scale), int(_max_gap_ms * speed_scale))
	_next_spawn_at_ms = now_ms + gap_ms


func _spawn_collectible() -> void:
	var roll: float = randf()
	var kind: int = CollectibleScript.CollectibleKind.COIN
	if roll > 0.9:
		kind = CollectibleScript.CollectibleKind.INVINCIBLE
	elif roll > 0.8:
		kind = CollectibleScript.CollectibleKind.DOUBLE_COIN
	var y_offsets: Array[float] = [13.0, 80.0]
	var y: float = GROUND_Y - y_offsets[randi() % y_offsets.size()]
	var col: Area2D = COLLECTIBLE_SCENE.instantiate() as Area2D
	_root.add_child(col)
	col.position = Vector2(690.0, y)
	if col.has_method("setup"):
		col.call("setup", kind, _scroll_speed)
	if col.has_signal("player_collected"):
		col.player_collected.connect(_on_player_collected)


func _on_player_collected(kind: int) -> void:
	collectible_collected.emit(kind)
