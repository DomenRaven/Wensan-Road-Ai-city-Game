extends Area2D

const ScreenWrapUtil = preload("res://core/screen_wrap.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal deactivated(bullet: Area2D)

var velocity: Vector2 = Vector2.ZERO
var damage: int = 1
var _hit_ids: Dictionary = {}

@onready var _sprite: Sprite2D = $Sprite2D


func activate(pos: Vector2, dir: Vector2, speed: float, bullet_damage: int) -> void:
	global_position = pos
	velocity = dir.normalized() * speed
	damage = bullet_damage
	_hit_ids.clear()
	_apply_bullet_theme()
	visible = true
	monitoring = true
	monitorable = true
	process_mode = Node.PROCESS_MODE_INHERIT


func _apply_bullet_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("bullet_sprite", ""))
	if sprite_path != "" and ResourceLoader.exists(sprite_path):
		_sprite.texture = load(sprite_path) as Texture2D
		return
	_sprite.modulate = Color(0.45, 0.95, 1.0, 1.0)


func deactivate() -> void:
	velocity = Vector2.ZERO
	visible = false
	call_deferred("set", "monitoring", false)
	call_deferred("set", "monitorable", false)
	call_deferred("set", "process_mode", Node.PROCESS_MODE_DISABLED)
	deactivated.emit(self)


func _physics_process(delta: float) -> void:
	position += velocity * delta
	position = ScreenWrapUtil.wrap(position)


func _on_area_entered(area: Area2D) -> void:
	if not monitoring or not area.is_in_group("enemy"):
		return
	var enemy_id: int = area.get_instance_id()
	if _hit_ids.has(enemy_id):
		return
	_hit_ids[enemy_id] = true
	if area.has_method("take_damage"):
		area.call("take_damage", damage)
	ThemeSoundUtil.play(self, "impact", "hit")
	deactivate()
