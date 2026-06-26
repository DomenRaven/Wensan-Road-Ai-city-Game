extends Node2D

const XP_GEM_SCENE: PackedScene = preload("res://scenes/xp_gem.tscn")
const BOSS_SCENE: PackedScene = preload("res://scenes/boss.tscn")
const SurvivorWorld := preload("res://core/survivor_world.gd")
const GEM_POOL_SIZE: int = 64

var _manager: Node = null
var _gem_pool: Array[Area2D] = []
var _session_duration: float = 180.0
var _elapsed: float = 0.0
var _boss_elapsed: float = 0.0
var _xp: int = 0
var _level: int = 1
var _xp_to_next: int = 100
var _game_over: bool = false
var _in_boss: bool = false
var _base_magnet_range: float = 64.0
var _xp_scale: float = 1.5
var _boss: Area2D = null
var _boss_timer: float = 0.0

@onready var _player: Area2D = $Player
@onready var _spawner: Node2D = $HordeSpawner
@onready var _gems_root: Node2D = $XpGems
@onready var _level_up_ui: CanvasLayer = $LevelUpUI
@onready var _background: Node2D = $Background
@onready var _boss_root: Node2D = $BossRoot
@onready var _camera: Camera2D = $Camera2D


func setup(manager: Node) -> void:
	_manager = manager
	var center: Vector2 = SurvivorWorld.get_center()
	_player.global_position = center
	if _camera.has_method("bind_target"):
		_camera.call("bind_target", _player)
	_build_gem_pool()
	_apply_tuning()
	_apply_theme()
	if _player.has_signal("hp_changed"):
		_player.hp_changed.connect(_on_player_hp_changed)
	if _player.has_signal("died"):
		_player.died.connect(_on_player_died)
	if _level_up_ui.has_signal("choice_selected"):
		_level_up_ui.choice_selected.connect(_on_level_choice)
	if _spawner.has_method("set_player_level"):
		_spawner.call("set_player_level", _level)


func _build_gem_pool() -> void:
	for _i: int in GEM_POOL_SIZE:
		var gem: Area2D = XP_GEM_SCENE.instantiate() as Area2D
		gem.visible = false
		gem.process_mode = Node.PROCESS_MODE_DISABLED
		_gems_root.add_child(gem)
		if gem.has_signal("collected"):
			gem.collected.connect(_on_gem_collected)
		_gem_pool.append(gem)


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var session_cfg: Dictionary = tuning.get("session", {}) as Dictionary
	var xp_cfg: Dictionary = tuning.get("xp", {}) as Dictionary
	_session_duration = float(session_cfg.get("duration_sec", _session_duration))
	_xp_to_next = int(xp_cfg.get("level_threshold_base", _xp_to_next))
	_xp_scale = float(xp_cfg.get("level_threshold_scale", _xp_scale))
	_base_magnet_range = float(xp_cfg.get("magnet_range", _base_magnet_range))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_color: String = str(theme.get("background_color", "#FDFBF7"))
	if _background != null and _background.has_method("apply_theme_color"):
		_background.call("apply_theme_color", bg_color)


func _physics_process(delta: float) -> void:
	if _game_over or get_tree().paused:
		return
	if _in_boss:
		_boss_elapsed += delta
		_boss_timer += delta
		if _boss_timer >= 1.0:
			_boss_timer = 0.0
			if _manager != null and _manager.has_method("increment_boss_time"):
				_manager.call("increment_boss_time")
	else:
		_elapsed += delta
		var ratio: float = maxf(0.0, (_session_duration - _elapsed) / maxf(1.0, _session_duration))
		if _spawner.has_method("set_time_remaining_ratio"):
			_spawner.call("set_time_remaining_ratio", ratio)
		if _elapsed >= _session_duration and _player.has_method("get_hp") and int(_player.call("get_hp")) > 0:
			_begin_boss_fight()
	_update_hud()


