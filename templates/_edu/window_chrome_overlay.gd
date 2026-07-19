extends CanvasLayer

## 展厅 · 无边框全屏时的窗口控件（关闭 / 小窗）
## 独立高 layer，避免被 HUD / 触控层在游戏中抢走点击。
## 由 edu_workspace 注入到 workspace，不修改 templates/*/core 源文件。

const BTN_MIN: Vector2 = Vector2(36, 20)
const FONT_SIZE: int = 8
const WINDOWED_SIZE: Vector2i = Vector2i(960, 540)
const CHROME_LAYER: int = 128

var _root: Control = null
var _bar: HBoxContainer = null


func _ready() -> void:
	layer = CHROME_LAYER
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_chrome()
	# 启动即边框全屏铺满（勿依赖外置 Win32 竞态）；置顶由 DisplayServer + 后端 HWND_TOPMOST 双保险
	call_deferred("_apply_exhibition_fullscreen")


func _apply_exhibition_fullscreen() -> void:
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
	# 展厅要「可置顶」：用无边框窗口铺满显示器，避免 MODE_EXCLUSIVE_FULLSCREEN 丢掉 always_on_top
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	var screen: Vector2i = DisplayServer.screen_get_size()
	var origin: Vector2i = DisplayServer.screen_get_position()
	DisplayServer.window_set_position(origin)
	DisplayServer.window_set_size(screen)


func _build_chrome() -> void:
	_root = Control.new()
	_root.name = "WindowChromeRoot"
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)

	_bar = HBoxContainer.new()
	_bar.name = "WindowChromeBar"
	_bar.position = Vector2(12, 12)
	_bar.add_theme_constant_override("separation", 4)
	_bar.mouse_filter = Control.MOUSE_FILTER_STOP
	# 固定命中区域，避免 HBox 未排版时 size 为 0（仅关闭 + 小窗）
	_bar.custom_minimum_size = Vector2(BTN_MIN.x * 2.0 + 4.0, BTN_MIN.y)
	_root.add_child(_bar)

	_add_btn("✕ 关闭", _on_close)
	_add_btn("❐ 小窗", _on_windowed)


func _add_btn(label: String, handler: Callable) -> void:
	var btn: Button = Button.new()
	btn.text = label
	btn.custom_minimum_size = BTN_MIN
	btn.focus_mode = Control.FOCUS_NONE
	btn.mouse_filter = Control.MOUSE_FILTER_STOP
	btn.process_mode = Node.PROCESS_MODE_ALWAYS
	btn.add_theme_font_size_override("font_size", FONT_SIZE)
	btn.add_theme_color_override("font_color", Color(0.95, 0.98, 1.0, 1.0))
	btn.add_theme_color_override("font_hover_color", Color(1.0, 1.0, 1.0, 1.0))
	btn.add_theme_stylebox_override("normal", _make_style(Color(0.08, 0.14, 0.28, 0.82)))
	btn.add_theme_stylebox_override("hover", _make_style(Color(0.12, 0.35, 0.72, 0.92)))
	btn.add_theme_stylebox_override("pressed", _make_style(Color(0.06, 0.22, 0.5, 0.95)))
	btn.pressed.connect(handler)
	_bar.add_child(btn)


func _make_style(bg: Color) -> StyleBoxFlat:
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = bg
	style.set_corner_radius_all(5)
	style.set_content_margin_all(4)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.35, 0.65, 1.0, 0.55)
	return style


func _on_close() -> void:
	get_tree().quit()


func _on_windowed() -> void:
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, false)
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	DisplayServer.window_set_size(WINDOWED_SIZE)
	var screen: Vector2i = DisplayServer.screen_get_size()
	var pos: Vector2i = Vector2i(
		maxi(0, (screen.x - WINDOWED_SIZE.x) / 2),
		maxi(0, (screen.y - WINDOWED_SIZE.y) / 2)
	)
	DisplayServer.window_set_position(pos)
