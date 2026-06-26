extends "res://core/enemy_patrol_base.gd"

## 紫怪：需踩两次；首次踩头停顿 0.6s + 闪烁
const PURPLE_COLOR: Color = Color(0.58, 0.2, 0.82, 1.0)

var _stomp_hits: int = 0
var _stomp_required: int = 2
var _stun_sec: float = 0.6


func _apply_tuning() -> void:
	super._apply_tuning()
	var tuning: Dictionary = GameConfig.get_tuning()
	var types_cfg: Dictionary = tuning.get("enemy_types", {}) as Dictionary
	var tough_cfg: Dictionary = types_cfg.get("tough", {}) as Dictionary
	_stomp_required = int(tough_cfg.get("stomp_hits", _stomp_required))
	_stun_sec = float(tough_cfg.get("stun_sec", _stun_sec))


func _get_enemy_color() -> Color:
	return PURPLE_COLOR


func on_stomped() -> bool:
	if not _alive:
		return false
	_stomp_hits += 1
	if _stomp_hits < _stomp_required:
		_start_stun_flash()
		return false
	_kill_enemy()
	return true


func _start_stun_flash() -> void:
	_pause_movement(_stun_sec)
	if _sprite == null:
		return
	var tween: Tween = create_tween()
	tween.set_loops(int(_stun_sec / 0.08))
	tween.tween_property(_sprite, "modulate", Color(1.0, 1.0, 1.0, 0.25), 0.04)
	tween.tween_property(_sprite, "modulate", PURPLE_COLOR, 0.04)


func _on_movement_pause_done() -> void:
	_movement_paused = false
	if _sprite != null:
		_sprite.modulate = PURPLE_COLOR
