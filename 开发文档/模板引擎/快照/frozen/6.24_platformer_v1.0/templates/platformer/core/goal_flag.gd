extends Area2D

signal reached

const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")

var _triggered: bool = false

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D


func _ready() -> void:
	body_entered.connect(_on_body_entered)
	_apply_theme()


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	SpriteFramesUtil.apply_goal_frames(_sprite, theme)
	_sprite.centered = true
	_sprite.position = Vector2(0.0, -32.0)


func _on_body_entered(body: Node2D) -> void:
	if _triggered or not body.is_in_group("player"):
		return
	_triggered = true
	_sprite.play("pressed")
	reached.emit()
