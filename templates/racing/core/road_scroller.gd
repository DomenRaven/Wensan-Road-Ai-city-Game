extends Node2D

const RacingViewportScript := preload("res://core/racing_viewport.gd")

var _scroll_speed: float = 0.0
var _scroll_offset: float = 0.0
var _tile_height: float = RacingViewportScript.HEIGHT

@onready var _layer_a: Sprite2D = $LayerA
@onready var _layer_b: Sprite2D = $LayerB


func setup(track_texture: Texture2D, _bg_color: Color, _crop_left_ratio: float = 0.38) -> void:
	if track_texture == null:
		return
	var tex_size: Vector2 = track_texture.get_size()
	# 秒哒 Phaser tileSprite(0,0,width,height,'track_atlas')：整图集非等比拉伸至 540×960
	var scale_x: float = RacingViewportScript.WIDTH / tex_size.x
	var scale_y: float = RacingViewportScript.HEIGHT / tex_size.y
	_tile_height = tex_size.y * scale_y
	for layer: Sprite2D in [_layer_a, _layer_b]:
		layer.texture = track_texture
		layer.region_enabled = false
		layer.centered = false
		layer.scale = Vector2(scale_x, scale_y)
		layer.position = Vector2.ZERO
	_layer_a.position = Vector2.ZERO
	_layer_b.position = Vector2(0.0, -_tile_height)


func set_scroll_speed(speed: float) -> void:
	_scroll_speed = maxf(0.0, speed)


func _process(delta: float) -> void:
	if _scroll_speed <= 0.0:
		return
	_scroll_offset += _scroll_speed * delta
	while _scroll_offset >= _tile_height:
		_scroll_offset -= _tile_height
	_layer_a.position.y = _scroll_offset
	_layer_b.position.y = _scroll_offset - _tile_height
