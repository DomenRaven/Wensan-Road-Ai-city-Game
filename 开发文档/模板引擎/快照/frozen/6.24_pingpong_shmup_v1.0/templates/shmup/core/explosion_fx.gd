extends Node2D

const ShmupSheetUtil := preload("res://core/shmup_sheet.gd")

const FRAMES: Array[int] = [4, 5, 6, 7]
const FRAME_SEC: float = 1.0 / 12.0

var _index: int = 0
var _timer: float = 0.0

@onready var _sprite: Sprite2D = $Sprite2D


func _ready() -> void:
	_sprite.texture = ShmupSheetUtil.tiles_frame(FRAMES[0])


func setup(world_pos: Vector2, scale_factor: float = 1.0) -> void:
	global_position = world_pos
	_sprite.scale = Vector2(scale_factor, scale_factor)


func _process(delta: float) -> void:
	_timer += delta
	if _timer < FRAME_SEC:
		return
	_timer = 0.0
	_index += 1
	if _index >= FRAMES.size():
		queue_free()
		return
	_sprite.texture = ShmupSheetUtil.tiles_frame(FRAMES[_index])
