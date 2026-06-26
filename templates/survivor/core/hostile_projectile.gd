extends Area2D

const SurvivorWorld := preload("res://core/survivor_world.gd")

var velocity: Vector2 = Vector2.ZERO
var damage: int = 10
var _life: float = 3.0

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	top_level = true
	z_index = 7
	_apply_theme()


func activate(pos: Vector2, direction: Vector2, speed: float, projectile_damage: int) -> void:
	global_position = pos
	damage = projectile_damage
	var dir: Vector2 = direction.normalized() if direction.length_squared() > 0.001 else Vector2.DOWN
	velocity = dir * speed
	rotation = dir.angle()
	_life = 3.0
	_sprite.visible = true
	visible = true
	monitoring = true
	monitorable = true
	process_mode = Node.PROCESS_MODE_INHERIT


func deactivate() -> void:
	velocity = Vector2.ZERO
	visible = false
	_sprite.visible = false
	global_position = Vector2(-9999.0, -9999.0)
	monitoring = false
	monitorable = false
	process_mode = Node.PROCESS_MODE_DISABLED


func _apply_theme() -> void:
	_build_hostile_bullet_texture()
	_sprite.scale = Vector2(2.4, 2.4)
	_sprite.modulate = Color(0.15, 0.15, 0.18, 1.0)


func _build_hostile_bullet_texture() -> void:
	var image: Image = Image.create(14, 14, false, Image.FORMAT_RGBA8)
	image.fill(Color(0, 0, 0, 0))
	for y: int in 14:
		for x: int in 14:
			var dx: float = float(x) - 6.5
			var dy: float = float(y) - 6.5
			if dx * dx + dy * dy <= 36.0:
				image.set_pixel(x, y, Color(0.2, 0.2, 0.25, 1.0))
	_sprite.texture = ImageTexture.create_from_image(image)


func _physics_process(delta: float) -> void:
	if not visible:
		return
	global_position += velocity * delta
	_life -= delta
	if _life <= 0.0:
		deactivate()
		return
	var world_size: Vector2 = SurvivorWorld.get_size()
	if global_position.x < -32.0 or global_position.x > world_size.x + 32.0:
		deactivate()
		return
	if global_position.y < -32.0 or global_position.y > world_size.y + 32.0:
		deactivate()


func _on_area_entered(area: Area2D) -> void:
	if not monitoring:
		return
	if area.is_in_group("player") and area.has_method("take_hit"):
		area.call("take_hit", damage, global_position)
		deactivate()
