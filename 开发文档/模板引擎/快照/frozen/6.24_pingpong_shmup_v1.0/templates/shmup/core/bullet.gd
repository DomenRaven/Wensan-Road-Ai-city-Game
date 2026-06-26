extends Area2D

signal deactivated(bullet: Area2D)

const ShmupSheetUtil := preload("res://core/shmup_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var velocity: Vector2 = Vector2.ZERO
var damage: int = 1
var is_player_bullet: bool = true
var pierce: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func activate(
	pos: Vector2,
	vel: Vector2,
	from_player: bool,
	bullet_damage: int,
	is_pierce: bool
) -> void:
	global_position = pos
	velocity = vel
	is_player_bullet = from_player
	damage = bullet_damage
	pierce = is_pierce
	_apply_bullet_theme(from_player)
	visible = true
	monitoring = true
	monitorable = true
	process_mode = Node.PROCESS_MODE_INHERIT
	collision_layer = 8 if from_player else 16
	collision_mask = 4 if from_player else 1


func _apply_bullet_theme(from_player: bool) -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	if from_player:
		var bullet_data: Dictionary = types_cfg.get("player_bullet", {}) as Dictionary
		var frame_index: int = int(bullet_data.get("frame", 0))
		ShmupSheetUtil.apply_tile_sprite(_sprite, frame_index, 1.0)
	else:
		var bullet_data: Dictionary = types_cfg.get("enemy_bullet", {}) as Dictionary
		var frame_index: int = int(bullet_data.get("frame", 2))
		ShmupSheetUtil.apply_tile_sprite(_sprite, frame_index, 1.2)


func deactivate() -> void:
	velocity = Vector2.ZERO
	visible = false
	call_deferred("set", "monitoring", false)
	call_deferred("set", "monitorable", false)
	call_deferred("set", "process_mode", Node.PROCESS_MODE_DISABLED)
	deactivated.emit(self)


func _physics_process(delta: float) -> void:
	position += velocity * delta
	if global_position.y < -24.0 or global_position.y > 384.0:
		deactivate()
		return
	if global_position.x < -24.0 or global_position.x > 664.0:
		deactivate()


func _on_area_entered(area: Area2D) -> void:
	if not monitoring:
		return
	if is_player_bullet and area.is_in_group("enemy"):
		if area.has_method("take_damage"):
			area.call("take_damage", damage)
		ThemeSoundUtil.play(self, "impact", "hit")
		if not pierce:
			call_deferred("deactivate")
	elif not is_player_bullet and area.is_in_group("player"):
		if area.has_method("take_hit"):
			area.call("take_hit")
		call_deferred("deactivate")
