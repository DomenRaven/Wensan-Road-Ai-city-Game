extends Area2D

signal collected(value: int)

const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")

var _gem_value: int = 5
var _magnet_speed: float = 320.0
var _magnet_range: float = 64.0
var _magnet_range_multiplier: float = 1.0
var _collected: bool = false

@onready var _sprite: Sprite2D = $Sprite2D


func setup(value: int, magnet_range: float) -> void:
	activate(value, magnet_range, 1.0)


func activate(value: int, magnet_range: float, magnet_multiplier: float) -> void:
	_gem_value = value
	_magnet_range = magnet_range
	_magnet_range_multiplier = maxf(0.5, magnet_multiplier)
	_collected = false
	_apply_theme()
	visible = true
	process_mode = Node.PROCESS_MODE_INHERIT
	monitoring = true
	monitorable = true


func deactivate() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_DISABLED
	monitoring = false
	monitorable = false
	_collected = true


func set_magnet_multiplier(multiplier: float) -> void:
	_magnet_range_multiplier = maxf(0.5, multiplier)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var sprite_path: String = str(theme.get("xp_gem_sprite", ""))
	SurvivorSpriteUtil.apply_sprite(_sprite, sprite_path, Vector2(1.6, 1.6))


func _physics_process(delta: float) -> void:
	if _collected:
		return
	var player: Node2D = get_tree().get_first_node_in_group("player") as Node2D
	if player == null:
		return
	var effective_range: float = _magnet_range * _magnet_range_multiplier
	var to_player: Vector2 = player.global_position - global_position
	var dist: float = to_player.length()
	if dist <= effective_range:
		if dist < 8.0:
			_collect()
			return
		global_position += to_player.normalized() * _magnet_speed * delta


func _collect() -> void:
	if _collected:
		return
	_collected = true
	ThemeSoundUtil.play(self, "impact", "collect")
	collected.emit(_gem_value)
	deactivate()


func _on_area_entered(area: Area2D) -> void:
	if _collected:
		return
	if area.is_in_group("player"):
		_collect()
