extends Node2D

signal level_won

const ThemeSoundUtil := preload("res://core/theme_sound.gd")

enum GameStatus { START, PLAYING, GAMEOVER, VICTORY }

const DEATH_FALL_MSG: String = "掉坑了！"
const DEATH_ENEMY_MSG: String = "碰到敌人了！"

var _status: GameStatus = GameStatus.START
var _score: int = 0
var _lives: int = 3
var _level_num: int = 1
var _coins: int = 0
var _max_lives: int = 3
var _invincible_sec: float = 1.5
var _score_coin: int = 10
var _score_stomp: int = 100
var _score_goal: int = 500
var _bounce_on_enemy: float = -300.0

var _player: CharacterBody2D = null
var _handling_death: bool = false
var _goal_reached: bool = false

@onready var _hud: Control = $CanvasLayer/HUD
@onready var _score_label: Label = $CanvasLayer/HUD/ScoreLabel
@onready var _coins_label: Label = $CanvasLayer/HUD/CoinsLabel
@onready var _level_label: Label = $CanvasLayer/HUD/LevelLabel
@onready var _lives_label: Label = $CanvasLayer/HUD/LivesLabel
@onready var _help_label: Label = $CanvasLayer/HUD/HelpLabel
@onready var _start_screen: Control = $CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _victory_screen: Control = $CanvasLayer/VictoryScreen
@onready var _title_label: Label = $CanvasLayer/StartScreen/TitleLabel
@onready var _go_score_label: Label = $CanvasLayer/GameOverScreen/Panel/VBox/ScoreValue
@onready var _vic_score_label: Label = $CanvasLayer/VictoryScreen/Panel/VBox/ScoreValue
@onready var _level_root: Node2D = $LevelRoot


func _ready() -> void:
	_apply_tuning()
	_apply_theme_ui()
	_show_screen(GameStatus.START)
	_wire_buttons()


func _apply_theme_ui() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var title: String = str(theme.get("title", GameConfig.get_display_name()))
	_title_label.text = title


func _apply_tuning() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var lives_cfg: Dictionary = tuning.get("lives", {}) as Dictionary
	var scoring_cfg: Dictionary = tuning.get("scoring", {}) as Dictionary
	var enemy_cfg: Dictionary = tuning.get("enemy", {}) as Dictionary
	_max_lives = int(lives_cfg.get("max", _max_lives))
	_invincible_sec = float(lives_cfg.get("invincible_sec", _invincible_sec))
	_score_coin = int(scoring_cfg.get("coin", _score_coin))
	_score_stomp = int(scoring_cfg.get("enemy_stomp", _score_stomp))
	_score_goal = int(scoring_cfg.get("goal", _score_goal))
	_bounce_on_enemy = float(enemy_cfg.get("bounce_on_stomp", _bounce_on_enemy))


func _wire_buttons() -> void:
	$CanvasLayer/StartScreen/StartButton.pressed.connect(_on_start_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/RetryButton.pressed.connect(_on_restart_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/MenuButton.pressed.connect(_on_menu_pressed)
	$CanvasLayer/VictoryScreen/Panel/VBox/NextButton.pressed.connect(_on_next_level_pressed)


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_victory_screen.visible = status == GameStatus.VICTORY
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING


func _on_start_pressed() -> void:
	_reset_run_state()
	_start_level()


func _on_restart_pressed() -> void:
	_reset_run_state()
	_start_level()


func _on_menu_pressed() -> void:
	_clear_level()
	_show_screen(GameStatus.START)


func _on_next_level_pressed() -> void:
	_level_num += 1
	_goal_reached = false
	_start_level()


func _reset_run_state() -> void:
	_score = 0
	_lives = _max_lives
	_level_num = 1
	_coins = 0
	_goal_reached = false
	_handling_death = false


func _start_level() -> void:
	_clear_level()
	_load_level()
	_show_screen(GameStatus.PLAYING)
	_update_hud()


func _clear_level() -> void:
	for child: Node in _level_root.get_children():
		child.queue_free()
	_player = null


func _load_level() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var level_cfg: Dictionary = tuning.get("level", {}) as Dictionary
	var scene_path: String = str(level_cfg.get("scene", "res://scenes/level_01.tscn"))
	if not ResourceLoader.exists(scene_path):
		push_error("GameManager: level scene missing: %s" % scene_path)
		return
	var packed: PackedScene = load(scene_path) as PackedScene
	var level: Node = packed.instantiate()
	if level.has_method("configure_level"):
		level.call("configure_level", _level_num)
	_level_root.add_child(level)


func register_player(player: CharacterBody2D) -> void:
	_player = player
	if player.has_method("configure_from_manager"):
		player.configure_from_manager(_bounce_on_enemy, _invincible_sec)
	if player.has_signal("died") and not player.died.is_connected(_on_player_died):
		player.died.connect(_on_player_died)


func register_goal(goal: Area2D) -> void:
	if goal.has_signal("reached") and not goal.reached.is_connected(_on_goal_reached):
		goal.reached.connect(_on_goal_reached)


func register_collectible(collectible: Area2D) -> void:
	if collectible.has_signal("collected") and not collectible.collected.is_connected(_on_collectible_collected):
		collectible.collected.connect(_on_collectible_collected)


func register_enemy(_enemy: CharacterBody2D) -> void:
	pass


func on_enemy_stomped() -> void:
	if _status != GameStatus.PLAYING:
		return
	_add_score(_score_stomp)
	ThemeSoundUtil.play(self, "impact", "hit")


func _on_collectible_collected() -> void:
	if _status != GameStatus.PLAYING:
		return
	_coins += 1
	_add_score(_score_coin)
	ThemeSoundUtil.play(self, "impact", "collect")


func _add_score(points: int) -> void:
	_score += points
	_update_hud()


func _on_goal_reached() -> void:
	if _status != GameStatus.PLAYING or _goal_reached:
		return
	_goal_reached = true
	_add_score(_score_goal)
	ThemeSoundUtil.play(self, "interface", "confirm")
	if _player != null and _player.has_method("freeze"):
		_player.freeze()
	await get_tree().create_timer(1.5).timeout
	_vic_score_label.text = str(_score)
	_show_screen(GameStatus.VICTORY)
	level_won.emit()


func _on_player_died(cause: String) -> void:
	if _status != GameStatus.PLAYING or _handling_death:
		return
	_begin_death(cause)


func _begin_death(cause: String) -> void:
	if _handling_death or _player == null:
		return
	_handling_death = true
	if _player.has_method("trigger_death"):
		_player.trigger_death(cause)
	if cause == "enemy":
		ThemeSoundUtil.play(self, "impact", "hit")
	ThemeSoundUtil.play(self, "interface", "error")
	await get_tree().create_timer(0.6).timeout
	_lives -= 1
	_update_hud()
	if _lives <= 0:
		_go_score_label.text = str(_score)
		_show_screen(GameStatus.GAMEOVER)
		_handling_death = false
		return
	if _player.has_method("respawn_with_invincibility"):
		_player.respawn_with_invincibility(cause)
	_handling_death = false


func _update_hud() -> void:
	_score_label.text = "分数  %06d" % _score
	_coins_label.text = "🍒 x %02d" % _coins
	_level_label.text = "关卡 %d" % _level_num
	var hearts: String = ""
	for _i: int in range(_lives):
		hearts += "♥"
	_lives_label.text = hearts


func get_bounce_on_enemy() -> float:
	return _bounce_on_enemy


func get_level_num() -> int:
	return _level_num


func is_playing() -> bool:
	return _status == GameStatus.PLAYING
