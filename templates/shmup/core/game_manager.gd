extends Node2D

enum GameStatus { START, PLAYING, GAMEOVER }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")

var _status: GameStatus = GameStatus.START
var _score: int = 0
var _game_scene: Node2D = null
var _starting: bool = false

@onready var _game_root: Node2D = $GameRoot
@onready var _hud: Control = $CanvasLayer/HUD
@onready var _score_label: Label = $CanvasLayer/HUD/ScoreLabel
@onready var _start_screen: Control = $CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _title_label: Label = $CanvasLayer/StartScreen/TitleLabel
@onready var _go_score_label: Label = $CanvasLayer/GameOverScreen/Panel/VBox/ScoreValue
@onready var _help_label: Label = $CanvasLayer/HUD/HelpLabel
@onready var _boss_bar_panel: Control = $CanvasLayer/HUD/BossBarPanel
@onready var _boss_bar_fill: ColorRect = $CanvasLayer/HUD/BossBarPanel/Fill
@onready var _boss_bar_label: Label = $CanvasLayer/HUD/BossBarPanel/BarLabel


func _ready() -> void:
	_title_label.text = GameConfig.get_display_name()
	_show_screen(GameStatus.START)
	_wire_buttons()
	call_deferred("_warmup_assets")


func _warmup_assets() -> void:
	var ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
	ShmupSheetUtil.background_texture()
	ShmupSheetUtil.ships_frame(4)
	ShmupSheetUtil.tiles_frame(0)


func _wire_buttons() -> void:
	$CanvasLayer/StartScreen/StartButton.pressed.connect(_on_start_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/RetryButton.pressed.connect(_on_restart_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/MenuButton.pressed.connect(_on_menu_pressed)


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING
	if status != GameStatus.PLAYING:
		set_boss_bar_visible(false)


func _on_start_pressed() -> void:
	if _starting:
		return
	_score = 0
	_begin_start_flow()


func _on_restart_pressed() -> void:
	if _starting:
		return
	_score = 0
	_begin_start_flow()


func _begin_start_flow() -> void:
	_starting = true
	_start_screen.visible = false
	_game_over_screen.visible = false
	_hud.visible = true
	_help_label.visible = true
	_update_hud()
	call_deferred("_start_game")


func _on_menu_pressed() -> void:
	_clear_game()
	_starting = false
	_show_screen(GameStatus.START)


func _start_game() -> void:
	_clear_game()
	_load_game()
	_status = GameStatus.PLAYING
	_starting = false
	_update_hud()


func _clear_game() -> void:
	for child: Node in _game_root.get_children():
		_game_root.remove_child(child)
		child.queue_free()
	_game_scene = null


func _load_game() -> void:
	_game_scene = GAME_SCENE.instantiate() as Node2D
	_game_root.add_child(_game_scene)
	if _game_scene.has_method("setup"):
		_game_scene.call_deferred("setup", self)


func get_score() -> int:
	return _score


func is_playing() -> bool:
	return _status == GameStatus.PLAYING


func add_score(value: int) -> void:
	if _status != GameStatus.PLAYING:
		return
	_score += value
	_update_hud()


func on_player_died() -> void:
	if _status != GameStatus.PLAYING:
		return
	_go_score_label.text = str(_score).pad_zeros(6)
	if _game_scene != null and _game_scene.has_method("stop_game"):
		_game_scene.call("stop_game")
	await get_tree().create_timer(1.0).timeout
	_show_screen(GameStatus.GAMEOVER)


func _update_hud() -> void:
	_score_label.text = "SCORE  %s" % str(_score).pad_zeros(6)


func set_boss_bar_visible(active: bool) -> void:
	if _boss_bar_panel != null:
		_boss_bar_panel.visible = active


func update_boss_hp(current_hp: int, max_hp: int) -> void:
	if _boss_bar_panel == null or _boss_bar_fill == null or _boss_bar_label == null:
		return
	_boss_bar_panel.visible = true
	var ratio: float = 0.0
	if max_hp > 0:
		ratio = clampf(float(current_hp) / float(max_hp), 0.0, 1.0)
	_boss_bar_fill.size = Vector2(476.0 * ratio, 10.0)
	_boss_bar_label.text = "BOSS  %d / %d" % [maxi(0, current_hp), max_hp]


func shake_camera() -> void:
	if _game_scene == null:
		return
	var camera: Camera2D = _game_scene.get_node_or_null("Camera2D") as Camera2D
	if camera == null:
		return
	var tween: Tween = create_tween()
	var base: Vector2 = camera.offset
	for _i: int in 6:
		tween.tween_property(camera, "offset", base + Vector2(randf_range(-4.0, 4.0), randf_range(-2.0, 2.0)), 0.05)
	tween.tween_property(camera, "offset", base, 0.05)
