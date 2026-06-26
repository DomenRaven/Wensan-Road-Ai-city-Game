extends Node2D

const PathFollowerClass: GDScript = preload("res://core/path_follower.gd")
const TdCombatClass: GDScript = preload("res://core/td_combat.gd")
const TdGridClass: GDScript = preload("res://core/td_grid.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal reached_exit
signal defeated(reward: int)

var hp: int = 40
var max_hp: int = 40
var move_speed: float = 60.0
var defense: int = 0
var grid_cell: Vector2i = Vector2i.ZERO

var _follower: RefCounted = PathFollowerClass.new()


func setup(
	waypoints: Array[Vector2],
	p_hp: int,
	p_speed: float,
	p_defense: int,
	sprite_path: String
) -> void:
	hp = p_hp
	max_hp = p_hp
	move_speed = p_speed
	defense = p_defense
	_follower.setup(waypoints)
	_apply_sprite(sprite_path)


func _apply_sprite(sprite_path: String) -> void:
	var sprite: Sprite2D = $Sprite as Sprite2D
	if sprite == null:
		return
	if sprite_path != "" and ResourceLoader.exists(sprite_path):
		sprite.texture = load(sprite_path) as Texture2D


func get_progress() -> float:
	return _follower.get_progress_ratio()


func _process(delta: float) -> void:
	if _follower.finished:
		reached_exit.emit()
		queue_free()
		return
	var step: Vector2 = _follower.advance(move_speed, delta)
	if step != Vector2.ZERO:
		position += step
		grid_cell = _estimate_grid_cell()


func take_damage(attack: int) -> void:
	var damage: int = TdCombatClass.calc_damage(attack, defense)
	hp -= damage
	ThemeSoundUtil.play(self, "impact", "hit")
	if hp <= 0:
		var tuning: Dictionary = GameConfig.get_tuning()
		var economy: Dictionary = tuning.get("economy", {}) as Dictionary
		var reward: int = int(economy.get("kill_reward", 10))
		defeated.emit(reward)
		queue_free()


func _estimate_grid_cell() -> Vector2i:
	return Vector2i(
		int(floor(position.x / float(TdGridClass.CELL_SIZE))),
		int(floor(position.y / float(TdGridClass.CELL_SIZE)))
	)
