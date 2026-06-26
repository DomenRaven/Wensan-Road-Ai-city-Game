extends Area2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const PongSheetUtil := preload("res://core/pong_sheet.gd")

var paddle_thickness: float = 14.0
var paddle_length: float = 56.0
var hit_width: float = 8.0
var hit_height: float = 40.0
var move_speed: float = 168.0
var table_top: float = 48.0
var table_bottom: float = 352.0
var is_player: bool = true
var is_left_side: bool = true
var _input_enabled: bool = true

@onready var _visual: ColorRect = $Visual
@onready var _sprite: Sprite2D = $Sprite


func _ready() -> void:
	_apply_config()
	_apply_theme()
	_update_collision()


func configure_bounds(top: float, bottom: float) -> void:
	table_top = top
	table_bottom = bottom


func set_input_enabled(enabled: bool) -> void:
	_input_enabled = enabled


func reset_to_center(center_y: float) -> void:
	position.y = center_y
	if has_method("set_velocity_y"):
		call("set_velocity_y", 0.0)


func _apply_config() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var paddle_cfg: Dictionary = tuning.get("paddle", {}) as Dictionary
	move_speed = float(paddle_cfg.get("speed", move_speed))
	paddle_thickness = float(paddle_cfg.get("width", paddle_thickness))
	paddle_length = float(paddle_cfg.get("height", paddle_length))
	hit_width = float(paddle_cfg.get("hit_width", paddle_thickness * 0.6))
	hit_height = float(paddle_cfg.get("hit_height", paddle_length * 0.72))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_key: String = "paddle_player_sprite" if is_left_side else "paddle_ai_sprite"
	var fallback: String = "paddle_player.png" if is_left_side else "paddle_ai.png"
	var sprite_path: String = str(theme.get(sprite_key, PongSheetUtil.theme_path(sprite_key, fallback)))
	if sprite_path != "":
		_sprite.visible = true
		_visual.visible = false
		_sprite.texture = ThemeSpriteUtil.load_texture(
			sprite_path,
			Color(0.2, 0.85, 0.35) if is_left_side else Color(0.95, 0.35, 0.3),
			Vector2i(int(paddle_thickness), int(paddle_length))
		)
		_sprite.centered = true
		var tex_size: Vector2 = _sprite.texture.get_size()
		if tex_size.x > 0.0 and tex_size.y > 0.0:
			_sprite.scale = Vector2(paddle_thickness / tex_size.x, paddle_length / tex_size.y)
	else:
		_sprite.visible = false
		_visual.visible = true
		_visual.size = Vector2(paddle_thickness, paddle_length)
		_visual.position = Vector2(-paddle_thickness * 0.5, -paddle_length * 0.5)
		_visual.color = Color(0.2, 0.85, 0.35) if is_left_side else Color(0.95, 0.35, 0.3)


func _update_collision() -> void:
	var shape_node: CollisionShape2D = $CollisionShape2D as CollisionShape2D
	if shape_node == null:
		return
	var rect: RectangleShape2D = shape_node.shape as RectangleShape2D
	if rect != null:
		rect.size = Vector2(hit_width, hit_height)


func get_paddle_length() -> float:
	return paddle_length


func get_hit_rect() -> Rect2:
	var half: Vector2 = Vector2(hit_width * 0.5, hit_height * 0.5)
	return Rect2(global_position - half, half * 2.0)


func _physics_process(delta: float) -> void:
	if not is_player or not _input_enabled:
		return
	var move_dir: float = 0.0
	if Input.is_action_pressed("move_up") and Input.is_action_pressed("move_down"):
		move_dir = 0.0
	elif Input.is_action_pressed("move_up"):
		move_dir = -1.0
	elif Input.is_action_pressed("move_down"):
		move_dir = 1.0
	position.y += move_dir * move_speed * delta
	var half_len: float = paddle_length * 0.5
	position.y = clampf(position.y, table_top + half_len, table_bottom - half_len)
