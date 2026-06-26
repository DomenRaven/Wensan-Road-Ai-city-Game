extends Node2D

var _manager: Node = null

@onready var _player: Area2D = $Player
@onready var _wave: Node2D = $WaveSpawner


func setup(manager: Node) -> void:
	_manager = manager
	if _player.has_signal("hp_changed"):
		_player.hp_changed.connect(_on_player_hp_changed)
	if _player.has_signal("died"):
		_player.died.connect(_on_player_died)
	if _wave.has_signal("wave_cleared"):
		_wave.wave_cleared.connect(_on_wave_cleared)
	if _wave.has_signal("enemy_destroyed"):
		_wave.enemy_destroyed.connect(_on_enemy_destroyed)
	if _wave.has_signal("all_waves_cleared"):
		_wave.all_waves_cleared.connect(_on_all_waves_cleared)


func _on_player_hp_changed(current_hp: int, max_hp: int) -> void:
	if _manager != null and _manager.has_method("update_hp"):
		_manager.call("update_hp", current_hp, max_hp)


func _on_player_died() -> void:
	if _manager != null and _manager.has_method("on_player_died"):
		_manager.call("on_player_died")


func _on_wave_cleared(wave_index: int) -> void:
	if _manager != null and _manager.has_method("on_wave_cleared"):
		_manager.call("on_wave_cleared", wave_index)


func _on_enemy_destroyed(score_value: int) -> void:
	if _manager != null and _manager.has_method("add_score"):
		_manager.call("add_score", score_value)


func _on_all_waves_cleared() -> void:
	if _manager != null and _manager.has_method("on_all_waves_cleared"):
		_manager.call("on_all_waves_cleared")
