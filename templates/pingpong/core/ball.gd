extends Area2D

const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")
const PongSheetUtil := preload("res://core/pong_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal scored(side: String)

var base_speed: float = 250.0
var speed_increment: float = 25.0
var ball_radius: float = 9.0
var hit_radius: float = 6.0
var table_left: float = 0.0
var table_right: float = 640.0
var table_top: float = 48.0
var table_bottom: float = 352.0
var hits_per_speed_ramp: int = 3
var speed_fluctuation_min: float = 0.85
var speed_fluctuation_max: float = 1.15
var contact_angle_scale: float = 4.2
var spin_frame_interval: float = 0.0833333

var velocity: Vector2 = Vector2.ZERO
var _current_speed: float = 250.0
var _hit_count: int = 0
var _active: bool = false
var _spin_frame: int = 0
var _spin_timer: float = 0.0
var _player_paddle: Area2D = null
var _ai_paddle: Area2D = null

@onready var _visual: ColorRect = $Visual
@onready var _sprite: Sprite2D = $Sprite
@onready var _shadow: Sprite2D = $Shadow


func _ready() -> void:
	_apply_config()
	_apply_theme()


func configure(
	player_paddle: Area2D,
	ai_paddle: Area2D,
	bounds: Rect2
) -> void:
	_player_paddle = player_paddle
	_ai_paddle = ai_paddle
	table_left = bounds.position.x
	table_right = bounds.position.x + bounds.size.x
	table_top = bounds.position.y + hit_radius
	table_bottom = bounds.position.y + bounds.size.y - hit_radius


func get_velocity() -> Vector2:
	return velocity


func _apply_config() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var ball_cfg: Dictionary = tuning.get("ball", {}) as Dictionary
	base_speed = float(ball_cfg.get("base_speed", base_speed))
	speed_increment = float(ball_cfg.get("speed_increment", speed_increment))
	ball_radius = float(ball_cfg.get("radius", ball_radius))
	hit_radius = float(ball_cfg.get("hit_radius", ball_radius * 0.67))
	hits_per_speed_ramp = int(ball_cfg.get("hits_per_ramp", hits_per_speed_ramp))
	var physics_cfg: Dictionary = tuning.get("physics", {}) as Dictionary
	speed_fluctuation_min = float(physics_cfg.get("speed_fluctuation_min", speed_fluctuation_min))
	speed_fluctuation_max = float(physics_cfg.get("speed_fluctuation_max", speed_fluctuation_max))
	contact_angle_scale = float(physics_cfg.get("contact_angle_scale", contact_angle_scale))
	spin_frame_interval = 1.0 / float(ball_cfg.get("spin_fps", 12.0))
	_current_speed = base_speed
	_update_collision()


func _update_collision() -> void:
	var shape_node: CollisionShape2D = $CollisionShape2D as CollisionShape2D
	if shape_node == null:
		return
	var circle: CircleShape2D = shape_node.shape as CircleShape2D
	if circle != null:
		circle.radius = hit_radius


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(
		theme.get("ball_sprite", PongSheetUtil.theme_path("ball_sprite", "ball_frames.png"))
	)
	var diameter: int = int(ball_radius * 2.0)
	if sprite_path.ends_with("ball_frames.png"):
		_sprite.texture = PongSheetUtil.ball_frame(0)
		_sprite.visible = true
		_visual.visible = false
		var frame_scale: float = diameter / float(PongSheetUtil.BALL_FRAME_SIZE.x)
		_sprite.scale = Vector2(frame_scale, frame_scale)
		_sprite.centered = true
		_sprite.z_index = 1
	else:
		ThemeSpriteUtil.apply_to_sprite(
			_sprite,
			sprite_path,
			Color(1, 1, 1),
			Vector2i(diameter, diameter)
		)
		_sprite.visible = sprite_path != ""
		_visual.visible = not _sprite.visible
		_sprite.centered = true
		_sprite.z_index = 1
	_apply_shadow()
	if _visual.visible:
		_visual.size = Vector2(diameter, diameter)
		_visual.position = Vector2(-ball_radius, -ball_radius)
		_visual.color = Color(1, 1, 1)


func _apply_shadow() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var shadow_path: String = str(
		theme.get("ball_shadow_sprite", PongSheetUtil.theme_path("ball_shadow_sprite", "ball_shadow.png"))
	)
	var shadow_tex: Texture2D = _load_shadow_texture(shadow_path)
	if shadow_tex == null:
		shadow_tex = _create_soft_shadow_texture(Vector2i(48, 24))
	_shadow.texture = shadow_tex
	_shadow.visible = true
	_shadow.centered = true
	_shadow.z_index = 0
	_shadow.show_behind_parent = false
	var tex_size: Vector2 = shadow_tex.get_size()
	var shadow_w: float = ball_radius * 2.8
	var shadow_h: float = ball_radius * 1.35
	if tex_size.x > 0.0 and tex_size.y > 0.0:
		_shadow.scale = Vector2(shadow_w / tex_size.x, shadow_h / tex_size.y)
	_shadow.position = Vector2(0.0, ball_radius * 1.05)
	_shadow.modulate = Color(1.0, 1.0, 1.0, 0.82)


func _load_shadow_texture(path: String) -> Texture2D:
	if path == "":
		return null
	if ResourceLoader.exists(path):
		var loaded: Texture2D = load(path) as Texture2D
		if loaded != null:
			return loaded
	var abs_path: String = path
	if path.begins_with("res://"):
		abs_path = ProjectSettings.globalize_path(path)
	if FileAccess.file_exists(abs_path):
		var img: Image = Image.load_from_file(abs_path)
		if img != null and not img.is_empty():
			return ImageTexture.create_from_image(img)
	return null


func _create_soft_shadow_texture(size: Vector2i) -> Texture2D:
	var img: Image = Image.create(size.x, size.y, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.0, 0.0, 0.0, 0.0))
	var center: Vector2 = Vector2(size) * 0.5
	var radius_x: float = float(size.x) * 0.5 - 1.0
	var radius_y: float = float(size.y) * 0.5 - 1.0
	for y: int in range(size.y):
		for x: int in range(size.x):
			var nx: float = (float(x) - center.x) / radius_x
			var ny: float = (float(y) - center.y) / radius_y
			var dist_sq: float = nx * nx + ny * ny
			if dist_sq <= 1.0:
				var alpha: float = (1.0 - dist_sq) * (1.0 - dist_sq) * 0.7
				img.set_pixel(x, y, Color(0.0, 0.0, 0.0, alpha))
	return ImageTexture.create_from_image(img)


