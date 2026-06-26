extends Node2D

enum GameStatus { START, PLAYING, GAMEOVER, VICTORY }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _status: GameStatus = GameStatus.START
var _level: int = 1
var _survive_seconds: int = 0
var _boss_seconds: int = 0
var _starting: bool = false
var _game_scene: Node2D = null
var _shake_timer: float = 0.0
var _shake_strength: float = 0.0

@onready var _game_root: Node2D = $GameRoot
@onready var _hud: Control = $CanvasLayer/HUD
@onready var _info_label: Label = $CanvasLayer/HUD/InfoLabel
@onready var _exp_bar_bg: ColorRect = $CanvasLayer/HUD/ExpBarBg
@onready var _exp_bar_fill: ColorRect = $CanvasLayer/HUD/ExpBarFill
@onready var _start_screen: Control = $CanvasLayer/StartScreen
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _victory_screen: Control = $CanvasLayer/VictoryScreen
@onready var _title_label: Label = $CanvasLayer/StartScreen/TitleLabel
@onready var _help_label: Label = $CanvasLayer/HUD/HelpLabel
@onready var _go_time_label: Label = $CanvasLayer/GameOverScreen/Panel/VBox/TimeValue
@onready var _vic_level_label: Label = $CanvasLayer/VictoryScreen/Panel/VBox/LevelValue
@onready var _vic_time_label: Label = $CanvasLayer/VictoryScreen/Panel/VBox/TimeValue
@onready var _boss_bar_panel: Control = $CanvasLayer/HUD/BossBarPanel
@onready var _boss_bar_fill: ColorRect = $CanvasLayer/HUD/BossBarPanel/Fill
@onready var _boss_bar_label: Label = $CanvasLayer/HUD/BossBarPanel/BarLabel
@onready var _toast_label: Label = $CanvasLayer/HUD/ToastLabel
@onready var _player_hp_bg: ColorRect = $CanvasLayer/HUD/PlayerHpBarPanel/BarBg
@onready var _player_hp_fill: ColorRect = $CanvasLayer/HUD/PlayerHpBarPanel/Fill
@onready var _player_hp_label: Label = $CanvasLayer/HUD/PlayerHpBarPanel/BarLabel


func _ready() -> void:
	_title_label.text = GameConfig.get_display_name()
	_show_screen(GameStatus.START)
	_wire_buttons()
	_toast_label.visible = false
	call_deferred("_warmup_assets")


func _warmup_assets() -> void:
	var SurvivorSpriteUtil := preload("res://core/survivor_sprite_util.gd")
	var theme: Dictionary = GameConfig.get_theme()
	SurvivorSpriteUtil.load_texture(str(theme.get("player_sprite", "")))
	if theme.has("enemy_sprites") and theme["enemy_sprites"] is Array:
		for path: Variant in theme["enemy_sprites"] as Array:
			SurvivorSpriteUtil.load_texture(str(path))
	SurvivorSpriteUtil.bullet_texture()
	SurvivorSpriteUtil.load_texture(str(theme.get("xp_gem_sprite", "")))


