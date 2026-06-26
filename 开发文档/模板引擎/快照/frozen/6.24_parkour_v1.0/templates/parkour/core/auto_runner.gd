extends Node2D

const CollectibleScript := preload("res://core/collectible.gd")
const ParkourTexturesUtil := preload("res://core/parkour_textures.gd")

const DAY_COLOR: Color = Color("87ceeb")
const NIGHT_COLOR: Color = Color("0f172a")
const BG_TRANSITION_SEC: float = 120.0

var _manager: Node = null
var _runner_speed: float = 300.0
var _speed_accel: float = 5.0
var _elapsed: float = 0.0
var _distance_m: float = 0.0
var _coins: int = 0
var _invincible_ms: float = 0.0
var _double_coin_ms: float = 0.0
var _invincible_duration_ms: float = 5000.0
var _double_coin_duration_ms: float = 8000.0
var _game_over: bool = false
var _playing: bool = false
var _skill_tick: float = 0.0
var _pending_over: bool = false

@onready var _player: CharacterBody2D = $Player
@onready var _scroll_world: Node2D = $ScrollWorld
@onready var _cloud_layer: Node2D = $CloudLayer
@onready var _spawner: Node2D = $ObstacleSpawner
@onready var _collectibles: Node2D = $CollectibleSpawner
@onready var _background: ColorRect = $Background


func setup(manager: Node) -> void:
	_manager = manager
	_player = get_node_or_null("Player") as CharacterBody2D
	_spawner = get_node_or_null("ObstacleSpawner") as Node2D
	_collectibles = get_node_or_null("CollectibleSpawner") as Node2D
	_cloud_layer = get_node_or_null("CloudLayer") as Node2D
	_apply_tuning()
	_apply_theme()
	_setup_world()
	if _spawner != null and _spawner.has_signal("obstacle_hit_player"):
		if not _spawner.obstacle_hit_player.is_connected(_on_obstacle_hit_player):
			_spawner.obstacle_hit_player.connect(_on_obstacle_hit_player)
	if _collectibles != null and _collectibles.has_signal("collectible_collected"):
		if not _collectibles.collectible_collected.is_connected(_on_collectible_collected):
			_collectibles.collectible_collected.connect(_on_collectible_collected)
	if _player != null and _player.has_signal("run_hit_finished"):
		if not _player.run_hit_finished.is_connected(_on_player_hit_finished):
			_player.run_hit_finished.connect(_on_player_hit_finished)


func start_run() -> void:
	_elapsed = 0.0
	_distance_m = 0.0
	_coins = 0
	_invincible_ms = 0.0
	_double_coin_ms = 0.0
	_runner_speed = _get_start_speed()
	_game_over = false
	_pending_over = false
	_playing = true
	_skill_tick = 0.0
	_background.color = DAY_COLOR
	if _player != null:
		if _player.has_method("set_playing"):
			_player.call("set_playing", true)
		if _player.has_method("set_invincible"):
			_player.call("set_invincible", false)
	if _spawner != null:
		if _spawner.has_method("clear_all"):
			_spawner.call("clear_all")
		if _spawner.has_method("start_spawning"):
			_spawner.call("start_spawning")
	if _collectibles != null:
		if _collectibles.has_method("clear_all"):
			_collectibles.call("clear_all")
		if _collectibles.has_method("start_spawning"):
			_collectibles.call("start_spawning")
	_update_hud()


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var runner_cfg: Dictionary = tuning.get("runner", {}) as Dictionary
	var skills_cfg: Dictionary = tuning.get("skills", {}) as Dictionary
	var inv_cfg: Dictionary = skills_cfg.get("invincible", {}) as Dictionary
	var dbl_cfg: Dictionary = skills_cfg.get("double_coin", {}) as Dictionary
	_runner_speed = float(runner_cfg.get("speed", _runner_speed))
	_speed_accel = float(runner_cfg.get("speed_accel", _speed_accel))
	_invincible_duration_ms = float(inv_cfg.get("duration_ms", _invincible_duration_ms))
	_double_coin_duration_ms = float(dbl_cfg.get("duration_ms", _double_coin_duration_ms))


func _get_start_speed() -> float:
	var tuning: Dictionary = GameConfig.get_tuning()
	var runner_cfg: Dictionary = tuning.get("runner", {}) as Dictionary
	return clampf(float(runner_cfg.get("speed", 300.0)), 160.0, 360.0)


func _apply_theme() -> void:
	_background.color = DAY_COLOR