func reset_to_center(center: Vector2) -> void:
	global_position = center
	velocity = Vector2.ZERO
	_active = false


func serve_toward(direction: int) -> void:
	_hit_count = 0
	_current_speed = base_speed
	_active = true
	global_position = Vector2((table_left + table_right) * 0.5, (table_top + table_bottom) * 0.5)
	velocity = Vector2(
		float(direction) * _current_speed,
		(randf() - 0.5) * _current_speed
	)


func halt() -> void:
	_active = false
	velocity = Vector2.ZERO


func _physics_process(delta: float) -> void:
	if not _active:
		return
	var step_count: int = maxi(1, int(ceilf(velocity.length() * delta / (hit_radius * 0.5))))
	var step_delta: float = delta / float(step_count)
	for _i: int in step_count:
		global_position += velocity * step_delta
		_bounce_vertical_walls()
		if _check_paddle_hits():
			break
		_check_scoring()
		if not _active:
			break
	_animate_spin(delta)


func _animate_spin(delta: float) -> void:
	_spin_timer += delta
	if _spin_timer < spin_frame_interval:
		return
	_spin_timer = 0.0
	_spin_frame = (_spin_frame + 1) % PongSheetUtil.BALL_FRAME_COUNT
	if _sprite.visible:
		_sprite.texture = PongSheetUtil.ball_frame(_spin_frame)


func _bounce_vertical_walls() -> void:
	if global_position.y <= table_top:
		global_position.y = table_top
		velocity.y = absf(velocity.y)
	elif global_position.y >= table_bottom:
		global_position.y = table_bottom
		velocity.y = -absf(velocity.y)


func _check_paddle_hits() -> bool:
	if _player_paddle != null and velocity.x < 0.0:
		if _try_paddle_bounce(_player_paddle, 1):
			return true
	if _ai_paddle != null and velocity.x > 0.0:
		if _try_paddle_bounce(_ai_paddle, -1):
			return true
	return false


func _try_paddle_bounce(paddle: Area2D, direction: int) -> bool:
	if not paddle.has_method("get_hit_rect"):
		return false
	var paddle_rect: Rect2 = paddle.call("get_hit_rect") as Rect2
	var ball_rect: Rect2 = Rect2(
		global_position - Vector2(hit_radius, hit_radius),
		Vector2(hit_radius * 2.0, hit_radius * 2.0)
	)
	if not paddle_rect.intersects(ball_rect):
		return false
	_apply_paddle_bounce(paddle, direction)
	return true


func _apply_paddle_bounce(paddle: Area2D, direction: int) -> void:
	_hit_count += 1
	if _hit_count % hits_per_speed_ramp == 0:
		_current_speed += speed_increment
	var diff: float = 0.0
	if global_position.y < paddle.global_position.y:
		diff = paddle.global_position.y - global_position.y
		velocity.y = -contact_angle_scale * diff
	elif global_position.y > paddle.global_position.y:
		diff = global_position.y - paddle.global_position.y
		velocity.y = contact_angle_scale * diff
	else:
		velocity.y = 2.0 + randf() * 8.0
	var factor: float = randf_range(speed_fluctuation_min, speed_fluctuation_max)
	var new_speed: float = _current_speed * factor
	velocity.x = float(direction) * new_speed
	if direction > 0:
		global_position.x = paddle.global_position.x + hit_radius + 2.0
	else:
		global_position.x = paddle.global_position.x - hit_radius - 2.0
	ThemeSoundUtil.play(self, "impact", "rally")


func _check_scoring() -> void:
	if global_position.x <= table_left - hit_radius:
		halt()
		scored.emit("ai")
	elif global_position.x >= table_right + hit_radius:
		halt()
		scored.emit("player")
