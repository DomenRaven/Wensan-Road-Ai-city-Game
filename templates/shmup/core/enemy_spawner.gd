extends Node2D

signal enemy_destroyed(score_value: int, enemy: Area2D)
signal request_powerup(spawn_pos: Vector2, count: int)
signal boss_state_changed(active: bool)
signal boss_hp_changed(current_hp: int, max_hp: int)

const ENEMY_SCENE: PackedScene = preload("res://scenes/enemy.tscn")
const EXPLOSION_SCENE: PackedScene = preload("res://scenes/explosion_fx.tscn")

var _spawn_delay_ms: int = 1500
var _min_spawn_delay_ms: int = 500
var _spawn_timer: float = 0.0
var _active: bool = false
var _is_boss_active: bool = false
var _next_boss_score: int = 500
var _boss_score_step: int = 1000
var _manager: Node = null
var _current_boss: Area2D = null

@onready var _enemies_root: Node2D = $Enemies


func _ready() -> void:
	_apply_tuning()


func setup(manager: Node) -> void:
	_manager = manager


func set_spawning(active: bool) -> void:
	_active = active


func is_boss_active() -> bool:
	return _is_boss_active


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var spawn_cfg: Dictionary = tuning.get("spawn", {}) as Dictionary
	var boss_cfg: Dictionary = tuning.get("boss", {}) as Dictionary
	_spawn_delay_ms = int(spawn_cfg.get("interval_ms", _spawn_delay_ms))
	_min_spawn_delay_ms = int(spawn_cfg.get("min_interval_ms", _min_spawn_delay_ms))
	_next_boss_score = int(boss_cfg.get("first_score", _next_boss_score))
	_boss_score_step = int(boss_cfg.get("score_step", _boss_score_step))


func _process(delta: float) -> void:
	if not _active:
		return
	_try_spawn_boss()
	if _is_boss_active:
		return
	_spawn_timer += delta
	var delay_sec: float = float(_spawn_delay_ms) / 1000.0
	if _spawn_timer >= delay_sec:
		_spawn_timer = 0.0
		_spawn_random_enemy()
		if _spawn_delay_ms > _min_spawn_delay_ms:
			_spawn_delay_ms = maxi(_min_spawn_delay_ms, _spawn_delay_ms - 10)


func _get_score() -> int:
	if _manager != null and _manager.has_method("get_score"):
		return int(_manager.call("get_score"))
	return 0


func _try_spawn_boss() -> void:
	if _is_boss_active:
		return
	if _get_score() < _next_boss_score:
		return
	_spawn_boss()
	_next_boss_score += _boss_score_step


func _spawn_random_enemy() -> void:
	var roll: float = randf()
	var type_id: String = "normal"
	if roll > 0.9:
		type_id = "heavy"
	elif roll > 0.6:
		type_id = "fast"
	_spawn_enemy(type_id, Vector2(randf_range(48.0, 592.0), -40.0))


func _spawn_boss() -> void:
	_is_boss_active = true
	boss_state_changed.emit(true)
	var boss: Area2D = _spawn_enemy("boss", Vector2(320.0, -100.0), true)
	_current_boss = boss


func _spawn_enemy(type_id: String, spawn_pos: Vector2, is_boss_spawn: bool = false) -> Area2D:
	var enemy: Area2D = ENEMY_SCENE.instantiate() as Area2D
	enemy.position = spawn_pos
	if enemy.has_signal("destroyed"):
		enemy.destroyed.connect(_on_enemy_destroyed)
	if enemy.has_signal("request_fan_shot"):
		enemy.request_fan_shot.connect(_on_enemy_fan_shot)
	if enemy.has_signal("boss_hp_changed"):
		enemy.boss_hp_changed.connect(_on_boss_hp_changed)
	_enemies_root.add_child(enemy)
	if enemy.has_method("configure"):
		enemy.call("configure", type_id, is_boss_spawn)
	return enemy


func _on_enemy_destroyed(enemy: Area2D, score_value: int, drop_rate: float, is_boss: bool) -> void:
	_spawn_explosion(enemy.global_position, 2.0 if is_boss else 1.0)
	enemy_destroyed.emit(score_value, enemy)
	if is_boss:
		request_powerup.emit(enemy.global_position, 3)
		_clear_boss()
	elif randf() <= drop_rate:
		request_powerup.emit(enemy.global_position, 1)


func _clear_boss() -> void:
	_is_boss_active = false
	_current_boss = null
	boss_state_changed.emit(false)


func _on_boss_hp_changed(current_hp: int, max_hp: int) -> void:
	boss_hp_changed.emit(current_hp, max_hp)


func _on_enemy_fan_shot(origin: Vector2) -> void:
	var pool: Node2D = get_tree().get_first_node_in_group("bullet_pool") as Node2D
	if pool == null or not pool.has_method("spawn_enemy_bullet_fan"):
		return
	var tuning: Dictionary = GameConfig.get_tuning()
	var bullet_speed: float = float((tuning.get("enemy", {}) as Dictionary).get("bullet_speed", 300.0))
	pool.call("spawn_enemy_bullet_fan", origin + Vector2(0.0, 50.0), bullet_speed)


func _spawn_explosion(pos: Vector2, scale_factor: float) -> void:
	var fx: Node2D = EXPLOSION_SCENE.instantiate() as Node2D
	_enemies_root.get_parent().add_child(fx)
	if fx.has_method("setup"):
		fx.call("setup", pos, scale_factor)
