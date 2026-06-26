extends Area2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _base_speed: float = 120.0
var _lateral_speed: float = 0.0
var _track_left: float = 50.0
var _track_right: float = 590.0
var _sprite_scale: float = 0.14

var _hit_severity: float = 0.4

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("npc_car")
	monitoring = true
	monitorable = true
	collision_mask = 1
	area_entered.connect(_on_area_entered)


func setup(
	base_speed: float,
	lateral_speed: float,
	texture: Texture2D,
	track_left: float,
	track_right: float,
	sprite_scale: float
) -> void:
	_base_speed = base_speed
	_lateral_speed = lateral_speed
	_track_left = track_left
	_track_right = track_right
	_sprite_scale = sprite_scale
	if texture != null:
		_sprite.texture = texture
	_sprite.scale = Vector2(_sprite_scale, _sprite_scale)


func _on_area_entered(area: Area2D) -> void:
	var player: Node = area.get_parent()
	if player == null or not player.is_in_group("player"):
		return
	if player.has_method("trigger_hit"):
		player.call("trigger_hit", _hit_severity)


func setup_from_theme(
	base_speed: float,
	lateral_speed: float,
	sprite_path: String,
	track_left: float,
	track_right: float,
	sprite_scale: float,
	fallback_color: Color,
	hit_severity: float = 0.4
) -> void:
	_hit_severity = hit_severity
	var tex: Texture2D = ThemeSpriteUtil.load_texture(sprite_path, fallback_color, Vector2i(44, 68))
	setup(base_speed, lateral_speed, tex, track_left, track_right, sprite_scale)


func update_motion(delta: float, player_speed: float) -> void:
	var relative_y: float = player_speed - _base_speed
	position.y += relative_y * delta
	position.x += _lateral_speed * delta
	if position.x < _track_left and _lateral_speed < 0.0:
		_lateral_speed = -_lateral_speed
	if position.x > _track_right and _lateral_speed > 0.0:
		_lateral_speed = -_lateral_speed
	if position.y > RacingViewportScript.HEIGHT + 200.0:
		queue_free()
