extends Node2D

const _InstantGrowSkill = preload("res://core/skills/instant_grow.gd")
const _SpeedCookSkill = preload("res://core/skills/speed_cook.gd")
const _TaskChain = preload("res://core/task_chain.gd")
const _Inventory = preload("res://core/inventory.gd")
const _OrderQueue = preload("res://core/order_queue.gd")
const _ThemeSprite = preload("res://core/theme_sprite.gd")
const _HotspotManager = preload("res://core/hotspot_manager.gd")
const _TimerBar = preload("res://core/timer_bar.gd")
const ThemeSoundUtil := preload("res://core/theme_sound.gd")

signal hud_changed(payload: Dictionary)
signal order_completed(payout: int, total_orders: int)
signal game_won(coins: int)

enum FarmState { EMPTY, GROWING, READY }

var _crop_id: String = "生菜"
var _dish_id: String = "田园沙拉"
var _grow_time_sec: float = 8.0
var _cook_time_sec: float = 5.0

var _task_chain = _TaskChain.new()
var _inventory = _Inventory.new()
var _orders = _OrderQueue.new()

var _farm_state: FarmState = FarmState.EMPTY
var _grow_elapsed: float = 0.0
var _cook_elapsed: float = 0.0
var _is_cooking: bool = false
var _game_over: bool = false

var _grow_cooldown_left: float = 0.0
var _cook_cooldown_left: float = 0.0

@onready var _farm_area: Area2D = $FarmSpot
@onready var _stove_area: Area2D = $StoveSpot
@onready var _customer_area: Area2D = $CustomerSpot
@onready var _grow_bar: ProgressBar = $FarmSpot/GrowBar
@onready var _cook_bar: ProgressBar = $StoveSpot/CookBar
@onready var _patience_bar: ProgressBar = $CustomerSpot/PatienceBar
@onready var _order_label: Label = $CustomerSpot/OrderLabel


func _ready() -> void:
	_load_config()
	_apply_theme()
	_setup_collision_shapes()
	_bind_hotspots()
	_reset_round()
	_emit_hud()


func _setup_collision_shapes() -> void:
	_apply_rect_collision(_farm_area, Vector2(80.0, 60.0))
	_apply_rect_collision(_stove_area, Vector2(88.0, 56.0))
	_apply_rect_collision(_customer_area, Vector2(72.0, 72.0))


func _apply_rect_collision(area: Area2D, size: Vector2) -> void:
	var shape_node: CollisionShape2D = area.get_node("CollisionShape2D") as CollisionShape2D
	var rect: RectangleShape2D = RectangleShape2D.new()
	rect.size = size
	shape_node.shape = rect


func _load_config() -> void:
	var tuning: Dictionary = GameConfig.get_tuning()
	var crop_cfg: Dictionary = tuning.get("crop", {}) as Dictionary
	var cook_cfg: Dictionary = tuning.get("cook", {}) as Dictionary
	var order_cfg: Dictionary = tuning.get("order", {}) as Dictionary
	var reward_cfg: Dictionary = tuning.get("reward", {}) as Dictionary
	var items_cfg: Dictionary = tuning.get("items", {}) as Dictionary
	_grow_time_sec = float(crop_cfg.get("grow_time_sec", _grow_time_sec))
	_cook_time_sec = float(cook_cfg.get("time_sec", _cook_time_sec))
	_crop_id = str(items_cfg.get("crop_id", _crop_id))
	_dish_id = str(items_cfg.get("dish_id", _dish_id))
	_orders.configure(
		_dish_id,
		int(order_cfg.get("count_to_win", 3)),
		float(order_cfg.get("patience_sec", 30.0)),
		int(reward_cfg.get("coins_per_order", 10))
	)


