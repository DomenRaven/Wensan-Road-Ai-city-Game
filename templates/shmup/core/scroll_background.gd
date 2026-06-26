extends Node2D

const SCROLL_SPEED: float = 56.0

@onready var _bg_a: Sprite2D = $BgA
@onready var _bg_b: Sprite2D = $BgB


func _ready() -> void:
	_apply_theme()


func _apply_theme() -> void:
	var ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
	var bg_tex: Texture2D = ShmupSheetUtil.background_texture()
	if bg_tex == null:
		return
	for sprite: Sprite2D in [_bg_a, _bg_b]:
		sprite.texture = bg_tex
		sprite.centered = false
		sprite.scale = Vector2(1.0, 1.2)


func _process(delta: float) -> void:
	if _bg_a.texture == null:
		return
	var scroll: float = SCROLL_SPEED * delta
	_bg_a.position.y += scroll
	_bg_b.position.y += scroll
	var height: float = 432.0
	if _bg_a.position.y >= height:
		_bg_a.position.y = _bg_b.position.y - height
	if _bg_b.position.y >= height:
		_bg_b.position.y = _bg_a.position.y - height
