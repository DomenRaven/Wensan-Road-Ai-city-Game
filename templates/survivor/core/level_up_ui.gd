extends CanvasLayer

signal choice_selected(choice_id: String)

const ALL_CHOICES: Array[String] = [
	"attack_speed",
	"attack_damage",
	"move_speed",
	"multi_shot",
	"max_hp",
	"hp_regen"
]
const CHOICE_META: Dictionary = {
	"attack_speed": {"title": "攻击速度", "desc": "攻击间隔 -20%"},
	"attack_damage": {"title": "攻击伤害", "desc": "基础伤害 +5"},
	"move_speed": {"title": "移动速度", "desc": "移速 +10%"},
	"multi_shot": {"title": "连发提升", "desc": "一次多 +1 发"},
	"max_hp": {"title": "血量上限", "desc": "最大生命 +50"},
	"hp_regen": {"title": "自动回血", "desc": "每秒回复 +1"}
}
const CARD_NORMAL_COLOR: Color = Color(0.99, 0.98, 0.96, 1.0)
const CARD_HOVER_COLOR: Color = Color(0.22, 0.78, 0.58, 1.0)
const TEXT_NORMAL_COLOR: Color = Color(0.15, 0.15, 0.15, 1.0)
const TEXT_HOVER_COLOR: Color = Color(1.0, 1.0, 1.0, 1.0)

var _current_choices: Array[String] = []
var _backdrop: ColorRect = null
var _title: Label = null
var _choice_buttons: Array[Button] = []
var _choice_cards: Array[PanelContainer] = []


func _ready() -> void:
	visible = false
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 20
	_build_ui()


func _build_ui() -> void:
	_backdrop = ColorRect.new()
	_backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	_backdrop.color = Color(0.12, 0.12, 0.14, 0.82)
	_backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_backdrop)

	var center: CenterContainer = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var root: VBoxContainer = VBoxContainer.new()
	root.add_theme_constant_override("separation", 18)
	center.add_child(root)

	_title = Label.new()
	_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title.add_theme_font_size_override("font_size", 28)
	_title.add_theme_color_override("font_color", Color(0.99, 0.98, 0.96, 1.0))
	_title.add_theme_color_override("font_outline_color", Color(0.2, 0.2, 0.2, 1.0))
	_title.add_theme_constant_override("outline_size", 4)
	_title.text = "等级提升！"
	root.add_child(_title)

	var row: HBoxContainer = HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_theme_constant_override("separation", 16)
	root.add_child(row)

	for _i: int in 3:
		var card: PanelContainer = PanelContainer.new()
		card.custom_minimum_size = Vector2(170, 190)
		card.add_theme_stylebox_override("panel", _make_card_style(CARD_NORMAL_COLOR))
		row.add_child(card)
		_choice_cards.append(card)

		var btn: Button = Button.new()
		btn.flat = true
		btn.custom_minimum_size = Vector2(162, 182)
		btn.focus_mode = Control.FOCUS_NONE
		btn.add_theme_color_override("font_color", TEXT_NORMAL_COLOR)
		btn.add_theme_color_override("font_hover_color", TEXT_HOVER_COLOR)
		btn.add_theme_color_override("font_pressed_color", TEXT_HOVER_COLOR)
		btn.add_theme_font_size_override("font_size", 16)
		var empty_style: StyleBoxEmpty = StyleBoxEmpty.new()
		btn.add_theme_stylebox_override("normal", empty_style)
		btn.add_theme_stylebox_override("hover", empty_style)
		btn.add_theme_stylebox_override("pressed", empty_style)
		var idx: int = _choice_buttons.size()
		btn.pressed.connect(_on_choice.bind(idx))
		btn.mouse_entered.connect(_on_card_hover.bind(idx, true))
		btn.mouse_exited.connect(_on_card_hover.bind(idx, false))
		card.add_child(btn)
		_choice_buttons.append(btn)


func _make_card_style(bg_color: Color) -> StyleBoxFlat:
	var card_style: StyleBoxFlat = StyleBoxFlat.new()
	card_style.bg_color = bg_color
	card_style.border_color = Color(0.15, 0.15, 0.15, 1.0)
	card_style.set_border_width_all(4)
	card_style.set_corner_radius_all(18)
	card_style.shadow_color = Color(0, 0, 0, 0.25)
	card_style.shadow_size = 6
	return card_style


func _on_card_hover(index: int, hovered: bool) -> void:
	if index < 0 or index >= _choice_cards.size():
		return
	var card: PanelContainer = _choice_cards[index]
	var btn: Button = _choice_buttons[index]
	card.add_theme_stylebox_override("panel", _make_card_style(CARD_HOVER_COLOR if hovered else CARD_NORMAL_COLOR))
	btn.add_theme_color_override("font_color", TEXT_HOVER_COLOR if hovered else TEXT_NORMAL_COLOR)


func show_choices(level: int) -> void:
	_title.text = "等级提升！Lv.%d" % level
	var shuffled: Array[String] = ALL_CHOICES.duplicate()
	shuffled.shuffle()
	_current_choices = shuffled.slice(0, 3)
	for i: int in _choice_buttons.size():
		var choice_id: String = _current_choices[i]
		var meta: Dictionary = CHOICE_META.get(choice_id, {}) as Dictionary
		var title: String = str(meta.get("title", choice_id))
		var desc: String = str(meta.get("desc", ""))
		_choice_buttons[i].text = "%s\n\n%s" % [title, desc]
		_on_card_hover(i, false)
	visible = true
	get_tree().paused = true


func hide_choices() -> void:
	visible = false
	get_tree().paused = false


func _on_choice(index: int) -> void:
	if index < 0 or index >= _current_choices.size():
		return
	choice_selected.emit(_current_choices[index])
	hide_choices()
