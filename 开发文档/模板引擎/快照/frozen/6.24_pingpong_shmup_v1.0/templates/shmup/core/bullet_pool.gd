extends Node2D

const POOL_SIZE: int = 48
const BULLET_SCENE: PackedScene = preload("res://scenes/bullet.tscn")

var _pool: Array[Area2D] = []
var _building: bool = false


func _ready() -> void:
	call_deferred("_build_pool")


func _build_pool() -> void:
	if _building:
		return
	_building = true
	for _i: int in POOL_SIZE:
		var bullet: Area2D = BULLET_SCENE.instantiate() as Area2D
		bullet.visible = false
		bullet.process_mode = Node.PROCESS_MODE_DISABLED
		add_child(bullet)
		if bullet.has_signal("deactivated"):
			bullet.deactivated.connect(_on_bullet_deactivated)
		_pool.append(bullet)
	_building = false


func spawn_player_bullet(pos: Vector2, speed: float, pierce: bool) -> void:
	var bullet: Area2D = _acquire_bullet()
	if bullet == null:
		return
	var vel: Vector2 = Vector2(0.0, -speed)
	if bullet.has_method("activate"):
		bullet.call("activate", pos, vel, true, 1, pierce)


func spawn_enemy_bullet(pos: Vector2, direction: Vector2, speed: float) -> void:
	var bullet: Area2D = _acquire_bullet()
	if bullet == null:
		return
	var vel: Vector2 = direction.normalized() * speed
	if bullet.has_method("activate"):
		bullet.call("activate", pos, vel, false, 1, false)


func spawn_enemy_bullet_fan(pos: Vector2, speed: float) -> void:
	var angles: Array[float] = [-20.0, 0.0, 20.0]
	for angle_deg: float in angles:
		var rad: float = deg_to_rad(90.0 + angle_deg)
		var direction: Vector2 = Vector2(cos(rad), sin(rad))
		spawn_enemy_bullet(pos, direction, speed)


func clear_enemy_bullets() -> void:
	for bullet: Area2D in _pool:
		if bullet.visible and bullet.has_method("is_player_bullet"):
			if not bool(bullet.get("is_player_bullet")):
				if bullet.has_method("deactivate"):
					bullet.call("deactivate")


func _acquire_bullet() -> Area2D:
	for bullet: Area2D in _pool:
		if not bullet.visible:
			return bullet
	return null


func _on_bullet_deactivated(_bullet: Area2D) -> void:
	pass
