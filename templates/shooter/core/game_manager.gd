extends Node2D

signal game_won
signal game_lost

var _score: int = 0
var _target_waves: int = 3
var _game_over: bool = false

@onready var _game_root: Node2D = $GameRoot
@onready var _info_label: Label = $CanvasLayer/HUD/InfoLabel
@onready var _status_label: Label = $CanvasLayer/HUD/StatusLabel
@onready var _background: ColorRect = $Background


func _ready() -> void:
	_apply_tuning()
	_apply_theme()
	_status_label.visible = false
	_load_game()
	_update_hud()


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var wave_cfg: Dictionary = tuning.get("wave", {}) as Dictionary
	_target_waves = int(wave_cfg.get("count", _target_waves))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_hex: String = str(theme.get("bg_color", "#0a1628"))
	_background.color = Color.from_string(bg_hex, Color(0.04, 0.09, 0.16, 1.0))


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


func add_score(value: int) -> void:
	if _game_over:
		return
	_score += value
	_update_hud()


func update_hp(current_hp: int, max_hp: int) -> void:
	_update_hud(current_hp, max_hp)


func on_wave_cleared(_wave_index: int) -> void:
	if _game_over:
		return
	_update_hud()


func on_all_waves_cleared() -> void:
	if _game_over:
		return
	_show_win("太棒了！守卫成功！")


func on_player_died() -> void:
	if _game_over:
		return
	_game_over = true
	_status_label.text = "游戏结束！按 R 重来"
	_status_label.visible = true
	game_lost.emit()


func _show_win(message: String) -> void:
	_game_over = true
	_status_label.text = message
	_status_label.visible = true
	game_won.emit()


func _update_hud(current_hp: int = -1, max_hp: int = 3) -> void:
	var title: String = str(GameConfig.get_theme().get("title", GameConfig.get_display_name()))
	var wave_index: int = 0
	if _game_root.get_child_count() > 0:
		var game: Node = _game_root.get_child(0)
		var wave: Node = game.get_node_or_null("WaveSpawner")
		if wave != null and wave.has_method("get_wave_index"):
			wave_index = int(wave.call("get_wave_index"))
	var hp_text: String = ""
	if current_hp >= 0:
		hp_text = "  生命 %d/%d" % [current_hp, max_hp]
	_info_label.text = "%s  得分 %d  波次 %d/%d%s" % [
		title,
		_score,
		wave_index,
		_target_waves,
		hp_text
	]


func _unhandled_input(event: InputEvent) -> void:
	if _game_over and event is InputEventKey:
		var key_event: InputEventKey = event as InputEventKey
		if key_event.pressed and key_event.keycode == KEY_R:
			get_tree().reload_current_scene()
