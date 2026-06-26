extends Area2D

const SurvivorWorld := preload("res://core/survivor_world.gd")

const HIT_RADIUS_SQ: float = 20.0 * 20.0

var velocity: Vector2 = Vector2.ZERO
var damage: int = 8
var _life: float = 5.0
var _hit_player: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	top_level = true
	z_index = 6
	_build_orb_texture()


func _build_orb_texture() -> void:
	var image: Image = Image.create(32, 32, false, Image.FORMAT_RGBA8)
	image.fill(Color(0, 0, 0, 0))
	for y: int in 32:
		for x: int in 32:
			var dist: float = Vector2(x - 15.5, y - 15.5).length()
			if dist <= 14.0:
				var alpha: float = clampf(1.0 - dist / 14.0, 0.25, 1.0)
				image.set_pixel(x, y, Color(1.0, 0.75, 0.2, alpha))
	var texture: ImageTexture = ImageTexture.create_from_image(image)
	_sprite.texture = texture
	_sprite.scale = Vector2(1.15, 1.15)


func activate(pos: Vector2, direction: Vector2, speed: float, orb_damage: int, lifetime: float) -> void:
	var dir: Vector2 = direction.normalized() if direction.length_squared() > 0.001 else Vector2.DOWN
	global_position = pos + dir * 52.0
	damage = orb_damage
	velocity = dir * speed
	_life = lifetime
	_hit_player = false
	visible = true
	_sprite.visible = true
	monitoring = true
	monitorable = true
	process_mode = Node.PROCESS_MODE_INHERIT


func deactivate() -> void:
	velocity = Vector2.ZERO
	_hit_player = false
	visible = false
	_sprite.visible = false
	global_position = Vector2(-9999.0, -9999.0)
	monitoring = false
	monitorable = false
	process_mode = Node.PROCESS_MODE_DISABLED


func _physics_process(delta: float) -> void:
	if not visible:
		return
	global_position += velocity * delta
	_life -= delta
	if _life <= 0.0:
		deactivate()
		return
	_try_hit_player()
	var world_size: Vector2 = SurvivorWorld.get_size()
	if global_position.x < -64.0 or global_position.x > world_size.x + 64.0:
		deactivate()
		return
	if global_position.y < -64.0 or global_position.y > world_size.y + 64.0:
		deactivate()


func _try_hit_player() -> void:
	if _hit_player:
		return
	var player: Area2D = get_tree().get_first_node_in_group("player") as Area2D
	if player == null:
		return
	if global_position.distance_squared_to(player.global_position) > HIT_RADIUS_SQ:
		return
	if player.has_method("take_orb_hit"):
		player.call("take_orb_hit", damage, global_position)
	elif player.has_method("take_hit"):
		player.call("take_hit", damage, global_position)
	_hit_player = true
	deactivate()


func _on_area_entered(area: Area2D) -> void:
	if not monitoring or _hit_player:
		return
	if not area.is_in_group("player"):
		return
	if area.has_method("take_orb_hit"):
		area.call("take_orb_hit", damage, global_position)
	elif area.has_method("take_hit"):
		area.call("take_hit", damage, global_position)
	_hit_player = true
	deactivate()
