extends Area2D

signal collected(pickup: Area2D, powerup_name: String)

var _powerup_name: String = ""
var _speed: float = 100.0

@onready var _sprite: Sprite2D = $Sprite2D


func configure(powerup_name: String, tile_frame: int, speed: float) -> void:
	_powerup_name = powerup_name
	_speed = speed
	var sprite: Sprite2D = _sprite if _sprite != null else get_node_or_null("Sprite2D") as Sprite2D
	if sprite == null:
		return
	var ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
	ShmupSheetUtil.apply_tile_sprite(sprite, tile_frame, 1.5)


func _physics_process(delta: float) -> void:
	position.y += _speed * delta
	if global_position.y > 400.0:
		queue_free()


func _on_area_entered(area: Area2D) -> void:
	if area.is_in_group("player"):
		collected.emit(self, _powerup_name)
		queue_free()