func _begin_boss_fight() -> void:
	if _in_boss:
		return
	_in_boss = true
	if _spawner.has_method("set_spawning_enabled"):
		_spawner.call("set_spawning_enabled", false)
	if _spawner.has_method("clear_all_enemies"):
		_spawner.call("clear_all_enemies")
	if _boss != null:
		_boss.queue_free()
	_boss = BOSS_SCENE.instantiate() as Area2D
	_boss_root.add_child(_boss)
	_boss.global_position = _player.global_position + Vector2(0.0, -120.0)
	if _boss.has_method("setup"):
		_boss.call("setup", _spawner)
	if _boss.has_signal("defeated"):
		_boss.defeated.connect(_on_boss_defeated)
	if _boss.has_signal("hp_changed"):
		_boss.hp_changed.connect(_on_boss_hp_changed)
	if _boss.has_method("get_current_hp") and _boss.has_method("get_max_hp"):
		_on_boss_hp_changed(int(_boss.call("get_current_hp")), int(_boss.call("get_max_hp")))
	if _manager != null and _manager.has_method("set_boss_bar_visible"):
		_manager.call("set_boss_bar_visible", true)
	if _manager != null and _manager.has_method("shake_screen"):
		_manager.call("shake_screen", 0.5, 4.0)


func spawn_xp_gem(pos: Vector2, value: int) -> void:
	var gem: Area2D = _acquire_gem()
	if gem == null:
		return
	gem.global_position = pos
	if gem.has_method("activate"):
		gem.call("activate", value, _base_magnet_range, 1.0)


func _acquire_gem() -> Area2D:
	for gem: Area2D in _gem_pool:
		if not gem.visible:
			return gem
	return null


func _on_gem_collected(value: int) -> void:
	if _player.has_method("get_hp") and int(_player.call("get_hp")) <= 0:
		return
	_xp += value
	while _xp >= _xp_to_next:
		_xp -= _xp_to_next
		_level += 1
		_xp_to_next = int(round(float(_xp_to_next) * _xp_scale))
		if _spawner.has_method("set_player_level"):
			_spawner.call("set_player_level", _level)
		if _level_up_ui.has_method("show_choices"):
			_level_up_ui.call("show_choices", _level)
			break
	_update_hud()


func _on_level_choice(choice_id: String) -> void:
	if _player.has_method("apply_level_choice"):
		_player.call("apply_level_choice", choice_id)
	if _in_boss and _boss != null and _boss.visible and _boss.has_method("full_heal"):
		_boss.call("full_heal")
		if _manager != null and _manager.has_method("show_boss_heal_toast"):
			_manager.call("show_boss_heal_toast")
		if _boss.has_method("get_current_hp") and _boss.has_method("get_max_hp"):
			_on_boss_hp_changed(int(_boss.call("get_current_hp")), int(_boss.call("get_max_hp")))


func _on_boss_hp_changed(current_hp: int, max_hp: int) -> void:
	if _manager != null and _manager.has_method("update_boss_bar"):
		_manager.call("update_boss_bar", current_hp, max_hp)


func _on_boss_defeated() -> void:
	if _game_over:
		return
	_game_over = true
	if _manager != null and _manager.has_method("shake_screen"):
		_manager.call("shake_screen", 0.8, 6.0)
	if _manager != null and _manager.has_method("on_session_won"):
		_manager.call("on_session_won", _level)


func _on_player_hp_changed(_current_hp: int, _max_hp: int) -> void:
	if _manager != null and _manager.has_method("update_hp"):
		_manager.call("update_hp", _current_hp, _max_hp)
	_update_hud()


func _on_player_died() -> void:
	if _game_over:
		return
	_game_over = true
	if _manager != null and _manager.has_method("on_player_died"):
		_manager.call("on_player_died")


func _update_hud() -> void:
	if _manager == null or not _manager.has_method("update_session_hud"):
		return
	var time_left: float = maxf(0.0, _session_duration - _elapsed)
	var current_hp: int = 0
	var max_hp: int = 0
	if _player.has_method("get_hp"):
		current_hp = int(_player.call("get_hp"))
	if _player.has_method("get_max_hp"):
		max_hp = int(_player.call("get_max_hp"))
	_manager.call(
		"update_session_hud",
		_level,
		_xp,
		_xp_to_next,
		time_left,
		"boss" if _in_boss else "survive",
		current_hp,
		max_hp,
		_in_boss
	)
