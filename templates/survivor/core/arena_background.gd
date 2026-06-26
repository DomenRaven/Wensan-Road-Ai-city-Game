extends Node2D

const SurvivorWorld := preload("res://core/survivor_world.gd")

var _base_color: Color = Color(0.992, 0.984, 0.969, 1.0)
var _alt_color: Color = Color(0.961, 0.941, 0.902, 1.0)


func _ready() -> void:
	z_index = -100
	_apply_theme()
	queue_redraw()


func apply_theme_color(hex: String) -> void:
	_base_color = Color.from_string(hex, _base_color)
	_alt_color = _base_color.darkened(0.04)
	queue_redraw()


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_color: String = str(theme.get("background_color", "#FDFBF7"))
	_base_color = Color.from_string(bg_color, _base_color)
	_alt_color = _base_color.darkened(0.04)


func _draw() -> void:
	var world_size: Vector2 = SurvivorWorld.get_size()
	var step: float = SurvivorWorld.get_grid_step()
	draw_rect(Rect2(Vector2.ZERO, world_size), _base_color)
	var cols: int = int(ceil(world_size.x / step))
	var rows: int = int(ceil(world_size.y / step))
	for row: int in rows:
		for col: int in cols:
			if (row + col) % 2 != 0:
				continue
			var cell: Rect2 = Rect2(float(col) * step, float(row) * step, step, step)
			draw_rect(cell, _alt_color)
