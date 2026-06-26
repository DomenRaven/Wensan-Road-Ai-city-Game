extends Area2D

signal destroyed(enemy: Area2D)

var _speed: float = 120.0
var _hp: int = 1
var _hit_this_frame: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	_apply_tuning()
	_apply_theme()


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	_speed = float(enemy_cfg.get("speed", _speed))
	_hp = int(enemy_cfg.get("hp", _hp))


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("enemy_sprite", ""))
	if sprite_path != "" and ResourceLoader.exists(sprite_path):
		_sprite.texture = load(sprite_path) as Texture2D
	else:
		_sprite.modulate = Color(1.0, 0.55, 0.45, 1.0)
	_sprite.scale = Vector2(0.55, 0.55)


func _physics_process(delta: float) -> void:
	_hit_this_frame = false
	position.y += _speed * delta
	if global_position.y > 392.0:
		queue_free()


func take_damage(amount: int) -> void:
	if _hit_this_frame:
		return
	_hit_this_frame = true
	_hp -= amount
	if _hp <= 0:
		destroyed.emit(self)
		queue_free()
