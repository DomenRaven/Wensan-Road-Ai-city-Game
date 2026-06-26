extends Area2D

## 红怪发射的缓慢光球：向左飞行 · 5s 寿命 · 出屏销毁
const ORB_COLOR: Color = Color(0.92, 0.15, 0.12, 1.0)
const ThemeSpriteUtil := preload("res://core/theme_sprite.gd")

var _speed: float = 80.0
var _lifetime: float = 5.0
var _age: float = 0.0
var _level_left: float = -32.0
var _level_right: float = 2000.0

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	add_to_group("enemy_projectile")
	body_entered.connect(_on_body_entered)
	_sprite.texture = ThemeSpriteUtil.load_texture("", ORB_COLOR, Vector2i(14, 14))
	_sprite.centered = true
	_cache_level_bounds()


func configure(speed: float, lifetime: float) -> void:
	_speed = speed
	_lifetime = lifetime


func _cache_level_bounds() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var mult: float = float(level_cfg.get("width_multiplier", 3.0))
	var viewport_w: float = 640.0
	if get_viewport() != null:
		viewport_w = get_viewport().get_visible_rect().size.x
	_level_right = viewport_w * mult + 64.0
	_level_left = -64.0


func _physics_process(delta: float) -> void:
	_age += delta
	if _age >= _lifetime:
		queue_free()
		return
	global_position.x -= _speed * delta
	if global_position.x < _level_left or global_position.x > _level_right:
		queue_free()


func _on_body_entered(body: Node2D) -> void:
	if body == null or not body.is_in_group("player"):
		return
	if body.has_method("notify_hazard"):
		body.notify_hazard("enemy")
	queue_free()
