extends Node2D

enum GameStatus { START, PLAYING, GAMEOVER }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")
const SpriteFramesUtil := preload("res://core/sprite_frames_util.gd")

var _status: GameStatus = GameStatus.START
var _game_instance: Node2D = null
var _starting: bool = false

@onready var _game_root: Node2D = $GameRoot
@onready var _hud: Control = $CanvasLayer/HUD
@onready var _distance_label: Label = $CanvasLayer/HUD/DistanceLabel
@onready var _coins_label: Label = $CanvasLayer/HUD/CoinsLabel
@onready var _time_label: Label = $CanvasLayer/HUD/TimeLabel
@onready var _invinc_label: Label = $CanvasLayer/HUD/InvincLabel
@onready var _double_label: Label = $CanvasLayer/HUD/DoubleLabel
@onready var _help_label: Label = $CanvasLayer/HUD/HelpLabel
@onready var _start_screen: Control = $CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _title_label: Label = $CanvasLayer/StartScreen/TitleLabel
@onready var _go_distance: Label = $CanvasLayer/GameOverScreen/Panel/VBox/StatsGrid/DistanceValue
@onready var _go_time: Label = $CanvasLayer/GameOverScreen/Panel/VBox/StatsGrid/TimeValue
@onready var _go_coins: Label = $CanvasLayer/GameOverScreen/Panel/VBox/StatsGrid/CoinsValue


func _ready() -> void:
	_title_label.text = GameConfig.get_display_name()
	_show_screen(GameStatus.START)
	_wire_buttons()
	call_deferred("_warmup_assets")


func _warmup_assets() -> void:
	SpriteFramesUtil.warmup(GameConfig.get_theme())


func _wire_buttons() -> void:
	$CanvasLayer/StartScreen/StartButton.pressed.connect(_on_start_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/RetryButton.pressed.connect(_on_restart_pressed)


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING


func _on_start_pressed() -> void:
	if _starting:
		return
	ThemeSoundUtil.play(self, "interface", "confirm")
	_begin_start_flow()


func _on_restart_pressed() -> void:
	if _starting:
		return
	ThemeSoundUtil.play(self, "interface", "confirm")
	_begin_start_flow()


func _begin_start_flow() -> void:
	_starting = true
	_start_screen.visible = false
	_game_over_screen.visible = false
	_hud.visible = true
	_help_label.visible = true
	_update_hud_zero()
	call_deferred("_start_run")


func _start_run() -> void:
	_clear_game()
	_load_game()
	_status = GameStatus.PLAYING
	_starting = false
	if _game_instance != null and _game_instance.has_method("start_run"):
		_game_instance.call_deferred("start_run")


func _clear_game() -> void:
	for child: Node in _game_root.get_children():
		_game_root.remove_child(child)
		child.queue_free()
	_game_instance = null


func _load_game() -> void:
	_game_instance = GAME_SCENE.instantiate() as Node2D
	_game_root.add_child(_game_instance)
	if _game_instance.has_method("setup"):
		_game_instance.call_deferred("setup", self)


func _update_hud_zero() -> void:
	update_run_hud(0, 0, 0, 0.0, 0.0)


func update_run_hud(
	distance_m: int,
	survival_sec: int,
	coins: int,
	invinc_ms: float,
	double_ms: float
) -> void:
	if _status != GameStatus.PLAYING:
		return
	_distance_label.text = "距离 %dm" % distance_m
	_coins_label.text = "金币 %d" % coins
	_time_label.text = "生存 %ds" % survival_sec
	_invinc_label.visible = invinc_ms > 0.0
	_double_label.visible = double_ms > 0.0
	if invinc_ms > 0.0:
		_invinc_label.text = "无敌 %.1fs" % (invinc_ms / 1000.0)
	if double_ms > 0.0:
		_double_label.text = "双倍金币 %.1fs" % (double_ms / 1000.0)


func on_run_over(distance_m: int, survival_sec: int, coins: int) -> void:
	_go_distance.text = "%dm" % distance_m
	_go_time.text = "%ds" % survival_sec
	_go_coins.text = "%d" % coins
	ThemeSoundUtil.play(self, "interface", "error")
	_show_screen(GameStatus.GAMEOVER)
