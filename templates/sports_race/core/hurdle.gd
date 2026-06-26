extends Area2D
class_name Hurdle

signal player_hit

const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _scroll_speed: float = 240.0

@onready var _sprite: Sprite2D = $Sprite2D
@onready var _collision: CollisionShape2D = $CollisionShape2D


func setup(scroll_speed: float, texture: Texture2D) -> void:
	_scroll_speed = scroll_speed
	if texture != null:
		_sprite.texture = texture
	var rect: RectangleShape2D = _collision.shape as RectangleShape2D
	if rect != null:
		rect.size = Vector2(40, 36)
		_collision.position = Vector2(0, -18)
		_sprite.position = Vector2(0, -18)


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = speed


func _physics_process(delta: float) -> void:
	position.x -= _scroll_speed * delta
	if global_position.x < -56.0:
		queue_free()


func _on_body_entered(body: Node) -> void:
	if not body.is_in_group("player"):
		return
	if body.has_method("is_clearing_hurdle") and bool(body.call("is_clearing_hurdle")):
		return
	ThemeSoundUtil.play(self, "impact", "hit")
	player_hit.emit()
