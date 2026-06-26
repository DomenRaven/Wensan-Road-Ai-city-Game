extends Node2D

const PROJECTILE_SCENE: PackedScene = preload("res://scenes/projectile.tscn")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _projectile_speed: float = 400.0
var _spread_rad: float = deg_to_rad(15.0)
var _fire_timer: float = 0.0

@onready var _pool_root: Node2D = get_tree().get_first_node_in_group("projectile_pool")


func _ready() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var weapon_cfg: Dictionary = tuning.get("weapon", {}) as Dictionary
	_projectile_speed = float(weapon_cfg.get("projectile_speed", _projectile_speed))
	_spread_rad = deg_to_rad(float(weapon_cfg.get("spread_deg", 15.0)))


func _physics_process(delta: float) -> void:
	var player: Node = get_parent()
	if player == null or not player.has_method("get_attack_interval_ms"):
		return
	_fire_timer += delta
	var interval_sec: float = float(player.call("get_attack_interval_ms")) / 1000.0
	if _fire_timer < interval_sec:
		return
	_fire_timer = 0.0
	_fire_bullets(player)


func _fire_bullets(player: Node) -> void:
	if _pool_root == null:
		return
	var count: int = int(player.call("get_multishot_count"))
	var damage: int = int(player.call("get_attack_damage"))
	var base_angle: float = float(player.call("get_shoot_angle"))
	var start_angle: float = base_angle - ((float(count) - 1.0) / 2.0) * _spread_rad
	for i: int in count:
		var angle: float = start_angle + float(i) * _spread_rad
		var direction: Vector2 = Vector2(cos(angle), sin(angle))
		var projectile: Area2D = _acquire_projectile()
		if projectile == null or not projectile.has_method("activate"):
			continue
		projectile.call("activate", (player as Node2D).global_position, direction, _projectile_speed, damage)
	ThemeSoundUtil.play(self, "impact", "shoot")


func _acquire_projectile() -> Area2D:
	for child: Node in _pool_root.get_children():
		if child is Area2D and not child.visible:
			return child as Area2D
	var projectile: Area2D = PROJECTILE_SCENE.instantiate() as Area2D
	_pool_root.add_child(projectile)
	return projectile