func _apply_theme() -> void:
	var theme: Dictionary = GameConfig.get_theme()
	var bg_hex: String = str(theme.get("background_color", "#87c9a8"))
	$Background.color = Color.from_string(bg_hex, Color(0.53, 0.79, 0.66))
	_ThemeSprite.apply_to_sprite(
		$FarmSpot/Sprite as Sprite2D,
		str(theme.get("farm_sprite", "")),
		Color(0.35, 0.72, 0.38),
		Vector2i(40, 40)
	)
	_ThemeSprite.apply_to_sprite(
		$StoveSpot/Sprite as Sprite2D,
		str(theme.get("stove_sprite", "")),
		Color(0.75, 0.45, 0.25),
		Vector2i(44, 36)
	)
	_ThemeSprite.apply_to_sprite(
		$CustomerSpot/Sprite as Sprite2D,
		str(theme.get("customer_sprite", "")),
		Color(0.45, 0.62, 0.95),
		Vector2i(28, 48)
	)


func _bind_hotspots() -> void:
	_HotspotManager.bind(_farm_area, _on_farm_input)
	_HotspotManager.bind(_stove_area, _on_stove_input)
	_HotspotManager.bind(_customer_area, _on_customer_input)


func _reset_round() -> void:
	_task_chain.reset()
	_inventory.clear()
	_farm_state = FarmState.EMPTY
	_grow_elapsed = 0.0
	_cook_elapsed = 0.0
	_is_cooking = false
	_grow_cooldown_left = 0.0
	_cook_cooldown_left = 0.0
	_TimerBar.hide_bar(_grow_bar)
	_TimerBar.hide_bar(_cook_bar)
	_orders.reset_patience()
	_update_hotspot_highlights()
	_update_order_label()


func _process(delta: float) -> void:
	if _game_over:
		return
	_orders.tick(delta)
	if _grow_cooldown_left > 0.0:
		_grow_cooldown_left = maxf(0.0, _grow_cooldown_left - delta)
	if _cook_cooldown_left > 0.0:
		_cook_cooldown_left = maxf(0.0, _cook_cooldown_left - delta)
	_tick_farm(delta)
	_tick_cook(delta)
	_TimerBar.set_elapsed(_patience_bar, _orders.patience_sec - _orders.patience_left)
	_emit_hud()


func _tick_farm(delta: float) -> void:
	if _farm_state != FarmState.GROWING:
		return
	_grow_elapsed += delta
	_TimerBar.set_elapsed(_grow_bar, _grow_elapsed)
	if _grow_elapsed >= _grow_time_sec:
		_farm_state = FarmState.READY
		$FarmSpot/HintLabel.text = "可收获！"


func _tick_cook(delta: float) -> void:
	if not _is_cooking:
		return
	_cook_elapsed += delta
	_TimerBar.set_elapsed(_cook_bar, _cook_elapsed)
	if _cook_elapsed >= _cook_time_sec:
		_finish_cooking()


