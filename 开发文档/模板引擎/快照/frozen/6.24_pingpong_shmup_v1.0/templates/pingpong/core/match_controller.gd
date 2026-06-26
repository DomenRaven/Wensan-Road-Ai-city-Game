extends Node2D

const ScoreManagerClass := preload("res://core/score_manager.gd")
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const PongSheetUtil := preload("res://core/pong_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _score: ScoreManagerClass = ScoreManagerClass.new()
var _match_over: bool = false
var _serve_direction: int = -1
var _manager: Node2D = null
var _center_y: float = 200.0

@onready var _player_paddle: Area2D = $PlayerPaddle
@onready var _ai_paddle: Area2D = $AIPaddle
@onready var _ball: Area2D = $Ball
@onready var _court_bg: Sprite2D = $CourtBg
@onready var _center_line: Sprite2D = $CenterLine


func setup(manager: Node2D) -> void:
	_manager = manager


func _ready() -> void:
	_apply_theme()
	_setup_bounds()
	_score.configure(_read_points_to_win())
	_score.score_changed.connect(_on_score_changed)
	_score.match_won.connect(_on_match_won)
	_ball.scored.connect(_on_ball_scored)
	_update_hud()
	_set_paddles_active(false)
	_ball.halt()
	if _manager != null and _manager.has_method("play_countdown"):
		await _manager.play_countdown(3)
	if _match_over:
		return
	_set_paddles_active(true)
	_start_rally()


func stop_game() -> void:
	_match_over = true
	_ball.halt()
	_set_paddles_active(false)


func _set_paddles_active(active: bool) -> void:
	if _player_paddle.has_method("set_input_enabled"):
		_player_paddle.call("set_input_enabled", active)
	if _ai_paddle.has_method("set_ai_enabled"):
		_ai_paddle.call("set_ai_enabled", active)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_path: String = str(
		theme.get("court_bg_sprite", PongSheetUtil.theme_path("court_bg_sprite", "court_01.png"))
	)
	if bg_path != "":
		_court_bg.texture = ThemeSpriteUtil.load_texture(bg_path, Color(0.1, 0.45, 0.2), Vector2i(640, 360))
		_court_bg.visible = true
		var bg_size: Vector2 = _court_bg.texture.get_size()
		if bg_size.x > 0.0 and bg_size.y > 0.0:
			_court_bg.scale = Vector2(640.0 / bg_size.x, 360.0 / bg_size.y)
	var line_path: String = str(
		theme.get("court_center_line_sprite", PongSheetUtil.theme_path("court_center_line_sprite", "court_center_line.png"))
	)
	if line_path != "":
		_center_line.texture = ThemeSpriteUtil.load_texture(line_path, Color(1, 1, 1, 0.5), Vector2i(5, 300))
		_center_line.visible = true
		_center_line.modulate = Color(1, 1, 1, 0.5)
		var line_size: Vector2 = _center_line.texture.get_size()
		if line_size.x > 0.0 and line_size.y > 0.0:
			_center_line.scale = Vector2(10.0 / line_size.x, 304.0 / line_size.y)


func _setup_bounds() -> Rect2:
	var table_cfg: Dictionary = GameConfig.get_tuning().get("table", {}) as Dictionary
	var margin_x: float = float(table_cfg.get("margin_x", 12.0))
	var margin_top: float = float(table_cfg.get("margin_top", table_cfg.get("margin_y", 24.0)))
	var margin_bottom: float = float(table_cfg.get("margin_bottom", table_cfg.get("margin_y", 24.0)))
	var bounds: Rect2 = Rect2(
		margin_x,
		margin_top,
		640.0 - margin_x * 2.0,
		360.0 - margin_top - margin_bottom
	)
	var center_y: float = bounds.position.y + bounds.size.y * 0.5
	_center_y = center_y
	_player_paddle.configure_bounds(bounds.position.y, bounds.position.y + bounds.size.y)
	_ai_paddle.configure_bounds(bounds.position.y, bounds.position.y + bounds.size.y)
	var player_x: float = float(table_cfg.get("player_x", 30.0))
	var ai_x: float = float(table_cfg.get("ai_x", 610.0))
	_player_paddle.position = Vector2(player_x, center_y)
	_ai_paddle.position = Vector2(ai_x, center_y)
	_ai_paddle.setup_ai(_ball)
	_ball.configure(_player_paddle, _ai_paddle, bounds)
	return bounds


func _read_points_to_win() -> int:
	var rules_cfg: Dictionary = GameConfig.get_tuning().get("rules", {}) as Dictionary
	return int(rules_cfg.get("points_to_win", 5))


func _start_rally() -> void:
	if _match_over:
		return
	_ball.serve_toward(_serve_direction)


func _on_ball_scored(side: String) -> void:
	if _match_over:
		return
	ThemeSoundUtil.play(self, "impact", "score")
	if _manager != null and _manager.has_method("on_point_scored"):
		_manager.call("on_point_scored", side)
	if side == "player":
		_score.add_point_to_player()
		_serve_direction = -1
	else:
		_score.add_point_to_ai()
		_serve_direction = 1
	if _match_over:
		return
	_ball.reset_to_center(Vector2(320.0, _center_y))
	_reset_paddles()
	await get_tree().create_timer(1.0).timeout
	_start_rally()


func _reset_paddles() -> void:
	if _player_paddle.has_method("reset_to_center"):
		_player_paddle.call("reset_to_center", _center_y)
	if _ai_paddle.has_method("reset_to_center"):
		_ai_paddle.call("reset_to_center", _center_y)


func _on_score_changed(player_pts: int, ai_pts: int) -> void:
	_update_hud(player_pts, ai_pts)


func _update_hud(player_pts: int = _score.player_score, ai_pts: int = _score.ai_score) -> void:
	if _manager != null and _manager.has_method("update_match_hud"):
		_manager.call("update_match_hud", player_pts, ai_pts)


func _on_match_won(winner: String) -> void:
	_match_over = true
	_ball.halt()
	_set_paddles_active(false)
	if _manager != null and _manager.has_method("on_match_finished"):
		_manager.call(
			"on_match_finished",
			winner,
			_score.player_score,
			_score.ai_score
		)
