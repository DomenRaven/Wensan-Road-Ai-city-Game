extends Node2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const LapCounterScript := preload("res://core/lap_counter.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _manager: Node = null
var _round_duration: float = 90.0
var _time_left: int = 90
var _timer_accum: float = 0.0
var _is_playing: bool = false
var _game_over: bool = false
var _lap_distance: float = 10000.0
var _lap_counter = LapCounterScript.new()

@onready var _player: Node2D = $Player
@onready var _road: Node2D = $RoadScroller
@onready var _spawner: Node2D = $TrafficSpawner
@onready var _background: ColorRect = $Background


func setup(manager: Node) -> void:
	_manager = manager
	var player: Node2D = get_node_or_null("Player") as Node2D
	var road: Node2D = get_node_or_null("RoadScroller") as Node2D
	var spawner: Node2D = get_node_or_null("TrafficSpawner") as Node2D
	var background: ColorRect = get_node_or_null("Background") as ColorRect
	if player == null or road == null or spawner == null or background == null:
		push_error("TrackRunner: missing scene nodes")
		return
	_player = player
	_road = road
	_spawner = spawner
	_background = background
	_apply_tuning()
	_apply_theme()
	_setup_world()
	if not _lap_counter.lap_completed.is_connected(_on_lap_completed):
		_lap_counter.lap_completed.connect(_on_lap_completed)
	start_game()


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var round_cfg: Dictionary = tuning.get("round", {}) as Dictionary
	var track_cfg: Dictionary = tuning.get("track", {}) as Dictionary
	_round_duration = clampf(float(round_cfg.get("duration_sec", _round_duration)), 45.0, 120.0)
	_lap_distance = float(track_cfg.get("lap_distance_px", _lap_distance))
	_lap_counter.setup(_lap_distance, 999)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_color: String = str(theme.get("background_color", "#87CEEB"))
	_background.color = Color.from_string(bg_color, Color(0.53, 0.81, 0.92, 1.0))
	_background.offset_right = RacingViewportScript.WIDTH
	_background.offset_bottom = RacingViewportScript.HEIGHT


func _setup_world() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var track_path: String = str(theme.get("track_atlas", ""))
	var track_tex: Texture2D = ThemeSpriteUtil.load_texture(
		track_path,
		Color(0.35, 0.35, 0.38, 1.0),
		Vector2i(int(RacingViewportScript.WIDTH), int(RacingViewportScript.HEIGHT))
	)
	var tuning: Dictionary = GameConfig.get_tuning()
	var car_cfg: Dictionary = tuning.get("car", {}) as Dictionary
	var track_cfg: Dictionary = tuning.get("track", {}) as Dictionary
	var sprite_scale: float = float(car_cfg.get("sprite_scale", 0.14))
	var margin: float = float(track_cfg.get("margin_px", 50.0))
	var crop_ratio: float = float(track_cfg.get("atlas_crop_left_ratio", 0.5))
	var track_left: float = margin
	var track_right: float = RacingViewportScript.track_right(margin)
	if _road.has_method("setup"):
		_road.call("setup", track_tex, _background.color, crop_ratio)
	if _spawner.has_method("setup"):
		_spawner.call(
			"setup",
			track_left,
			track_right,
			sprite_scale,
			str(theme.get("npc_yellow_sprite", "")),
			str(theme.get("npc_blue_sprite", ""))
		)


func start_game() -> void:
	_is_playing = true
	_game_over = false
	_time_left = int(_round_duration)
	_timer_accum = 0.0
	_lap_counter.setup(_lap_distance, 999)
	if _player.has_method("setup_playing"):
		_player.call("setup_playing", true)
	if _spawner.has_method("reset_spawner"):
		_spawner.call("reset_spawner")
	if _spawner.has_method("set_active"):
		_spawner.call("set_active", true)
	_push_hud()


func stop_game() -> void:
	_is_playing = false
	if _player.has_method("set_game_over"):
		_player.call("set_game_over", true)
	if _spawner.has_method("set_active"):
		_spawner.call("set_active", false)


func _physics_process(delta: float) -> void:
	if not _is_playing or _game_over:
		return
	var scroll_speed: float = _get_scroll_speed()
	var scroll_delta: float = scroll_speed * delta
	_lap_counter.advance(scroll_delta)
	if _road.has_method("set_scroll_speed"):
		_road.call("set_scroll_speed", scroll_speed)
	if _spawner.has_method("process_spawner"):
		_spawner.call("process_spawner", delta, scroll_speed)
	if _spawner.has_method("set_lap_count"):
		_spawner.call("set_lap_count", _lap_counter.get_current_lap())
	_timer_accum += delta
	while _timer_accum >= 1.0:
		_time_left -= 1
		_timer_accum -= 1.0
		if _time_left <= 0:
			_push_hud()
			_end_game()
			return
	_push_hud()


func _get_scroll_speed() -> float:
	if _player != null and _player.has_method("get_forward_speed"):
		return float(_player.call("get_forward_speed"))
	return 0.0


func _on_lap_completed(lap_index: int) -> void:
	ThemeSoundUtil.play(self, "impact", "pass")
	if _manager != null and _manager.has_method("set_lap_count"):
		_manager.call("set_lap_count", lap_index)


func _end_game() -> void:
	if _game_over:
		return
	_game_over = true
	stop_game()
	if _manager != null and _manager.has_method("on_time_up"):
		_manager.call("on_time_up", _lap_counter.get_current_lap())


func _push_hud() -> void:
	if _manager == null:
		return
	if _manager.has_method("update_race_hud"):
		_manager.call("update_race_hud", _time_left, _lap_counter.get_current_lap())
