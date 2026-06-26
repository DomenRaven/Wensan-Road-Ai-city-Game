extends Control

enum GameStatus { START, PLAYING, GAMEOVER }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _status: GameStatus = GameStatus.START
var _laps: int = 0
var _time_left: int = 90
var _game_scene: Node2D = null
var _starting: bool = false

@onready var _backdrop: ColorRect = $Backdrop
@onready var _game_host: SubViewportContainer = $GameHost
@onready var _game_root: Node2D = $GameHost/GameViewport/GameRoot
@onready var _hud: Control = $GameHost/GameViewport/CanvasLayer/HUD
@onready var _time_label: Label = $GameHost/GameViewport/CanvasLayer/HUD/TimePanel/VBox/TimeValue
@onready var _lap_label: Label = $GameHost/GameViewport/CanvasLayer/HUD/LapPanel/VBox/LapValue
@onready var _start_screen: Control = $GameHost/GameViewport/CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $GameHost/GameViewport/CanvasLayer/GameOverScreen
@onready var _title_label: Label = $GameHost/GameViewport/CanvasLayer/StartScreen/TitleLabel
@onready var _subtitle_label: Label = $GameHost/GameViewport/CanvasLayer/StartScreen/SubtitleLabel
@onready var _go_lap_label: Label = $GameHost/GameViewport/CanvasLayer/GameOverScreen/Panel/VBox/LapValue
@onready var _help_label: Label = $GameHost/GameViewport/CanvasLayer/HUD/HelpLabel


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_game_host.stretch = false
	_game_host.custom_minimum_size = Vector2(RacingViewportScript.WIDTH, RacingViewportScript.HEIGHT)
	_game_host.size = Vector2(RacingViewportScript.WIDTH, RacingViewportScript.HEIGHT)
	_backdrop.color = Color.from_string("#87CEEB", Color(0.53, 0.81, 0.92, 1.0))
	_apply_theme()
	_show_screen(GameStatus.START)
	_wire_buttons()
	if not get_viewport().size_changed.is_connected(_refit_display):
		get_viewport().size_changed.connect(_refit_display)
	call_deferred("_warmup_assets")
	call_deferred("_refit_display")


func _refit_display() -> void:
	if not is_node_ready() or _game_host == null:
		return
	var view_size: Vector2 = get_viewport_rect().size
	if view_size.x <= 1.0 or view_size.y <= 1.0:
		return
	var design: Vector2 = Vector2(RacingViewportScript.WIDTH, RacingViewportScript.HEIGHT)
	var scale_x: float = view_size.x / design.x
	var scale_y: float = view_size.y / design.y
	# 与秒哒 App.tsx「540×960 + max-w/full max-h/full」一致：等比缩放塞进窗口
	var scale_factor: float = minf(scale_x, scale_y)
	_game_host.scale = Vector2.ONE * scale_factor
	_game_host.size = design
	_game_host.position = (view_size - design * scale_factor) * 0.5


func _warmup_assets() -> void:
	var game_theme: Dictionary = GameConfig.get_theme()
	var paths: PackedStringArray = PackedStringArray([
		str(game_theme.get("track_atlas", "")),
		str(game_theme.get("player_sprite", "")),
		str(game_theme.get("npc_yellow_sprite", "")),
		str(game_theme.get("npc_blue_sprite", "")),
	])
	ThemeSpriteUtil.warmup_paths(paths)


func _apply_theme() -> void:
	var game_theme: Dictionary = GameConfig.get_theme()
	var title: String = str(game_theme.get("title", GameConfig.get_display_name()))
	_title_label.text = title
	_subtitle_label.text = "快乐竞速，挑战极限！"
	var tuning: Dictionary = GameConfig.get_tuning()
	var round_cfg: Dictionary = tuning.get("round", {}) as Dictionary
	_time_left = int(round_cfg.get("duration_sec", 90))
	_update_hud()


func _wire_buttons() -> void:
	$GameHost/GameViewport/CanvasLayer/StartScreen/StartButton.pressed.connect(_on_start_pressed)
	$GameHost/GameViewport/CanvasLayer/GameOverScreen/Panel/VBox/RetryButton.pressed.connect(_on_restart_pressed)
	$GameHost/GameViewport/CanvasLayer/GameOverScreen/Panel/VBox/MenuButton.pressed.connect(_on_menu_pressed)


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING


func _on_start_pressed() -> void:
	if _starting:
		return
	_laps = 0
	_begin_start_flow()


func _on_restart_pressed() -> void:
	if _starting:
		return
	_laps = 0
	_begin_start_flow()


func _on_menu_pressed() -> void:
	_clear_game()
	_starting = false
	_show_screen(GameStatus.START)


func _begin_start_flow() -> void:
	_starting = true
	ThemeSoundUtil.play(self, "interface", "confirm")
	_start_screen.visible = false
	_game_over_screen.visible = false
	_hud.visible = true
	_help_label.visible = true
	call_deferred("_start_game")


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


func set_lap_count(laps: int) -> void:
	_laps = laps
	_update_hud()


func update_race_hud(time_left: int, laps: int) -> void:
	_time_left = time_left
	_laps = laps
	_update_hud()


func on_time_up(laps: int) -> void:
	if _status != GameStatus.PLAYING:
		return
	_laps = laps
	_go_lap_label.text = "%d 圈" % laps
	if _game_scene != null and _game_scene.has_method("stop_game"):
		_game_scene.call("stop_game")
	_show_screen(GameStatus.GAMEOVER)
	ThemeSoundUtil.play(self, "interface", "back")


func _update_hud() -> void:
	_time_label.text = "%ds" % _time_left
	_lap_label.text = str(_laps)
	if _time_left <= 10:
		_time_label.add_theme_color_override("font_color", Color(1.0, 0.27, 0.0, 1.0))
		_time_label.scale = Vector2(1.08, 1.08)
	else:
		_time_label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 1.0))
		_time_label.scale = Vector2.ONE


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var key_event: InputEventKey = event as InputEventKey
		if key_event.pressed and not key_event.echo and key_event.keycode == KEY_F11:
			_toggle_fullscreen()


func _toggle_fullscreen() -> void:
	var current: DisplayServer.WindowMode = DisplayServer.window_get_mode()
	if current == DisplayServer.WINDOW_MODE_FULLSCREEN or current == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	call_deferred("_refit_display")
