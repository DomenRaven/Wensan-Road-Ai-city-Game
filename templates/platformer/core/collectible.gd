extends Area2D

signal collected

const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _taken: bool = false

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D


func _ready() -> void:
	body_entered.connect(_on_body_entered)
	_apply_theme()


func _apply_theme() -> void:
	SpriteFramesUtil.apply_coin_frames(_sprite, GameConfig.get_theme())
	_sprite.centered = true


func _on_body_entered(body: Node2D) -> void:
	if _taken or not body.is_in_group("player"):
		return
	_taken = true
	collision_layer = 0
	collision_mask = 0
	_sprite.play("collected")
	ThemeSoundUtil.play(self, "impact", "collect")
	collected.emit()
	await _sprite.animation_finished
	queue_free()
