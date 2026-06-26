extends Node

signal round_over(player_won: bool)

var _player: Node = null
var _enemy: Node = null
var _round_finished: bool = false
var _rounds_to_win: int = 1
var _player_round_wins: int = 0
var _enemy_round_wins: int = 0


func setup(player: Node, enemy: Node) -> void:
	_player = player
	_enemy = enemy
	var core: Dictionary = GameConfig.get_core()
	var combat: Dictionary = core.get("combat", {}) as Dictionary
	var rounds_mode: String = str(combat.get("rounds", "best_of_1"))
	_rounds_to_win = 1 if rounds_mode == "best_of_1" else 2
	_player.defeated.connect(_on_fighter_defeated)
	_enemy.defeated.connect(_on_fighter_defeated)
	_player.hp_changed.connect(_on_player_hp_changed)


func start_round() -> void:
	_round_finished = false
	_player.call("set_round_active", true)
	_enemy.call("set_round_active", true)


func _on_player_hp_changed(current_hp: int, max_hp: int) -> void:
	var manager: Node = get_parent()
	if manager != null and manager.has_method("update_hp_hud"):
		manager.call(
			"update_hp_hud",
			current_hp,
			max_hp,
			int(_enemy.get("current_hp")),
			int(_enemy.get("max_hp"))
		)


func _on_fighter_defeated(player_side_won: bool) -> void:
	if _round_finished:
		return
	_round_finished = true
	_player.call("set_round_active", false)
	_enemy.call("set_round_active", false)
	if player_side_won:
		_player_round_wins += 1
	else:
		_enemy_round_wins += 1
	var match_over: bool = _player_round_wins >= _rounds_to_win or _enemy_round_wins >= _rounds_to_win
	var player_won: bool = _player_round_wins >= _rounds_to_win
	if match_over:
		round_over.emit(player_won)
