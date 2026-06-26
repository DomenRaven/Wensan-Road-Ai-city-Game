extends StaticBody2D

signal coin_spawned(world_pos: Vector2)

const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")

var _used: bool = false

@onready var _sprite: AnimatedSprite2D = $AnimatedSprite2D


func _ready() -> void:
	_apply_theme()


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	SpriteFramesUtil.apply_box_frames(_sprite, theme)
	_sprite.centered = true


func try_hit_from_below(player: CharacterBody2D) -> bool:
	if _used or player == null:
		return false
	var block_bottom: float = global_position.y + 12.0
	var player_head: float = player.global_position.y - 28.0
	if player.velocity.y >= 0.0:
		return false
	if player_head > block_bottom:
		return false
	_used = true
	player.velocity.y = 0.0
	_sprite.play("hit")
	coin_spawned.emit(global_position + Vector2(0.0, -32.0))
	await _sprite.animation_finished
	if is_instance_valid(_sprite):
		_sprite.play("break")
		await _sprite.animation_finished
	queue_free()
	return true