func _on_farm_input(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if _game_over or _task_chain.current_step != _TaskChain.Step.GET:
		return
	if not _is_click(event):
		return
	match _farm_state:
		FarmState.EMPTY:
			_start_growing()
		FarmState.READY:
			_harvest_crop()
		FarmState.GROWING:
			pass


func _on_stove_input(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if _game_over or _task_chain.current_step != _TaskChain.Step.PROCESS:
		return
	if not _is_click(event):
		return
	if _is_cooking:
		return
	if not _inventory.has(_crop_id):
		$StoveSpot/HintLabel.text = "需要%s" % _crop_id
		return
	_start_cooking()


func _on_customer_input(_viewport: Node, event: InputEvent, _shape_idx: int) -> void:
	if _game_over or _task_chain.current_step != _TaskChain.Step.DELIVER:
		return
	if not _is_click(event):
		return
	if not _inventory.has(_dish_id):
		$CustomerSpot/HintLabel.text = "需要%s" % _dish_id
		return
	_deliver_order()


func _is_click(event: InputEvent) -> bool:
	if event is InputEventMouseButton:
		var mouse_event: InputEventMouseButton = event as InputEventMouseButton
		return mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT
	return false


func _start_growing() -> void:
	_farm_state = FarmState.GROWING
	_grow_elapsed = 0.0
	_TimerBar.setup(_grow_bar, _grow_time_sec)
	$FarmSpot/HintLabel.text = "生长中…"


func _harvest_crop() -> void:
	ThemeSoundUtil.play(self, "impact", "harvest")
	_inventory.add(_crop_id)
	_farm_state = FarmState.EMPTY
	_grow_elapsed = 0.0
	_TimerBar.hide_bar(_grow_bar)
	$FarmSpot/HintLabel.text = "点击种植"
	_task_chain.advance()
	_update_hotspot_highlights()
	_emit_hud()


func _start_cooking() -> void:
	if not _inventory.take(_crop_id):
		return
	_is_cooking = true
	_cook_elapsed = 0.0
	_TimerBar.setup(_cook_bar, _cook_time_sec)
	$StoveSpot/HintLabel.text = "烹饪中…"


func _finish_cooking() -> void:
	ThemeSoundUtil.play(self, "impact", "cook")
	_is_cooking = false
	_inventory.add(_dish_id)
	_TimerBar.hide_bar(_cook_bar)
	$StoveSpot/HintLabel.text = "点击烹饪"
	_task_chain.advance()
	_update_hotspot_highlights()
	_emit_hud()


func _deliver_order() -> void:
	if not _inventory.take(_dish_id):
		return
	ThemeSoundUtil.play(self, "impact", "serve")
	var payout: int = _orders.complete_order()
	order_completed.emit(payout, _orders.orders_completed)
	if _orders.is_won():
		_game_over = true
		game_won.emit(_orders.coins_earned)
		return
	_task_chain.reset()
	_farm_state = FarmState.EMPTY
	_grow_elapsed = 0.0
	_TimerBar.hide_bar(_grow_bar)
	$FarmSpot/HintLabel.text = "点击种植"
	_update_hotspot_highlights()
	_update_order_label()
	_emit_hud()


func trigger_instant_grow() -> bool:
	if not _InstantGrowSkill.is_enabled() or _grow_cooldown_left > 0.0:
		return false
	if _farm_state != FarmState.GROWING:
		return false
	_farm_state = FarmState.READY
	_grow_elapsed = _grow_time_sec
	_TimerBar.set_elapsed(_grow_bar, _grow_elapsed)
	$FarmSpot/HintLabel.text = "可收获！"
	_grow_cooldown_left = _InstantGrowSkill.get_cooldown_sec()
	_emit_hud()
	return true


func trigger_speed_cook() -> bool:
	if not _SpeedCookSkill.is_enabled() or _cook_cooldown_left > 0.0:
		return false
	if not _is_cooking:
		return false
	var remaining: float = _cook_time_sec - _cook_elapsed
	_cook_elapsed += remaining * _SpeedCookSkill.get_speed_multiplier()
	_TimerBar.set_elapsed(_cook_bar, _cook_elapsed)
	if _cook_elapsed >= _cook_time_sec:
		_finish_cooking()
	_cook_cooldown_left = _SpeedCookSkill.get_cooldown_sec()
	_emit_hud()
	return true


func _update_hotspot_highlights() -> void:
	var target: String = _task_chain.get_target_hotspot()
	_HotspotManager.set_highlight(_farm_area, target == "farm")
	_HotspotManager.set_highlight(_stove_area, target == "stove")
	_HotspotManager.set_highlight(_customer_area, target == "customer")


func _update_order_label() -> void:
	_order_label.text = _orders.get_order_label()
	_patience_bar.max_value = _orders.patience_sec
	_patience_bar.value = _orders.patience_left


func _emit_hud() -> void:
	hud_changed.emit({
		"step": _task_chain.get_step_label(),
		"inventory": _inventory.get_summary(),
		"coins": _orders.coins_earned,
		"orders_done": _orders.orders_completed,
		"orders_total": _orders.orders_to_win,
		"grow_skill_ready": _InstantGrowSkill.is_enabled() and _grow_cooldown_left <= 0.0,
		"cook_skill_ready": _SpeedCookSkill.is_enabled() and _cook_cooldown_left <= 0.0,
		"grow_skill_cd": _grow_cooldown_left,
		"cook_skill_cd": _cook_cooldown_left,
	})


func restart_after_win() -> void:
	_game_over = false
	_orders.orders_completed = 0
	_orders.coins_earned = 0
	_reset_round()
	_emit_hud()