func _setup_world() -> void:
	var ground_tex: Texture2D = ParkourTexturesUtil.get_ground_texture()
	var scroll_world: Node2D = get_node_or_null("ScrollWorld") as Node2D
	if scroll_world != null and scroll_world.has_method("setup"):
		scroll_world.call("setup", _runner_speed, ground_tex)
	var cloud_layer: Node2D = get_node_or_null("CloudLayer") as Node2D
	if cloud_layer != null and cloud_layer.has_method("setup"):
		cloud_layer.call("setup")
	var tuning: Dictionary = GameConfig.get_tuning()
	var obstacle_cfg: Dictionary = tuning.get("obstacle", {}) as Dictionary
	var collectible_cfg: Dictionary = tuning.get("collectible", {}) as Dictionary
	var min_obs_ms: float = float(obstacle_cfg.get("min_gap_ms", 2000.0))
	var max_obs_ms: float = float(obstacle_cfg.get("max_gap_ms", 4000.0))
	var min_col_ms: float = float(collectible_cfg.get("min_gap_ms", 1500.0))
	var max_col_ms: float = float(collectible_cfg.get("max_gap_ms", 3500.0))
	if _spawner != null and _spawner.has_method("setup"):
		_spawner.call("setup", _runner_speed, min_obs_ms, max_obs_ms)
	if _collectibles != null and _collectibles.has_method("setup"):
		_collectibles.call("setup", _runner_speed, min_col_ms, max_col_ms)


func _physics_process(delta: float) -> void:
	if not _playing or _game_over:
		return
	_elapsed += delta
	_distance_m += _runner_speed * delta / 10.0
	_runner_speed += _speed_accel * delta
	_skill_tick += delta
	if _skill_tick >= 0.1:
		_skill_tick = 0.0
		_tick_skills(100.0)
	_update_background()
	var scroll_world: Node2D = get_node_or_null("ScrollWorld") as Node2D
	if scroll_world != null and scroll_world.has_method("set_scroll_speed"):
		scroll_world.call("set_scroll_speed", _runner_speed)
	if _cloud_layer != null and _cloud_layer.has_method("set_scroll_speed"):
		_cloud_layer.call("set_scroll_speed", _runner_speed)
	if _spawner != null and _spawner.has_method("set_scroll_speed"):
		_spawner.call("set_scroll_speed", _runner_speed)
	if _collectibles != null and _collectibles.has_method("set_scroll_speed"):
		_collectibles.call("set_scroll_speed", _runner_speed)
	_update_hud()


func _tick_skills(delta_ms: float) -> void:
	if _invincible_ms > 0.0:
		_invincible_ms = maxf(0.0, _invincible_ms - delta_ms)
		if _invincible_ms <= 0.0 and _player != null and _player.has_method("set_invincible"):
			_player.call("set_invincible", false)
	if _double_coin_ms > 0.0:
		_double_coin_ms = maxf(0.0, _double_coin_ms - delta_ms)


func _update_background() -> void:
	var progress: float = clampf(_elapsed / BG_TRANSITION_SEC, 0.0, 1.0)
	_background.color = DAY_COLOR.lerp(NIGHT_COLOR, progress)


func _on_obstacle_hit_player() -> void:
	if _invincible_ms > 0.0:
		return
	_finish_game()


func _on_collectible_collected(kind: int) -> void:
	if not _playing or _game_over:
		return
	if kind == CollectibleScript.CollectibleKind.COIN:
		var amount: int = 2 if _double_coin_ms > 0.0 else 1
		_coins += amount
	elif kind == CollectibleScript.CollectibleKind.INVINCIBLE:
		_invincible_ms = _invincible_duration_ms
		if _player != null and _player.has_method("set_invincible"):
			_player.call("set_invincible", true)
	elif kind == CollectibleScript.CollectibleKind.DOUBLE_COIN:
		_double_coin_ms = _double_coin_duration_ms
	_update_hud()


func _finish_game() -> void:
	if _game_over or _pending_over:
		return
	_pending_over = true
	_playing = false
	_game_over = true
	if _spawner != null and _spawner.has_method("set_game_over"):
		_spawner.call("set_game_over", true)
	if _collectibles != null and _collectibles.has_method("set_game_over"):
		_collectibles.call("set_game_over", true)
	if _player != null and _player.has_method("set_game_over"):
		_player.call("set_game_over", true)
	else:
		_notify_manager()


func _on_player_hit_finished() -> void:
	_notify_manager()


func _notify_manager() -> void:
	if _manager != null and _manager.has_method("on_run_over"):
		_manager.call(
			"on_run_over",
			int(_distance_m),
			int(_elapsed),
			_coins
		)


func get_distance_meters() -> int:
	return int(_distance_m)


func get_survival_seconds() -> int:
	return int(_elapsed)


func get_coins() -> int:
	return _coins


func get_invincible_ms() -> float:
	return _invincible_ms


func get_double_coin_ms() -> float:
	return _double_coin_ms


func _update_hud() -> void:
	if _manager == null or not _manager.has_method("update_run_hud"):
		return
	_manager.call(
		"update_run_hud",
		get_distance_meters(),
		get_survival_seconds(),
		_coins,
		_invincible_ms,
		_double_coin_ms
	)
