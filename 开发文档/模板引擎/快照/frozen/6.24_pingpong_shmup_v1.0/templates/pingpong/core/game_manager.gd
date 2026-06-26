extends Node2D

enum GameStatus { START, PLAYING, GAMEOVER }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")
const PongSheetUtil := preload("res://core/pong_sheet.gd")
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")

var _status: GameStatus = GameStatus.START
var _starting: bool = false
var _game_scene: Node2D = null
var _again_pulse_tween: Tween = null

@onready var _game_root: Node2D = $GameRoot
@onready var _hud: Control = $CanvasLayer/HUD
@onready var _player_score_label: Label = $CanvasLayer/HUD/PlayerScore
@onready var _ai_score_label: Label = $CanvasLayer/HUD/AIScore
@onready var _help_label: Label = $CanvasLayer/HUD/HelpLabel
@onready var _start_screen: Control = $CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _start_btn_sprite: TextureRect = $CanvasLayer/StartScreen/StartButton
@onready var _countdown_label: Label = $CanvasLayer/HUD/CountdownLabel
@onready var _result_sprite: TextureRect = $CanvasLayer/GameOverScreen/Panel/ResultImage
@onready var _board_sprite: TextureRect = $CanvasLayer/GameOverScreen/Panel/BoardImage
@onready var _final_score_label: Label = $CanvasLayer/GameOverScreen/Panel/FinalScore
@onready var _start_bg: TextureRect = $CanvasLayer/StartScreen/BackgroundImage
@onready var _end_bg: TextureRect = $CanvasLayer/GameOverScreen/BackgroundImage


func _ready() -> void:
	_apply_ui_theme()
	$CanvasLayer/StartScreen/StartButton.mouse_filter = Control.MOUSE_FILTER_STOP
	$CanvasLayer/GameOverScreen/Panel/AgainButton.mouse_filter = Control.MOUSE_FILTER_STOP
	_show_screen(GameStatus.START)
	_wire_buttons()
	_player_score_label.pivot_offset = Vector2(30.0, 18.0)
	_ai_score_label.pivot_offset = Vector2(30.0, 18.0)
	_countdown_label.pivot_offset = Vector2(80.0, 48.0)
	call_deferred("_warmup_assets")
	call_deferred("_start_button_pulse")


func _warmup_assets() -> void:
	PongSheetUtil.warmup()


