extends "res://core/enemy_patrol_base.gd"

## 橙怪：0.5× 移速 · 周期性跳跃（高度 = 玩家 0.6×）
const ORANGE_COLOR: Color = Color(0.95, 0.55, 0.1, 1.0)

var _jump_velocity: float = -240.0
var _jump_interval: float = 2.2
var _jump_timer: float = 0.0


func _ready() -> void:
	super._ready()
	_jump_timer = _jump_interval * randf()


func _apply_tuning() -> void:
	super._apply_tuning()
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var jumper_cfg: Dictionary = types_cfg.get("jumper", {}) as Dictionary
	var player_cfg: Dictionary = tuning.get("player", {}) as Dictionary
	var speed_mult: float = float(jumper_cfg.get("speed_mult", 0.5))
	var jump_mult: float = float(jumper_cfg.get("jump_mult", 0.8))
	_patrol_speed = _patrol_speed * speed_mult
	var player_jump: float = float(player_cfg.get("jump_velocity", -400.0))
	_jump_velocity = player_jump * jump_mult
	_jump_interval = float(jumper_cfg.get("jump_interval", _jump_interval))


func _get_enemy_color() -> Color:
	return ORANGE_COLOR


func _patrol_move(delta: float) -> void:
	_jump_timer -= delta
	if is_on_floor() and _jump_timer <= 0.0:
		velocity.y = _jump_velocity
		_jump_timer = _jump_interval
	super._patrol_move(delta)
