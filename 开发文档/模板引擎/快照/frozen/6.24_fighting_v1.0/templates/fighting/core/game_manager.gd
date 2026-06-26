extends Node2D

enum FlowStatus { MODE_SELECT, ROLE_SELECT, PLAYING, GAMEOVER }

const GAME_SCENE: PackedScene = preload("res://scenes/game.tscn")
const WarriorSheet := preload("res://core/warrior_sheet.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

var _status: FlowStatus = FlowStatus.MODE_SELECT
var _game_mode: String = "pve"
var _player_role: String = "Warrior_2"
var _enemy_role: String = "Warrior_3"
var _p1_pick: String = ""
var _winner_p1: bool = true
var _is_draw: bool = false
var _starting: bool = false
var _game_scene: Node2D = null
var _mp_flash_t: float = 0.0
var _last_p_mp: int = 0
var _last_p_max_mp: int = 100
var _last_e_mp: int = 0
var _last_e_max_mp: int = 100

const MP_COLOR_NORMAL: Color = Color(0.2, 0.45, 1.0, 1.0)
const MP_COLOR_FULL_A: Color = Color(0.45, 0.82, 1.0, 1.0)
const MP_COLOR_FULL_B: Color = Color(1.0, 1.0, 1.0, 1.0)

@onready var _game_root: Node2D = $GameRoot
@onready var _mode_screen: Control = $CanvasLayer/ModeScreen
@onready var _role_screen: Control = $CanvasLayer/RoleScreen
@onready var _battle_hud: Control = $CanvasLayer/BattleHUD
@onready var _game_over_screen: Control = $CanvasLayer/GameOverScreen
@onready var _title_label: Label = $CanvasLayer/ModeScreen/TitleLabel
@onready var _role_title: Label = $CanvasLayer/RoleScreen/RoleTitle
@onready var _result_label: Label = $CanvasLayer/GameOverScreen/ResultLabel
@onready var _p1_hp_bar: ColorRect = $CanvasLayer/BattleHUD/P1Panel/HpBar/Fill
@onready var _p1_mp_bar: ColorRect = $CanvasLayer/BattleHUD/P1Panel/MpBar/Fill
@onready var _p2_hp_bar: ColorRect = $CanvasLayer/BattleHUD/P2Panel/HpBar/Fill
@onready var _p2_mp_bar: ColorRect = $CanvasLayer/BattleHUD/P2Panel/MpBar/Fill
@onready var _w2_preview: TextureRect = $CanvasLayer/RoleScreen/W2Frame/W2Preview
@onready var _w3_preview: TextureRect = $CanvasLayer/RoleScreen/W3Frame/W3Preview
@onready var _w2_frame: PanelContainer = $CanvasLayer/RoleScreen/W2Frame
@onready var _w3_frame: PanelContainer = $CanvasLayer/RoleScreen/W3Frame
@onready var _background: ColorRect = $Background


func _ready() -> void:
	_apply_theme()
	_style_role_frames()
	_wire_buttons()
	_show_flow(FlowStatus.MODE_SELECT)
	call_deferred("_warmup_assets")


func _process(delta: float) -> void:
	if _status != FlowStatus.PLAYING:
		return
	_mp_flash_t += delta
	_update_mp_bar_flash(_p1_mp_bar, _last_p_mp >= _last_p_max_mp and _last_p_max_mp > 0)
	_update_mp_bar_flash(_p2_mp_bar, _last_e_mp >= _last_e_max_mp and _last_e_max_mp > 0)


func _update_mp_bar_flash(bar: ColorRect, is_full: bool) -> void:
	if is_full:
		var pulse: float = 0.5 + 0.5 * sin(_mp_flash_t * 10.0)
		bar.color = MP_COLOR_FULL_A.lerp(MP_COLOR_FULL_B, pulse)
	else:
		bar.color = MP_COLOR_NORMAL


func _warmup_assets() -> void:
	WarriorSheet.warmup("Warrior_2")
	WarriorSheet.warmup("Warrior_3")
	_apply_role_previews()


func _style_role_frames() -> void:
	_apply_frame_style(_w2_frame, Color(0.2, 0.45, 1.0, 1.0))
	_apply_frame_style(_w3_frame, Color(1.0, 0.25, 0.2, 1.0))


func _apply_frame_style(panel: PanelContainer, border_color: Color) -> void:
	var box: StyleBoxFlat = StyleBoxFlat.new()
	box.bg_color = Color(0.05, 0.07, 0.23, 0.95)
	box.border_color = border_color
	box.set_border_width_all(4)
	box.set_corner_radius_all(6)
	box.content_margin_left = 8.0
	box.content_margin_top = 8.0
	box.content_margin_right = 8.0
	box.content_margin_bottom = 8.0
	panel.add_theme_stylebox_override("panel", box)


func _apply_role_previews() -> void:
	var w2_tex: Texture2D = WarriorSheet.load_idle_preview("Warrior_2")
	var w3_tex: Texture2D = WarriorSheet.load_idle_preview("Warrior_3")
	if w2_tex != null:
		_w2_preview.texture = w2_tex
		_w2_preview.modulate = Color(0.75, 0.88, 1.0, 1.0)
	if w3_tex != null:
		_w3_preview.texture = w3_tex
		_w3_preview.modulate = Color(1.0, 0.72, 0.72, 1.0)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	_background.color = Color.from_string(str(theme.get("bg_bottom", "#0D113A")), Color(0.05, 0.07, 0.23))
	_title_label.text = str(theme.get("title", "K12 街机格斗"))


func _wire_buttons() -> void:
	$CanvasLayer/ModeScreen/PveButton.pressed.connect(_on_pve_pressed)
	$CanvasLayer/ModeScreen/PvpButton.pressed.connect(_on_pvp_pressed)
	$CanvasLayer/RoleScreen/W2Button.pressed.connect(func() -> void: _on_role_pressed("Warrior_2"))
	$CanvasLayer/RoleScreen/W3Button.pressed.connect(func() -> void: _on_role_pressed("Warrior_3"))
	$CanvasLayer/GameOverScreen/AgainButton.pressed.connect(_on_again_pressed)


func _show_flow(status: FlowStatus) -> void:
	_status = status
	_mode_screen.visible = status == FlowStatus.MODE_SELECT
	_role_screen.visible = status == FlowStatus.ROLE_SELECT
	_battle_hud.visible = status == FlowStatus.PLAYING
	_game_over_screen.visible = status == FlowStatus.GAMEOVER


func _on_pve_pressed() -> void:
	ThemeSoundUtil.play(self, "interface", "confirm")
	_game_mode = "pve"
	_p1_pick = ""
	_show_flow(FlowStatus.ROLE_SELECT)
	_role_title.text = "选择角色"


func _on_pvp_pressed() -> void:
	ThemeSoundUtil.play(self, "interface", "confirm")
	_game_mode = "pvp"
	_p1_pick = ""
	_show_flow(FlowStatus.ROLE_SELECT)
	_role_title.text = "P1 请选择角色"


func _on_role_pressed(role: String) -> void:
	ThemeSoundUtil.play(self, "interface", "select")
	if _game_mode == "pve":
		_player_role = role
		_enemy_role = "Warrior_3" if role == "Warrior_2" else "Warrior_2"
		_begin_match()
		return
	if _p1_pick == "":
		_p1_pick = role
		_player_role = role
		_role_title.text = "P2 请选择角色"
		return
	_enemy_role = role
	_begin_match()


func _begin_match() -> void:
	if _starting:
		return
	_starting = true
	_show_flow(FlowStatus.PLAYING)
	call_deferred("_start_match")


func _start_match() -> void:
	_clear_game()
	_game_scene = GAME_SCENE.instantiate() as Node2D
	_game_root.add_child(_game_scene)
	if _game_scene.has_method("setup"):
		_game_scene.call_deferred("setup", self, _game_mode, _player_role, _enemy_role)
	if _game_scene.has_signal("match_over"):
		_game_scene.match_over.connect(_on_match_over)
	_starting = false
	update_battle_hud(100, 100, 100, 100, 0, 100, 0, 100)


func _clear_game() -> void:
	for child: Node in _game_root.get_children():
		_game_root.remove_child(child)
		child.queue_free()
	_game_scene = null


func update_battle_hud(
	p_hp: int,
	p_max_hp: int,
	e_hp: int,
	e_max_hp: int,
	p_mp: int,
	p_max_mp: int,
	e_mp: int,
	e_max_mp: int
) -> void:
	_last_p_mp = p_mp
	_last_p_max_mp = p_max_mp
	_last_e_mp = e_mp
	_last_e_max_mp = e_max_mp
	_set_bar(_p1_hp_bar, float(p_hp) / float(maxi(1, p_max_hp)), true)
	_set_bar(_p1_mp_bar, float(p_mp) / float(maxi(1, p_max_mp)), true)
	_set_bar(_p2_hp_bar, float(e_hp) / float(maxi(1, e_max_hp)), false)
	_set_bar(_p2_mp_bar, float(e_mp) / float(maxi(1, e_max_mp)), false)


func _set_bar(bar: ColorRect, ratio: float, grow_left: bool) -> void:
	ratio = clampf(ratio, 0.0, 1.0)
	var full_w: float = 200.0 if bar.get_parent().name == "HpBar" else 150.0
	bar.size.x = full_w * ratio
	if grow_left:
		bar.position.x = 0.0
	else:
		bar.position.x = full_w - bar.size.x


func _on_match_over(player_one_won: bool, is_draw: bool) -> void:
	_winner_p1 = player_one_won
	_is_draw = is_draw
	_show_flow(FlowStatus.GAMEOVER)
	if is_draw:
		_result_label.text = "平局"
	elif player_one_won:
		_result_label.text = "玩家1 胜利！"
	else:
		if _game_mode == "pvp":
			_result_label.text = "玩家2 胜利！"
		else:
			_result_label.text = "KO！"


func _on_again_pressed() -> void:
	ThemeSoundUtil.play(self, "interface", "click")
	_clear_game()
	_p1_pick = ""
	_show_flow(FlowStatus.MODE_SELECT)