func _start_button_pulse() -> void:
	if _start_btn_sprite == null:
		return
	_start_btn_sprite.pivot_offset = Vector2(72.0, 25.0)
	var tween: Tween = create_tween()
	tween.set_loops()
	tween.tween_property(_start_btn_sprite, "scale", Vector2(1.05, 1.05), 0.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_property(_start_btn_sprite, "scale", Vector2.ONE, 0.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _apply_ui_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_path: String = str(
		theme.get("court_bg_sprite", PongSheetUtil.theme_path("court_bg_sprite", "court_01.png"))
	)
	if bg_path != "":
		var bg_tex: Texture2D = ThemeSpriteUtil.load_texture(bg_path, Color(0.1, 0.45, 0.2), Vector2i(640, 360))
		_start_bg.texture = bg_tex
		_end_bg.texture = bg_tex
	var btn_path: String = str(
		theme.get("btn_start_sprite", PongSheetUtil.theme_path("btn_start_sprite", "btn_menu_h_start.png"))
	)
	if btn_path != "":
		_start_btn_sprite.texture = ThemeSpriteUtil.load_texture(btn_path, Color(0.2, 0.8, 0.3), Vector2i(145, 50))
	var board_path: String = str(
		theme.get("board_sprite", PongSheetUtil.theme_path("board_sprite", "board.png"))
	)
	if board_path != "":
		_board_sprite.texture = ThemeSpriteUtil.load_texture(board_path, Color(0.15, 0.15, 0.2), Vector2i(205, 162))
	_update_help_text()


func _wire_buttons() -> void:
	$CanvasLayer/StartScreen/StartButton.gui_input.connect(_on_start_button_input)
	$CanvasLayer/GameOverScreen/Panel/AgainButton.gui_input.connect(_on_again_button_input)
	$CanvasLayer/GameOverScreen/Panel/MenuButton.pressed.connect(_on_menu_pressed)


func _on_start_button_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse: InputEventMouseButton = event as InputEventMouseButton
		if mouse.pressed and mouse.button_index == MOUSE_BUTTON_LEFT:
			_on_start_pressed()


func _on_again_button_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse: InputEventMouseButton = event as InputEventMouseButton
		if mouse.pressed and mouse.button_index == MOUSE_BUTTON_LEFT:
			_on_restart_pressed()


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING


func _on_start_pressed() -> void:
	if _starting:
		return
	_begin_start_flow()


func _on_restart_pressed() -> void:
	if _starting:
		return
	_begin_start_flow()


func _begin_start_flow() -> void:
	_stop_again_pulse()
	_reset_end_screen_visuals()
	_game_root.position = Vector2.ZERO
	_starting = true
	_start_screen.visible = false
	_game_over_screen.visible = false
	_hud.visible = true
	_help_label.visible = true
	update_match_hud(0, 0)
	call_deferred("_start_game")


func _on_menu_pressed() -> void:
	_stop_again_pulse()
	_clear_game()
	_game_root.position = Vector2.ZERO
	_starting = false
	_show_screen(GameStatus.START)


func _start_game() -> void:
	_clear_game()
	_load_game()
	_status = GameStatus.PLAYING
	_starting = false
	update_match_hud(0, 0)


func _clear_game() -> void:
	_stop_again_pulse()
	for child: Node in _game_root.get_children():
		_game_root.remove_child(child)
		child.queue_free()
	_game_scene = null


func _load_game() -> void:
	_game_scene = GAME_SCENE.instantiate() as Node2D
	if _game_scene.has_method("setup"):
		_game_scene.setup(self)
	_game_root.add_child(_game_scene)


func is_playing() -> bool:
	return _status == GameStatus.PLAYING


func _update_help_text() -> void:
	var pts: int = int(GameConfig.get_tuning().get("rules", {}).get("points_to_win", 5))
	_help_label.text = "↑ ↓ 移动球拍 · 先 %d 分胜" % pts


func play_countdown(seconds: int = 3) -> void:
	if _countdown_label == null:
		return
	_countdown_label.visible = true
	_countdown_label.z_index = 100
	_countdown_label.modulate = Color.WHITE
	_countdown_label.scale = Vector2.ONE
	for remaining: int in range(seconds, 0, -1):
		_countdown_label.text = str(remaining)
		_countdown_label.scale = Vector2(1.4, 1.4)
		var tick: Tween = create_tween()
		tick.tween_property(_countdown_label, "scale", Vector2.ONE, 0.35) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		await get_tree().create_timer(1.0).timeout
	_countdown_label.text = "开始!"
	_countdown_label.scale = Vector2(1.3, 1.3)
	var go: Tween = create_tween()
	go.tween_property(_countdown_label, "scale", Vector2.ONE, 0.25) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await get_tree().create_timer(0.45).timeout
	_countdown_label.visible = false


func update_match_hud(player_pts: int, ai_pts: int) -> void:
	_player_score_label.text = str(player_pts)
	_ai_score_label.text = str(ai_pts)


func on_point_scored(side: String) -> void:
	_game_root.position = Vector2.ZERO
	var label: Label = _player_score_label if side == "player" else _ai_score_label
	if label == null:
		return
	var pulse: Tween = create_tween()
	pulse.tween_property(label, "scale", Vector2(1.5, 1.5), 0.1).set_trans(Tween.TRANS_SINE)
	pulse.tween_property(label, "scale", Vector2.ONE, 0.1).set_trans(Tween.TRANS_SINE)
	if _game_root == null:
		return
	var shake: Tween = create_tween()
	shake.tween_property(_game_root, "position", Vector2(3.0, -2.0), 0.033)
	shake.tween_property(_game_root, "position", Vector2(-2.0, 2.0), 0.033)
	shake.tween_property(_game_root, "position", Vector2.ZERO, 0.034)


func on_match_finished(winner: String, player_pts: int, ai_pts: int) -> void:
	if _game_scene != null and _game_scene.has_method("stop_game"):
		_game_scene.call("stop_game")
	var theme: Dictionary = GameConfig.get_theme()
	var win_path: String = str(
		theme.get("text_win_sprite", PongSheetUtil.theme_path("text_win_sprite", "text_win.png"))
	)
	var lose_path: String = str(
		theme.get("text_lose_sprite", PongSheetUtil.theme_path("text_lose_sprite", "text_lose.png"))
	)
	var result_path: String = win_path if winner == "player" else lose_path
	if result_path != "":
		_result_sprite.texture = ThemeSpriteUtil.load_texture(result_path, Color(1, 0.9, 0.2), Vector2i(185, 48))
	_final_score_label.text = "%d - %d" % [player_pts, ai_pts]
	var again_path: String = str(
		theme.get("btn_again_sprite", PongSheetUtil.theme_path("btn_again_sprite", "btn_round_again.png"))
	)
	var again_btn: TextureRect = $CanvasLayer/GameOverScreen/Panel/AgainButton as TextureRect
	if again_path != "" and again_btn != null:
		again_btn.texture = ThemeSpriteUtil.load_texture(again_path, Color(0.3, 0.8, 0.4), Vector2i(87, 87))
	_prepare_end_screen_anim()
	await get_tree().create_timer(1.0).timeout
	_show_screen(GameStatus.GAMEOVER)
	_play_end_screen_enter()


func _get_again_button() -> TextureRect:
	return $CanvasLayer/GameOverScreen/Panel/AgainButton as TextureRect


func _prepare_end_screen_anim() -> void:
	_board_sprite.pivot_offset = Vector2(102.0, 81.0)
	_result_sprite.pivot_offset = Vector2(92.0, 24.0)
	_board_sprite.scale = Vector2.ZERO
	_result_sprite.scale = Vector2.ZERO
	_final_score_label.modulate.a = 0.0
	var again_btn: TextureRect = _get_again_button()
	if again_btn != null:
		again_btn.pivot_offset = Vector2(44.0, 44.0)
		again_btn.scale = Vector2.ONE
		again_btn.modulate.a = 0.0


func _reset_end_screen_visuals() -> void:
	_board_sprite.scale = Vector2.ONE
	_result_sprite.scale = Vector2.ONE
	_final_score_label.modulate.a = 1.0
	var again_btn: TextureRect = _get_again_button()
	if again_btn != null:
		again_btn.scale = Vector2.ONE
		again_btn.modulate.a = 1.0


func _play_end_screen_enter() -> void:
	var enter: Tween = create_tween()
	enter.set_parallel(true)
	enter.tween_property(_board_sprite, "scale", Vector2.ONE, 0.6) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	enter.tween_property(_result_sprite, "scale", Vector2.ONE, 0.6) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await enter.finished
	var reveal: Tween = create_tween()
	reveal.set_parallel(true)
	reveal.tween_property(_final_score_label, "modulate:a", 1.0, 0.4) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	var again_btn: TextureRect = _get_again_button()
	if again_btn != null:
		reveal.tween_property(again_btn, "modulate:a", 1.0, 0.4) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	await reveal.finished
	_start_again_pulse()


func _start_again_pulse() -> void:
	var again_btn: TextureRect = _get_again_button()
	if again_btn == null:
		return
	_stop_again_pulse()
	again_btn.pivot_offset = Vector2(44.0, 44.0)
	_again_pulse_tween = create_tween()
	_again_pulse_tween.set_loops()
	_again_pulse_tween.tween_property(again_btn, "scale", Vector2(1.1, 1.1), 0.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_again_pulse_tween.tween_property(again_btn, "scale", Vector2.ONE, 0.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _stop_again_pulse() -> void:
	if _again_pulse_tween != null:
		_again_pulse_tween.kill()
		_again_pulse_tween = null


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		if _status == GameStatus.START:
			_on_start_pressed()
		elif _status == GameStatus.GAMEOVER:
			_on_restart_pressed()
