extends Node2D

const POOL_SIZE: int = 48
const BULLET_SCENE: PackedScene = preload("res://scenes/bullet.tscn")

var _pool: Array[Area2D] = []


func _ready() -> void:
	for _i: int in POOL_SIZE:
		var bullet: Area2D = BULLET_SCENE.instantiate() as Area2D
		bullet.visible = false
		bullet.process_mode = Node.PROCESS_MODE_DISABLED
		add_child(bullet)
		if bullet.has_signal("deactivated"):
			bullet.deactivated.connect(_on_bullet_deactivated)
		_pool.append(bullet)


func spawn_player_bullet(pos: Vector2, direction: Vector2, speed: float) -> void:
	var bullet: Area2D = _acquire_bullet()
	if bullet == null:
		return
	if bullet.has_method("activate"):
		bullet.call("activate", pos, direction, speed, 1)


func _acquire_bullet() -> Area2D:
	for bullet: Area2D in _pool:
		if not bullet.visible:
			return bullet
	return null


func _on_bullet_deactivated(_bullet: Area2D) -> void:
	pass
