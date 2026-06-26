extends Area2D
class_name Obstacle

enum ObstacleKind { TALL, LOW }

signal player_hit

const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const ParkourTexturesUtil := preload("res://core/parkour_textures.gd")

var _kind: ObstacleKind = ObstacleKind.TALL
var _scroll_speed: float = 300.0
var _variant: int = 0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _collision: CollisionShape2D = $CollisionShape2D


func setup(kind: ObstacleKind, scroll_speed: float, variant: int) -> void:
	_kind = kind
	_scroll_speed = scroll_speed
	_variant = variant
	var sprite: Sprite2D = get_node_or_null("Sprite2D") as Sprite2D
	if sprite != null:
		sprite.texture = ParkourTexturesUtil.get_obstacle_texture(variant)
	_apply_kind_shape()


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed


func _apply_kind_shape() -> void:
	var collision: CollisionShape2D = get_node_or_null("CollisionShape2D") as CollisionShape2D
	var sprite: Sprite2D = get_node_or_null("Sprite2D") as Sprite2D
	var rect: RectangleShape2D = collision.shape as RectangleShape2D if collision != null else null
	if rect == null:
		return
	var tex: Texture2D = sprite.texture if sprite != null else null
	var tex_size: Vector2 = tex.get_size() if tex != null else Vector2(32, 64)
	if _kind == ObstacleKind.TALL:
		rect.size = tex_size
		collision.position = Vector2(0, -tex_size.y * 0.5)
		if sprite != null:
			sprite.position = Vector2(0, -tex_size.y * 0.5)
	else:
		rect.size = tex_size
		collision.position = Vector2(0, -tex_size.y * 0.5)
		if sprite != null:
			sprite.position = Vector2(0, -tex_size.y * 0.5)


func _physics_process(delta: float) -> void:
	position.x -= _scroll_speed * delta
	if global_position.x < -100.0:
		queue_free()


func _on_body_entered(body: Node) -> void:
	if not body.is_in_group("player"):
		return
	if body.has_method("is_invincible") and bool(body.call("is_invincible")):
		return
	if not body.has_method("can_pass_obstacle"):
		ThemeSoundUtil.play(self, "impact", "hit")
		player_hit.emit()
		return
	if bool(body.call("can_pass_obstacle", _kind)):
		return
	ThemeSoundUtil.play(self, "impact", "hit")
	player_hit.emit()
