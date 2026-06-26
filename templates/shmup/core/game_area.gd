extends Node2D

const POWERUP_SCENE: PackedScene = preload("res://scenes/powerup.tscn")
const EXPLOSION_SCENE: PackedScene = preload("res://scenes/explosion_fx.tscn")

var _manager: Node = null

@onready var _player: Area2D = $Player
@onready var _spawner: Node2D = $EnemySpawner
@onready var _powerups_root: Node2D = $Powerups


func setup(manager: Node) -> void:
	_manager = manager
	var player: Area2D = get_node_or_null("Player") as Area2D
	var spawner: Node2D = get_node_or_null("EnemySpawner") as Node2D
	if player == null or spawner == null:
		push_error("GameArea: Player or EnemySpawner missing")
		return
	if player.has_signal("hp_changed"):
		player.hp_changed.connect(_on_player_hp_changed)
	if player.has_signal("died"):
		player.died.connect(_on_player_died)
	if spawner.has_signal("enemy_destroyed"):
		spawner.enemy_destroyed.connect(_on_enemy_destroyed)
	if spawner.has_signal("request_powerup"):
		spawner.request_powerup.connect(_on_request_powerup)
	if spawner.has_signal("boss_state_changed"):
		spawner.boss_state_changed.connect(_on_boss_state_changed)
	if spawner.has_signal("boss_hp_changed"):
		spawner.boss_hp_changed.connect(_on_boss_hp_changed)
	if player.has_method("set_playing"):
		player.call("set_playing", true)
	if spawner.has_method("setup"):
		spawner.call("setup", manager)
	if spawner.has_method("set_spawning"):
		spawner.call("set_spawning", true)
	var camera: Camera2D = get_node_or_null("Camera2D") as Camera2D
	if camera != null:
		camera.make_current()


func stop_game() -> void:
	if _player.has_method("set_playing"):
		_player.call("set_playing", false)
	if _spawner.has_method("set_spawning"):
		_spawner.call("set_spawning", false)


func _on_player_hp_changed(_current_hp: int, _max_hp: int) -> void:
	pass


func _on_player_died() -> void:
	_spawn_explosion(_player.global_position, 2.0)
	if _manager != null and _manager.has_method("shake_camera"):
		_manager.call("shake_camera")
	if _manager != null and _manager.has_method("on_player_died"):
		_manager.call("on_player_died")


func _on_enemy_destroyed(score_value: int, _enemy: Area2D) -> void:
	if _manager != null and _manager.has_method("add_score"):
		_manager.call("add_score", score_value)


func _on_boss_state_changed(active: bool) -> void:
	if _manager != null and _manager.has_method("set_boss_bar_visible"):
		_manager.call("set_boss_bar_visible", active)


func _on_boss_hp_changed(current_hp: int, max_hp: int) -> void:
	if _manager != null and _manager.has_method("update_boss_hp"):
		_manager.call("update_boss_hp", current_hp, max_hp)


func _on_request_powerup(spawn_pos: Vector2, count: int) -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var types: Array = tuning.get("powerup_types", []) as Array
	if types.is_empty():
		return
	var power_cfg: Dictionary = tuning.get("powerup", {}) as Dictionary
	var speed: float = float(power_cfg.get("fall_speed", 100.0))
	for i: int in count:
		var entry: Dictionary = types[randi() % types.size()] as Dictionary
		var pickup: Area2D = POWERUP_SCENE.instantiate() as Area2D
		var offset_x: float = float(i - (count - 1)) * 30.0
		pickup.position = spawn_pos + Vector2(offset_x, 0.0)
		if pickup.has_signal("collected"):
			pickup.collected.connect(_on_powerup_collected)
		_powerups_root.add_child(pickup)
		if pickup.has_method("configure"):
			pickup.call(
				"configure",
				str(entry.get("name", "")),
				int(entry.get("frame", 0)),
				speed
			)


func _on_powerup_collected(_pickup: Area2D, powerup_name: String) -> void:
	if _player.has_method("apply_powerup"):
		_player.call("apply_powerup", powerup_name)


func _spawn_explosion(pos: Vector2, scale_factor: float) -> void:
	var fx: Node2D = EXPLOSION_SCENE.instantiate() as Node2D
	add_child(fx)
	if fx.has_method("setup"):
		fx.call("setup", pos, scale_factor)