func _wire_buttons() -> void:
	$CanvasLayer/StartScreen/StartButton.pressed.connect(_on_start_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/RetryButton.pressed.connect(_on_restart_pressed)
	$CanvasLayer/GameOverScreen/Panel/VBox/Buttons/MenuButton.pressed.connect(_on_menu_pressed)
	$CanvasLayer/VictoryScreen/Panel/VBox/Buttons/RetryButton.pressed.connect(_on_restart_pressed)
	$CanvasLayer/VictoryScreen/Panel/VBox/Buttons/MenuButton.pressed.connect(_on_menu_pressed)


func _show_screen(status: GameStatus) -> void:
	_status = status
	_start_screen.visible = status == GameStatus.START
	_game_over_screen.visible = status == GameStatus.GAMEOVER
	_victory_screen.visible = status == GameStatus.VICTORY
	_hud.visible = status == GameStatus.PLAYING
	_help_label.visible = status == GameStatus.PLAYING
	if status != GameStatus.PLAYING:
		set_boss_bar_visible(false)


func _on_start_pressed() -> void:
	if _starting:
		return
	_reset_run_state()
	_begin_start_flow()


func _on_restart_pressed() -> void:
	if _starting:
		return
	_reset_run_state()
	_begin_start_flow()


func _on_menu_pressed() -> void:
	_clear_game()
	_starting = false
	_show_screen(GameStatus.START)


func _reset_run_state() -> void:
	_level = 1
	_survive_seconds = 0
	_boss_seconds = 0


func _begin_start_flow() -> void:
	_starting = true
	_start_screen.visible = false
	_game_over_screen.visible = false
	_victory_screen.visible = false
	_hud.visible = true
	_help_label.visible = true
	call_deferred("_start_game")


func _start_game() -> void:
	_clear_game()
	_game_scene = GAME_SCENE.instantiate() as Node2D
	_game_root.add_child(_game_scene)
	if _game_scene.has_method("setup"):
		_game_scene.call_deferred("setup", self)
	_status = GameStatus.PLAYING
	_starting = false


func _clear_game() -> void:
	for child: Node in _game_root.get_children():
		_game_root.remove_child(child)
		child.queue_free()
	_game_scene = null
	_game_root.position = Vector2.ZERO


func is_playing() -> bool:
	return _status == GameStatus.PLAYING


func update_session_hud(
	level: int,
	xp: int,
	xp_to_next: int,
	time_left: float,
	_phase_label: String,
	current_hp: int,
	max_hp: int,
	in_boss: bool
) -> void:
	if _status != GameStatus.PLAYING:
		return
	_level = level
	var title: String = str(GameConfig.get_theme().get("title", GameConfig.get_display_name()))
	var time_text: String = "Boss战" if in_boss else "剩余 %ds" % int(ceil(time_left))
	_info_label.text = "%s  Lv.%d  生命 %d/%d  %s" % [title, level, current_hp, max_hp, time_text]
	var ratio: float = clampf(float(xp) / maxf(1.0, float(xp_to_next)), 0.0, 1.0)
	var bar_width: float = maxf(8.0, (_exp_bar_bg.size.x - 4.0) * ratio)
	_exp_bar_fill.size.x = bar_width
	update_hp(current_hp, max_hp)
	if in_boss:
		_survive_seconds = int(GameConfig.get_tuning().get("session", {}).get("duration_sec", 180))
	else:
		var duration: int = int(GameConfig.get_tuning().get("session", {}).get("duration_sec", 180))
		_survive_seconds = duration - int(ceil(time_left))


func set_boss_bar_visible(visible_flag: bool) -> void:
	_boss_bar_panel.visible = visible_flag


func update_boss_bar(current_hp: int, max_hp: int) -> void:
	if max_hp <= 0:
		return
	var ratio: float = clampf(float(current_hp) / float(max_hp), 0.0, 1.0)
	var width: float = maxf(4.0, (_boss_bar_panel.size.x - 4.0) * ratio)
	_boss_bar_fill.size.x = width
	_boss_bar_label.text = "BOSS  %d / %d" % [current_hp, max_hp]


func show_boss_heal_toast() -> void:
	_toast_label.text = "boss的力量回复了!"
	_toast_label.visible = true
	_toast_label.modulate = Color(1, 1, 1, 1)
	var tween: Tween = create_tween()
	tween.tween_property(_toast_label, "modulate:a", 0.0, 2.0).set_delay(0.6)
	tween.finished.connect(func() -> void:
		_toast_label.visible = false
		_toast_label.modulate = Color(1, 1, 1, 1)
	)


func update_hp(current_hp: int, max_hp: int) -> void:
	if max_hp <= 0:
		return
	var ratio: float = clampf(float(current_hp) / float(max_hp), 0.0, 1.0)
	var width: float = maxf(4.0, (_player_hp_bg.size.x - 4.0) * ratio)
	_player_hp_fill.size.x = width
	_player_hp_label.text = "生命 %d / %d" % [current_hp, max_hp]
	if ratio <= 0.25:
		_player_hp_fill.color = Color(0.95, 0.25, 0.25, 1.0)
	elif ratio <= 0.5:
		_player_hp_fill.color = Color(1.0, 0.72, 0.2, 1.0)
	else:
		_player_hp_fill.color = Color(0.26, 0.84, 0.64, 1.0)


func on_player_died() -> void:
	if _status != GameStatus.PLAYING:
		return
	_status = GameStatus.GAMEOVER
	var total: int = _survive_seconds + _boss_seconds
	_go_time_label.text = "存活 %d 秒" % total
	_show_screen(GameStatus.GAMEOVER)


func on_session_won(final_level: int) -> void:
	if _status != GameStatus.PLAYING:
		return
	_status = GameStatus.VICTORY
	var total: int = _survive_seconds + _boss_seconds
	_vic_level_label.text = "等级 %d" % final_level
	_vic_time_label.text = "存活 %d 秒" % total
	_show_screen(GameStatus.VICTORY)
	ThemeSoundUtil.play(self, "interface", "confirm")


func increment_boss_time() -> void:
	_boss_seconds += 1


func shake_screen(duration: float, strength: float) -> void:
	_shake_timer = duration
	_shake_strength = strength


func _process(delta: float) -> void:
	if _shake_timer <= 0.0:
		_game_root.position = Vector2.ZERO
		return
	_shake_timer = maxf(0.0, _shake_timer - delta)
	var offset: Vector2 = Vector2(
		randf_range(-_shake_strength, _shake_strength),
		randf_range(-_shake_strength, _shake_strength)
	)
	_game_root.position = offset
