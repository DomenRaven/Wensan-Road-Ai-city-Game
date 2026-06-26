extends Node
class_name WaveScheduler

## Core locked: interval_spawn wave scheduler

signal enemy_spawn_requested(wave_index: int, spawn_index: int)
signal wave_started(wave_index: int)
signal wave_spawn_complete(wave_index: int)
signal all_waves_complete

var wave_count: int = 5
var spawn_interval_sec: float = 0.8
var enemies_per_wave_base: int = 3

var current_wave: int = 0
var _spawned_in_wave: int = 0
var _enemies_to_spawn: int = 0
var _timer: float = 0.0
var _state: String = "idle"


func configure(p_wave_count: int, p_spawn_interval_ms: int, p_enemies_base: int) -> void:
	wave_count = p_wave_count
	spawn_interval_sec = float(p_spawn_interval_ms) / 1000.0
	enemies_per_wave_base = p_enemies_base


func start(delay_sec: float = 1.5) -> void:
	_timer = delay_sec
	_state = "delay_before_wave"
	current_wave = 0


func _process(delta: float) -> void:
	match _state:
		"delay_before_wave":
			_timer -= delta
			if _timer <= 0.0:
				_start_wave()
		"spawning":
			_timer -= delta
			if _timer <= 0.0:
				enemy_spawn_requested.emit(current_wave, _spawned_in_wave)
				_spawned_in_wave += 1
				if _spawned_in_wave >= _enemies_to_spawn:
					_state = "waiting_clear"
					wave_spawn_complete.emit(current_wave)
				else:
					_timer = spawn_interval_sec
		"waiting_clear", "done", "idle":
			pass


func on_wave_cleared() -> void:
	if _state != "waiting_clear":
		return
	if current_wave >= wave_count:
		_state = "done"
		all_waves_complete.emit()
		return
	_timer = 2.0
	_state = "delay_before_wave"


func has_finished_all_waves() -> bool:
	return _state == "done"


func is_spawning_or_waiting() -> bool:
	return _state == "spawning" or _state == "waiting_clear" or _state == "delay_before_wave"


func _start_wave() -> void:
	current_wave += 1
	_spawned_in_wave = 0
	_enemies_to_spawn = enemies_per_wave_base + current_wave - 1
	wave_started.emit(current_wave)
	_timer = 0.0
	_state = "spawning"
