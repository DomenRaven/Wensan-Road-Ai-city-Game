extends Area2D

signal deactivated(projectile: Area2D)

const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")
const SurvivorWorld := preload("res://core/survivor_world.gd")

var velocity: Vector2 = Vector2.ZERO
var damage: int = 10
var _max_travel: float = 900.0
var _spawn_pos: Vector2 = Vector2.ZERO

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	top_level = true
	z_index = 8
	_apply_theme()


func activate(pos: Vector2, direction: Vector2, speed: float, projectile_damage: int) -> void:
	_spawn_pos = pos
	damage = projectile_damage
	var dir: Vector2 = direction.normalized() if direction.length_squared() > 0.001 else Vector2.DOWN
	velocity = dir * speed
	global_position = pos
	rotation = dir.angle()
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
	deactivated.emit(self)


func _apply_theme() -> void:
	SurvivorSpriteUtil.apply_bullet_sprite(_sprite, 1.2)


func _physics_process(delta: float) -> void:
	if not visible:
		return
	global_position += velocity * delta
	var world_size: Vector2 = SurvivorWorld.get_size()
	if global_position.x < -32.0 or global_position.y < -32.0:
		deactivate()
		return
	if global_position.x > world_size.x + 32.0 or global_position.y > world_size.y + 32.0:
		deactivate()
		return
	if global_position.distance_squared_to(_spawn_pos) > _max_travel * _max_travel:
		deactivate()


func _on_area_entered(area: Area2D) -> void:
	if not monitoring:
		return
	if area.is_in_group("enemy") or area.is_in_group("boss"):
		if area.has_method("take_damage"):
			area.call("take_damage", damage)
		ThemeSoundUtil.play(self, "impact", "hit")
		call_deferred("deactivate")
