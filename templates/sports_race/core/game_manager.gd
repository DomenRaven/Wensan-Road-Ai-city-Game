extends Node2D

const TimerHudUtil := preload("res://core/timer_hud.gd")

var _game_over: bool = false

@onready var _game_root: Node2D = $GameRoot
@onready var _info_label: Label = $CanvasLayer/HUD/InfoLabel
@onready var _status_label: Label = $CanvasLayer/HUD/StatusLabel


func _ready() -> void:
	_status_label.visible = false
	_load_game()


func _load_game() -> void:
	var scene_path: String = "res://scenes/game.tscn"
	if not ResourceLoader.exists(scene_path):
		push_error("GameManager: game scene missing: %s" % scene_path)
		return
	var packed: PackedScene = load(scene_path) as PackedScene
	var game: Node2D = packed.instantiate() as Node2D
	_game_root.add_child(game)
	if game.has_method("setup"):
		game.call("setup", self)


func update_run_hud(
	distance_m: int,
	time_left: float,
	elapsed_sec: int,
	sprint_ready: bool
) -> void:
	if _game_over:
		return
	var title: String = str(GameConfig.get_theme().get("title", GameConfig.get_display_name()))
	_info_label.text = TimerHudUtil.format_run_hud(
		title,
		distance_m,
		elapsed_sec,
		time_left,
		sprint_ready
	)


func on_run_lost(distance_m: int) -> void:
	if _game_over:
		return
	_game_over = true
	_status_label.text = "绊倒了！跑了 %dm · 按 R 重来" % distance_m
	_status_label.visible = true


func on_run_won(message: String, distance_m: int) -> void:
	if _game_over:
		return
	_game_over = true
	_status_label.text = "%s  距离 %dm · 按 R 再来" % [message, distance_m]
	_status_label.visible = true


func _unhandled_input(event: InputEvent) -> void:
	if _game_over and event is InputEventKey:
		var key_event: InputEventKey = event as InputEventKey
		if key_event.pressed and key_event.keycode == KEY_R:
			get_tree().reload_current_scene()
