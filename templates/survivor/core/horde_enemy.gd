extends Area2D

const SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")

signal destroyed(enemy: Area2D, xp_value: int)

var _speed: float = 70.0
var _hp: int = 15
var _xp_value: int = 5
var _contact_damage: int = 1
var _touch_cooldown: float = 0.0

@onready var _sprite: Sprite2D = $Sprite2D


func setup(hp: int, speed: float, xp_value: int, contact_damage: int) -> void:
	activate(hp, speed, xp_value, contact_damage)


func activate(hp: int, speed: float, xp_value: int, contact_damage: int) -> void:
	_hp = hp
	_speed = speed
	_xp_value = xp_value
	_contact_damage = contact_damage
	_touch_cooldown = 0.0
	_apply_theme()
	visible = true
	z_index = 5
	process_mode = Node.PROCESS_MODE_INHERIT
	monitoring = true
	monitorable = true


func deactivate() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_DISABLED
	monitoring = false
	monitorable = false


func _apply_theme() -> void:
	var sprite_path: String = SurvivorSpriteUtil.pick_enemy_sprite_path()
	SurvivorSpriteUtil.apply_sprite(_sprite, sprite_path, Vector2(1.0, 1.0))


func take_damage(amount: int) -> void:
	_hp -= amount
	if _hp <= 0:
		destroyed.emit(self, _xp_value)
		deactivate()


func _physics_process(delta: float) -> void:
	var player: Node2D = get_tree().get_first_node_in_group("player") as Node2D
	if player != null:
		var direction: Vector2 = player.global_position - global_position
		if direction.length_squared() > 1.0:
			var move_dir: Vector2 = direction.normalized()
			global_position += move_dir * _speed * delta
			SurvivorSpriteUtil.apply_facing_flip(_sprite, move_dir)
	if _touch_cooldown > 0.0:
		_touch_cooldown = maxf(0.0, _touch_cooldown - delta)


func _on_area_entered(area: Area2D) -> void:
	if _touch_cooldown > 0.0:
		return
	if area.is_in_group("player"):
		if area.has_method("take_hit"):
			area.call("take_hit", _contact_damage, global_position)
		_touch_cooldown = 0.6
