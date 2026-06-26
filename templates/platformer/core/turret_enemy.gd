extends CharacterBody2D

## 红怪：固定于管道/砖块 · 每 2.5s 向左发射光球 · 踩头同普通怪
const RED_COLOR: Color = Color(0.88, 0.12, 0.12, 1.0)
const BODY_HALF_W: float = 14.0
const BODY_H: float = 24.0
const ORB_SCENE: PackedScene = preload("res://scenes/enemy_orb.tscn")
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")

var _alive: bool = true
var _fire_interval: float = 2.5
var _orb_speed: float = 80.0
var _orb_lifetime: float = 5.0
var _fire_timer: float = 0.0
var _gravity: float = 800.0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _muzzle: Marker2D = $Muzzle


func _ready() -> void:
	add_to_group("enemy")
	_apply_tuning()
	_apply_theme()
	_fire_timer = _fire_interval * 0.5


func configure_anchor(anchor: Vector2) -> void:
	global_position = anchor


func get_half_width() -> float:
	return BODY_HALF_W


func get_body_height() -> float:
	return BODY_H


func is_stompable() -> bool:
	return _alive


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var turret_cfg: Dictionary = types_cfg.get("turret", {}) as Dictionary
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	_fire_interval = float(turret_cfg.get("fire_interval", _fire_interval))
	_orb_speed = float(turret_cfg.get("orb_speed", _orb_speed))
	_orb_lifetime = float(turret_cfg.get("orb_lifetime", _orb_lifetime))
	_gravity = float(physics_cfg.get("gravity", _gravity))


func _apply_theme() -> void:
	_sprite.texture = ThemeSpriteUtil.load_texture("", RED_COLOR, Vector2i(32, 32))
	_sprite.centered = true
	_sprite.position = Vector2(0.0, -16.0)


func snap_to_floor() -> void:
	velocity = Vector2.ZERO
	move_and_slide()


func _physics_process(delta: float) -> void:
	if not _alive:
		return
	if not is_on_floor():
		velocity.y += _gravity * delta
	else:
		velocity.y = 0.0
	move_and_slide()
	_fire_timer -= delta
	if _fire_timer <= 0.0:
		_fire_timer = _fire_interval
		_fire_orb()


func _fire_orb() -> void:
	var orb: Area2D = ORB_SCENE.instantiate() as Area2D
	var spawn_pos: Vector2 = _muzzle.global_position if _muzzle != null else global_position
	orb.global_position = spawn_pos + Vector2(-8.0, -12.0)
	if orb.has_method("configure"):
		orb.configure(_orb_speed, _orb_lifetime)
	var host: Node = _find_projectiles_root()
	if host != null:
		host.add_child(orb)


func _find_projectiles_root() -> Node:
	var n: Node = get_parent()
	while n != null:
		if n.has_node("Projectiles"):
			return n.get_node("Projectiles")
		n = n.get_parent()
	return null


func on_stomped() -> bool:
	if not _alive:
		return false
	_alive = false
	collision_layer = 0
	collision_mask = 0
	velocity = Vector2.ZERO
	set_physics_process(false)
	var tween: Tween = create_tween()
	tween.tween_property(_sprite, "scale", Vector2(1.2, 0.4), 0.08)
	tween.tween_property(_sprite, "modulate:a", 0.0, 0.15)
	tween.tween_callback(queue_free)
	return true
