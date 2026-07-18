extends Node

## 展厅 · AI 沙箱桥（加固版）
## 1) 合并 overrides · 加载沙箱脚本/图标
## 2) 原生执行 sandbox_rules（不依赖 LLM 脚本也能生效）
## 3) 二段跳下落补丁 · 金币监听（Collectibles + 周期重扫 + HUD 兜底）

const SANDBOX_DIR: String = "res://core/ai_sandbox"
const OVERRIDES_PATH: String = "res://core/ai_sandbox/overrides.json"
const ICONS_DIR: String = "res://core/ai_sandbox/icons"

signal coin_collected(total: int)

var _coin_total: int = 0
var _coin_watchers: Array[Callable] = []
var _wired_collectibles: Dictionary = {}
var _speed_boost_left: float = 0.0
var _speed_boost_mult: float = 1.0
var _base_move_speed: float = -1.0
var _invincible_left: float = 0.0
var _fx_left: float = 0.0
var _air_jump_assist_used: bool = false
var _countdown_label: Label = null
var _countdown_left: float = 0.0
var _player_cache: CharacterBody2D = null
var _player_node_cache: Node = null
var _status_label: Label = null
var _rescan_accum: float = 0.0
var _hud_coin_last: int = -1
var _bullet_tint_palette: Array[Color] = []
var _bullet_tint_idx: int = 0
var _bullet_tint_accum: float = 0.0
var _temp_shield_left: float = 0.0
var _skill_bomb_cd: float = 0.0
var _skill_laser_cd: float = 0.0
var _skill_laser_active: float = 0.0
var _skill_input_ready: bool = false
var _laser_beam_node: Polygon2D = null
## 通用触屏：action_id → 中文标签（ensure_touch_action 注册）
var _touch_action_labels: Dictionary = {}
var _touch_hud_layer: CanvasLayer = null
var _touch_hud_row: HBoxContainer = null
var _touch_hud_buttons: Dictionary = {}
## 点技能 HUD 时阻止飞机鼠标跟机（player_ship 询 is_mouse_steer_blocked）
var _mouse_steer_blocked: bool = false

# 原生规则（来自 config.sandbox_rules / tuning.sandbox_rules）
var _rule_coin_every: int = 0
var _rule_coin_duration: float = 3.0
var _rule_coin_speed: float = 1.35


func _ready() -> void:
	add_to_group("ai_sandbox_bridge")
	_merge_overrides_json()
	_read_sandbox_rules()
	_build_skill_icon_hud()
	_build_status_label()
	_load_modifier_scripts()
	_ensure_skill_input_map()
	call_deferred("_bootstrap_watchers")
	_refresh_status_label()


func is_mouse_steer_blocked() -> bool:
	## 技能按钮按下中，或指针悬停在技能 HUD / BaseButton 上
	if _mouse_steer_blocked:
		return true
	var vp: Viewport = get_viewport()
	if vp == null:
		return false
	var hovered: Control = vp.gui_get_hovered_control()
	if hovered == null:
		return false
	var node: Node = hovered
	while node != null:
		if node is BaseButton:
			return true
		var nm: String = str(node.name)
		if nm.begins_with("Zone_") or nm == "AiTouchActionHud" or nm == "TouchPad":
			return true
		node = node.get_parent()
	return false


func set_mouse_steer_blocked(blocked: bool) -> void:
	_mouse_steer_blocked = blocked


func _bootstrap_watchers() -> void:
	var tree: SceneTree = get_tree()
	if tree == null:
		return
	if not tree.node_added.is_connected(_on_tree_node_added):
		tree.node_added.connect(_on_tree_node_added)
	_rescan_collectibles()


func _process(delta: float) -> void:
	_tick_speed_boost(delta)
	_tick_invincibility(delta)
	_tick_fx(delta)
	_tick_countdown(delta)
	_tick_temp_shield(delta)
	_tick_bullet_tint(delta)
	_tick_catalog_skills(delta)
	_rescan_accum += delta
	if _rescan_accum >= 0.45:
		_rescan_accum = 0.0
		_rescan_collectibles()
		_poll_hud_coins()
	_refresh_status_label()


func _physics_process(_delta: float) -> void:
	_tick_air_jump_assist()


func _read_sandbox_rules() -> void:
	var rules: Dictionary = _get_rules_dict()
	_rule_coin_every = int(rules.get("coin_every", rules.get("coin_buff_every", 0)))
	_rule_coin_duration = float(rules.get("coin_duration", rules.get("coin_buff_sec", 3.0)))
	_rule_coin_speed = float(rules.get("coin_speed_mult", rules.get("coin_buff_speed", 1.35)))


func _get_rules_dict() -> Dictionary:
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config == null:
		return {}
	var cfg: Variant = game_config.get("config")
	if not cfg is Dictionary:
		return {}
	var root: Dictionary = cfg as Dictionary
	if root.has("sandbox_rules") and root["sandbox_rules"] is Dictionary:
		return root["sandbox_rules"] as Dictionary
	var tuning: Variant = root.get("tuning", {})
	if tuning is Dictionary and (tuning as Dictionary).has("sandbox_rules"):
		var nested: Variant = (tuning as Dictionary)["sandbox_rules"]
		if nested is Dictionary:
			return nested as Dictionary
	return {}


# ── 公开 API ─────────────────────────────────────────────────────────────────


func get_player() -> CharacterBody2D:
	if _player_cache != null and is_instance_valid(_player_cache) and not _player_cache.is_queued_for_deletion():
		return _player_cache
	_player_cache = null
	var tree: SceneTree = get_tree()
	if tree == null:
		return null
	for node: Node in tree.get_nodes_in_group("player"):
		if node is CharacterBody2D and is_instance_valid(node):
			_player_cache = node as CharacterBody2D
			return _player_cache
	var current: Node = tree.current_scene
	if current != null:
		var found: Node = current.find_child("Player", true, false)
		if found is CharacterBody2D:
			_player_cache = found as CharacterBody2D
			return _player_cache
	return null


func get_player_node() -> Node:
	## 平台 CharacterBody2D 或 shmup Area2D 等任意 group=player 节点
	if _player_node_cache != null and is_instance_valid(_player_node_cache) and not _player_node_cache.is_queued_for_deletion():
		return _player_node_cache
	_player_node_cache = null
	var body: CharacterBody2D = get_player()
	if body != null:
		_player_node_cache = body
		return _player_node_cache
	var tree: SceneTree = get_tree()
	if tree == null:
		return null
	for node: Node in tree.get_nodes_in_group("player"):
		if is_instance_valid(node):
			_player_node_cache = node
			return _player_node_cache
	var current: Node = tree.current_scene
	if current != null:
		var found: Node = current.find_child("Player", true, false)
		if found != null:
			_player_node_cache = found
			return _player_node_cache
	return null


func get_game_manager() -> Node:
	var tree: SceneTree = get_tree()
	if tree == null:
		return null
	return tree.current_scene


func get_coin_count() -> int:
	return _coin_total


func watch_coins(cb: Callable) -> void:
	if cb.is_valid():
		_coin_watchers.append(cb)
	_rescan_collectibles()


func grant_invincibility(seconds: float) -> void:
	var sec: float = maxf(0.2, seconds)
	_invincible_left = maxf(_invincible_left, sec)
	var player: CharacterBody2D = get_player()
	if player == null:
		return
	player.set("_invincible_sec", sec)
	if player.has_method("_start_invincibility"):
		player.call("_start_invincibility")
	else:
		player.set("_is_invincible", true)


func boost_move_speed(multiplier: float, seconds: float) -> void:
	var player: CharacterBody2D = get_player()
	if player == null:
		return
	if _base_move_speed < 0.0:
		_base_move_speed = float(player.get("_move_speed"))
	_speed_boost_mult = maxf(1.05, multiplier)
	_speed_boost_left = maxf(0.2, seconds)
	player.set("_move_speed", _base_move_speed * _speed_boost_mult)


func show_countdown(seconds: float, title: String = "倒计时") -> void:
	_countdown_left = maxf(0.2, seconds)
	_ensure_countdown_label()
	if _countdown_label != null:
		_countdown_label.visible = true
		_countdown_label.text = "%s %.1f" % [title, _countdown_left]


func flash_player_fx(seconds: float) -> void:
	_fx_left = maxf(0.2, seconds)


func set_tuning_number(dotted_path: String, value: float) -> void:
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config == null:
		return
	var cfg: Variant = game_config.get("config")
	if not cfg is Dictionary:
		return
	var root: Dictionary = (cfg as Dictionary).duplicate(true)
	_set_dotted(root, dotted_path, value)
	game_config.set("config", root)


func tint_player_bullets(colors: Array) -> void:
	## shmup：玩家子弹循环着色。colors 可含 Color 或 "#RRGGBB" 字符串。
	_bullet_tint_palette.clear()
	_bullet_tint_idx = 0
	for item in colors:
		var c: Color = _to_color(item)
		_bullet_tint_palette.append(c)
	if _bullet_tint_palette.is_empty():
		rainbow_player_bullets()


func rainbow_player_bullets() -> void:
	tint_player_bullets([
		Color(1.0, 0.25, 0.35, 1.0),
		Color(1.0, 0.65, 0.2, 1.0),
		Color(1.0, 0.95, 0.25, 1.0),
		Color(0.3, 0.95, 0.45, 1.0),
		Color(0.25, 0.65, 1.0, 1.0),
		Color(0.75, 0.35, 1.0, 1.0),
	])


func grant_temp_shield(seconds: float) -> void:
	## shmup / 通用：临时护盾（点亮机体 ShieldSprite 或 _has_shield）
	var sec: float = maxf(0.4, seconds)
	_temp_shield_left = maxf(_temp_shield_left, sec)
	var player: Node = get_player_node()
	if player == null:
		return
	player.set("_has_shield", true)
	var shield_sprite: Node = player.get_node_or_null("ShieldSprite")
	if shield_sprite is CanvasItem:
		(shield_sprite as CanvasItem).visible = true
	flash_player_fx(minf(1.2, sec))
	show_countdown(sec, "护盾")


func activate_bomb() -> bool:
	## 清屏炸弹：清敌弹 + 伤敌；需 enabled_skills 含 bomb
	if not _has_catalog_skill("bomb"):
		return false
	if _skill_bomb_cd > 0.0:
		return false
	_skill_bomb_cd = 12.0
	var pool: Node = get_tree().get_first_node_in_group("bullet_pool") if get_tree() else null
	if pool != null and pool.has_method("clear_enemy_bullets"):
		pool.call("clear_enemy_bullets")
	var tree: SceneTree = get_tree()
	if tree != null:
		for enemy: Node in tree.get_nodes_in_group("enemy"):
			if enemy.has_method("take_damage"):
				enemy.call("take_damage", 40)
	show_countdown(1.2, "清屏炸弹")
	flash_player_fx(0.6)
	return true


func activate_laser_beam() -> bool:
	## 穿透激光：短暂持续伤敌；需 enabled_skills 含 laser_beam
	if not _has_catalog_skill("laser_beam"):
		return false
	if _skill_laser_cd > 0.0 or _skill_laser_active > 0.0:
		return false
	_skill_laser_cd = 6.0
	_skill_laser_active = 3.0
	show_countdown(3.0, "激光")
	flash_player_fx(0.4)
	return true


func ensure_touch_skill_buttons() -> void:
	## 硬性：展厅触屏 — 技能须有屏上按钮（勿每帧重建，否则点按永远点不中）
	_ensure_skill_input_map()
	var want: Dictionary = {}
	if _has_catalog_skill("bomb"):
		want["bomb"] = "炸弹"
	if _has_catalog_skill("laser_beam"):
		want["laser_beam"] = "激光"
	var same: bool = want.size() == _touch_action_labels.size()
	if same:
		for k in want.keys():
			if not _touch_action_labels.has(k) or str(_touch_action_labels[k]) != str(want[k]):
				same = false
				break
	if same and _touch_hud_buttons.size() == want.size():
		return
	_touch_action_labels = want
	for aid_v in want.keys():
		var aid: String = str(aid_v)
		var keycode: Key = KEY_F
		if aid == "bomb":
			keycode = KEY_Q
		elif aid == "laser_beam":
			keycode = KEY_E
		_ensure_action_key(aid, keycode)
	_ensure_touch_hud()
	_rebuild_touch_hud_buttons()


func ensure_touch_action(action_id: String, label: String) -> void:
	## 品类无关：注册 InputMap + 屏上可点按钮（收敛各 overlay 特例）
	var aid: String = action_id.strip_edges()
	if aid.is_empty():
		return
	var title: String = label.strip_edges()
	if title.is_empty():
		title = aid
	var already: bool = (
		_touch_action_labels.has(aid)
		and str(_touch_action_labels[aid]) == title
		and _touch_hud_buttons.has(aid)
		and is_instance_valid(_touch_hud_buttons[aid] as Node)
	)
	_touch_action_labels[aid] = title
	var keycode: Key = KEY_NONE
	if aid == "bomb":
		keycode = KEY_Q
	elif aid == "laser_beam":
		keycode = KEY_E
	elif aid == "jump":
		keycode = KEY_SPACE
	else:
		keycode = KEY_F
	_ensure_action_key(aid, keycode)
	_ensure_touch_hud()
	if already:
		return
	_rebuild_touch_hud_buttons()


func _ensure_touch_hud() -> void:
	if _touch_hud_layer != null and is_instance_valid(_touch_hud_layer):
		# 必须高于品类 Touch overlay（同 Canvas 内 z=100），否则点不到技能键
		_touch_hud_layer.layer = 110
		return
	_touch_hud_layer = CanvasLayer.new()
	_touch_hud_layer.name = "AiTouchActionHud"
	_touch_hud_layer.layer = 110
	add_child(_touch_hud_layer)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_touch_hud_layer.add_child(root)
	_touch_hud_row = HBoxContainer.new()
	_touch_hud_row.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	_touch_hud_row.offset_top = -132.0
	_touch_hud_row.offset_bottom = -24.0
	_touch_hud_row.offset_left = 24.0
	_touch_hud_row.offset_right = -24.0
	_touch_hud_row.alignment = BoxContainer.ALIGNMENT_CENTER
	_touch_hud_row.add_theme_constant_override("separation", 18)
	_touch_hud_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_touch_hud_row)


func _rebuild_touch_hud_buttons() -> void:
	if _touch_hud_row == null or not is_instance_valid(_touch_hud_row):
		return
	for child in _touch_hud_row.get_children():
		child.queue_free()
	_touch_hud_buttons.clear()
	for aid_v in _touch_action_labels.keys():
		var aid: String = str(aid_v)
		var title: String = str(_touch_action_labels[aid])
		var btn := Button.new()
		btn.text = title
		btn.custom_minimum_size = Vector2(132, 88)
		btn.focus_mode = Control.FOCUS_NONE
		btn.mouse_filter = Control.MOUSE_FILTER_STOP
		btn.button_down.connect(_on_touch_action_down.bind(aid))
		btn.button_up.connect(_on_touch_action_up.bind(aid))
		btn.pressed.connect(_on_touch_action_pressed.bind(aid))
		_touch_hud_row.add_child(btn)
		_touch_hud_buttons[aid] = btn


func _on_touch_action_down(_action_id: String) -> void:
	set_mouse_steer_blocked(true)


func _on_touch_action_up(_action_id: String) -> void:
	set_mouse_steer_blocked(false)


func _on_touch_action_pressed(action_id: String) -> void:
	## 点按 → 直接触发技能（勿依赖全局鼠标，避免跟机抢输入）
	set_mouse_steer_blocked(true)
	if action_id == "bomb":
		activate_bomb()
		set_mouse_steer_blocked(false)
		return
	if action_id == "laser_beam":
		activate_laser_beam()
		set_mouse_steer_blocked(false)
		return
	if not InputMap.has_action(action_id):
		set_mouse_steer_blocked(false)
		return
	Input.action_press(action_id)
	await get_tree().process_frame
	Input.action_release(action_id)
	set_mouse_steer_blocked(false)


func _has_catalog_skill(skill_id: String) -> bool:
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config != null and game_config.has_method("has_skill"):
		return bool(game_config.call("has_skill", skill_id))
	return skill_id in _enabled_skill_ids()


func _ensure_skill_input_map() -> void:
	if _skill_input_ready:
		return
	_skill_input_ready = true
	_ensure_action_key("bomb", KEY_Q)
	_ensure_action_key("laser_beam", KEY_E)


func _ensure_action_key(action: String, keycode: Key) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventKey.new()
	ev.physical_keycode = keycode
	for existing in InputMap.action_get_events(action):
		if existing is InputEventKey and (existing as InputEventKey).physical_keycode == keycode:
			return
	InputMap.action_add_event(action, ev)


func _tick_catalog_skills(delta: float) -> void:
	_ensure_skill_input_map()
	if _has_catalog_skill("bomb") or _has_catalog_skill("laser_beam"):
		ensure_touch_skill_buttons()
	if _skill_bomb_cd > 0.0:
		_skill_bomb_cd = maxf(0.0, _skill_bomb_cd - delta)
	if _skill_laser_cd > 0.0:
		_skill_laser_cd = maxf(0.0, _skill_laser_cd - delta)
	if _skill_laser_active > 0.0:
		_skill_laser_active = maxf(0.0, _skill_laser_active - delta)
		_apply_laser_tick()
	else:
		_hide_laser_beam()
	if Input.is_action_just_pressed("bomb"):
		activate_bomb()
	if Input.is_action_just_pressed("laser_beam"):
		activate_laser_beam()


func _apply_laser_tick() -> void:
	var player: Node = get_player_node()
	if player == null:
		return
	_ensure_laser_beam_visual(player)
	var tree: SceneTree = get_tree()
	if tree == null:
		return
	var ppos: Variant = player.get("global_position")
	if ppos == null:
		return
	var px: float = float((ppos as Vector2).x)
	for enemy: Node in tree.get_nodes_in_group("enemy"):
		if not is_instance_valid(enemy):
			continue
		var ep: Variant = enemy.get("global_position")
		if ep == null:
			continue
		var ex: float = float((ep as Vector2).x)
		if absf(ex - px) <= 36.0 and enemy.has_method("take_damage"):
			enemy.call("take_damage", 2)


func _ensure_laser_beam_visual(player: Node) -> void:
	if _laser_beam_node != null and is_instance_valid(_laser_beam_node):
		_laser_beam_node.visible = true
		return
	var beam := Polygon2D.new()
	beam.name = "AiSandboxLaserBeam"
	beam.polygon = PackedVector2Array([
		Vector2(-7.0, -260.0),
		Vector2(7.0, -260.0),
		Vector2(7.0, -8.0),
		Vector2(-7.0, -8.0),
	])
	beam.color = Color(0.35, 0.95, 1.0, 0.7)
	player.add_child(beam)
	_laser_beam_node = beam


func _hide_laser_beam() -> void:
	if _laser_beam_node != null and is_instance_valid(_laser_beam_node):
		_laser_beam_node.queue_free()
		_laser_beam_node = null


func _to_color(value: Variant) -> Color:
	if value is Color:
		return value as Color
	if value is String:
		var s: String = str(value).strip_edges()
		if s.begins_with("#"):
			return Color.html(s)
		return Color.html("#" + s) if s.length() >= 6 else Color.WHITE
	if value is Array and (value as Array).size() >= 3:
		var arr: Array = value as Array
		var a: float = float(arr[3]) if arr.size() > 3 else 1.0
		return Color(float(arr[0]), float(arr[1]), float(arr[2]), a)
	return Color.WHITE


func _tick_bullet_tint(delta: float) -> void:
	if _bullet_tint_palette.is_empty():
		return
	_bullet_tint_accum += delta
	if _bullet_tint_accum < 0.08:
		return
	_bullet_tint_accum = 0.0
	var tree: SceneTree = get_tree()
	if tree == null or tree.current_scene == null:
		return
	var pool: Node = tree.get_first_node_in_group("bullet_pool")
	var roots: Array[Node] = []
	if pool != null:
		roots.append(pool)
	else:
		roots.append(tree.current_scene)
	for root_node: Node in roots:
		_tint_bullets_under(root_node)


func _tint_bullets_under(node: Node) -> void:
	if node.get("is_player_bullet") == true and node is CanvasItem and bool(node.get("visible")):
		var color: Color = _bullet_tint_palette[_bullet_tint_idx % _bullet_tint_palette.size()]
		_bullet_tint_idx = (_bullet_tint_idx + 1) % maxi(1, _bullet_tint_palette.size())
		var sprite: Node = node.get_node_or_null("Sprite2D")
		if sprite is CanvasItem:
			(sprite as CanvasItem).modulate = color
		else:
			(node as CanvasItem).modulate = color
	for child: Node in node.get_children():
		_tint_bullets_under(child)


func _tick_temp_shield(delta: float) -> void:
	if _temp_shield_left <= 0.0:
		return
	_temp_shield_left = maxf(0.0, _temp_shield_left - delta)
	var player: Node = get_player_node()
	if player == null:
		return
	if _temp_shield_left > 0.0:
		player.set("_has_shield", true)
		var shield_on: Node = player.get_node_or_null("ShieldSprite")
		if shield_on is CanvasItem:
			(shield_on as CanvasItem).visible = true
		return
	# 到期：仅清桥发放的临时盾；不强制关道具盾逻辑冲突时保持可见由机体自己管
	if bool(player.get("_has_shield")):
		player.set("_has_shield", false)
		var shield_off: Node = player.get_node_or_null("ShieldSprite")
		if shield_off is CanvasItem:
			(shield_off as CanvasItem).visible = false


# ── 二段跳 ───────────────────────────────────────────────────────────────────


func _want_double_jump() -> bool:
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config != null and game_config.has_method("has_skill"):
		if bool(game_config.call("has_skill", "double_jump")):
			return true
	# 图标已生成也视为启用（防止 config 未刷新）
	if FileAccess.file_exists("%s/double_jump.svg" % ICONS_DIR):
		return true
	return false


func _tick_air_jump_assist() -> void:
	if not _want_double_jump():
		return
	var player: CharacterBody2D = get_player()
	if player == null:
		return
	if player.is_on_floor():
		_air_jump_assist_used = false
		return
	if not Input.is_action_just_pressed("jump"):
		return
	# 原版上升段自己处理；这里专补下落段
	if player.velocity.y <= 0.0:
		return
	if _air_jump_assist_used:
		return
	if bool(player.get("_double_jump_used")):
		# 上升段已用掉二段跳则不再补
		_air_jump_assist_used = true
		return
	var jump_v: float = float(player.get("_jump_velocity"))
	if jump_v >= 0.0:
		jump_v = -400.0
	player.velocity.y = jump_v
	_air_jump_assist_used = true
	player.set("_double_jump_used", true)


# ── 金币 ─────────────────────────────────────────────────────────────────────


func _on_tree_node_added(node: Node) -> void:
	if node.has_signal("collected"):
		_wire_one_collectible(node)


func _rescan_collectibles() -> void:
	var tree: SceneTree = get_tree()
	if tree == null:
		return
	for node: Node in tree.get_nodes_in_group("collectible"):
		_wire_one_collectible(node)
	var current: Node = tree.current_scene
	if current == null:
		return
	# 全树扫描带 collected 信号的 Area2D（不依赖 group）
	_scan_collected_signal(current)
	var level_root: Node = current.get_node_or_null("LevelRoot")
	if level_root != null:
		for level: Node in level_root.get_children():
			var bag: Node = level.get_node_or_null("Collectibles")
			if bag == null:
				continue
			for child: Node in bag.get_children():
				_wire_one_collectible(child)


func _scan_collected_signal(node: Node) -> void:
	if node.has_signal("collected"):
		_wire_one_collectible(node)
	for child: Node in node.get_children():
		_scan_collected_signal(child)


func _wire_one_collectible(node: Node) -> void:
	if not is_instance_valid(node) or not node.has_signal("collected"):
		return
	var id: int = node.get_instance_id()
	if _wired_collectibles.has(id):
		return
	if not node.is_in_group("collectible"):
		node.add_to_group("collectible")
	var cb := Callable(self, "_on_collectible_collected")
	if not node.is_connected("collected", cb):
		node.connect("collected", cb)
	_wired_collectibles[id] = true


func _on_collectible_collected() -> void:
	_register_coin(_coin_total + 1)


func _poll_hud_coins() -> void:
	## 兜底：从 HUD 樱桃数同步（防止漏接信号）
	var tree: SceneTree = get_tree()
	if tree == null or tree.current_scene == null:
		return
	var label: Node = tree.current_scene.find_child("CoinsLabel", true, false)
	if not (label is Label):
		return
	var text: String = (label as Label).text
	var digits: String = ""
	for i in range(text.length()):
		var ch: String = text.substr(i, 1)
		if ch >= "0" and ch <= "9":
			digits += ch
	if digits.is_empty():
		return
	var n: int = int(digits)
	if n > _coin_total:
		_register_coin(n)
	_hud_coin_last = n


func _register_coin(total: int) -> void:
	if total <= _coin_total:
		return
	_coin_total = total
	coin_collected.emit(_coin_total)
	for cb in _coin_watchers:
		if cb.is_valid():
			cb.call(_coin_total)
	_apply_native_coin_rules()


func _apply_native_coin_rules() -> void:
	if _rule_coin_every <= 0:
		return
	if _coin_total <= 0 or (_coin_total % _rule_coin_every) != 0:
		return
	grant_invincibility(_rule_coin_duration)
	boost_move_speed(_rule_coin_speed, _rule_coin_duration)
	flash_player_fx(_rule_coin_duration)
	show_countdown(_rule_coin_duration, "无敌加速")


# ── buff tick ────────────────────────────────────────────────────────────────


func _tick_speed_boost(delta: float) -> void:
	if _speed_boost_left <= 0.0:
		return
	_speed_boost_left = maxf(0.0, _speed_boost_left - delta)
	var player: CharacterBody2D = get_player()
	if player != null and _base_move_speed >= 0.0 and _speed_boost_left > 0.0:
		player.set("_move_speed", _base_move_speed * _speed_boost_mult)
	if _speed_boost_left > 0.0:
		return
	if player != null and _base_move_speed >= 0.0:
		player.set("_move_speed", _base_move_speed)
	_speed_boost_mult = 1.0


func _tick_invincibility(delta: float) -> void:
	if _invincible_left <= 0.0:
		return
	_invincible_left = maxf(0.0, _invincible_left - delta)
	var player: CharacterBody2D = get_player()
	if player == null:
		return
	if _invincible_left > 0.0:
		player.set("_is_invincible", true)
	elif player.has_method("_on_invincibility_done"):
		player.call("_on_invincibility_done")
	else:
		player.set("_is_invincible", false)


func _tick_fx(delta: float) -> void:
	if _fx_left <= 0.0:
		return
	_fx_left = maxf(0.0, _fx_left - delta)
	var player: Node = get_player_node()
	if player == null:
		return
	var sprite: Node = player.get_node_or_null("AnimatedSprite2D")
	if sprite == null:
		sprite = player.get_node_or_null("Sprite2D")
	if not (sprite is CanvasItem):
		return
	var item: CanvasItem = sprite as CanvasItem
	if _fx_left <= 0.0:
		item.modulate = Color(1, 1, 1, 1)
		return
	var pulse: float = 0.7 + 0.3 * sin(Time.get_ticks_msec() * 0.025)
	item.modulate = Color(1.25, 1.15 * pulse, 0.35, 1.0)


func _ensure_countdown_label() -> void:
	if _countdown_label != null and is_instance_valid(_countdown_label):
		return
	var layer: CanvasLayer = CanvasLayer.new()
	layer.name = "AiSandboxCountdownLayer"
	layer.layer = 70
	var label: Label = Label.new()
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 28)
	label.add_theme_color_override("font_color", Color(1, 0.95, 0.4))
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.75))
	label.add_theme_constant_override("outline_size", 4)
	label.set_anchors_preset(Control.PRESET_CENTER_TOP)
	label.offset_top = 20.0
	label.offset_bottom = 64.0
	label.offset_left = -180.0
	label.offset_right = 180.0
	layer.add_child(label)
	add_child(layer)
	_countdown_label = label


func _tick_countdown(delta: float) -> void:
	if _countdown_left <= 0.0:
		if _countdown_label != null:
			_countdown_label.visible = false
		return
	_countdown_left = maxf(0.0, _countdown_left - delta)
	if _countdown_label != null:
		_countdown_label.text = "无敌加速 %.1f" % _countdown_left
		_countdown_label.visible = _countdown_left > 0.0


func _build_status_label() -> void:
	var layer: CanvasLayer = CanvasLayer.new()
	layer.name = "AiSandboxStatusLayer"
	layer.layer = 65
	var label: Label = Label.new()
	label.name = "SandboxStatus"
	label.add_theme_font_size_override("font_size", 13)
	label.add_theme_color_override("font_color", Color(0.1, 0.35, 0.65))
	label.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	label.offset_left = 12.0
	label.offset_top = -36.0
	label.offset_right = 420.0
	label.offset_bottom = -8.0
	layer.add_child(label)
	add_child(layer)
	_status_label = label


func _refresh_status_label() -> void:
	if _status_label == null:
		return
	var skills: Array[String] = _enabled_skill_ids()
	var skill_txt: String = ",".join(skills) if not skills.is_empty() else "-"
	var rule_txt: String = "金币/%d" % _rule_coin_every if _rule_coin_every > 0 else "无规则"
	_status_label.text = "沙箱ON · 技能[%s] · %s · 币%d" % [skill_txt, rule_txt, _coin_total]


func _set_dotted(root: Dictionary, dotted: String, value: Variant) -> void:
	var parts: PackedStringArray = dotted.split(".")
	if parts.is_empty():
		return
	var cur: Dictionary = root
	for i in range(parts.size() - 1):
		var key: String = str(parts[i])
		if not cur.has(key) or not cur[key] is Dictionary:
			cur[key] = {}
		cur = cur[key] as Dictionary
	cur[str(parts[parts.size() - 1])] = value


# ── overrides / 脚本 / 图标 ───────────────────────────────────────────────────


func _merge_overrides_json() -> void:
	if not FileAccess.file_exists(OVERRIDES_PATH):
		return
	var file: FileAccess = FileAccess.open(OVERRIDES_PATH, FileAccess.READ)
	if file == null:
		return
	var raw: String = file.get_as_text()
	file.close()
	var json: JSON = JSON.new()
	if json.parse(raw) != OK:
		push_warning("AiSandboxBridge: overrides.json parse failed")
		return
	if not json.data is Dictionary:
		return
	var patch: Dictionary = json.data as Dictionary
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config == null:
		return
	var base: Variant = game_config.get("config")
	if not base is Dictionary:
		return
	game_config.set("config", _deep_merge(base as Dictionary, patch))


func _build_skill_icon_hud() -> void:
	var skills: Array[String] = _enabled_skill_ids()
	if skills.is_empty() and FileAccess.file_exists("%s/double_jump.svg" % ICONS_DIR):
		skills = ["double_jump"]
	if skills.is_empty():
		return
	var layer: CanvasLayer = CanvasLayer.new()
	layer.name = "AiSandboxSkillHud"
	layer.layer = 60
	var panel: PanelContainer = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_TOP_LEFT)
	panel.offset_left = 16.0
	panel.offset_top = 16.0
	panel.offset_right = 16.0 + float(skills.size()) * 76.0 + 20.0
	panel.offset_bottom = 108.0
	var style: StyleBoxFlat = StyleBoxFlat.new()
	style.bg_color = Color(1, 1, 1, 0.85)
	style.set_border_width_all(2)
	style.border_color = Color(0.45, 0.75, 0.98, 0.95)
	style.corner_radius_top_left = 14
	style.corner_radius_top_right = 14
	style.corner_radius_bottom_left = 14
	style.corner_radius_bottom_right = 14
	panel.add_theme_stylebox_override("panel", style)
	var row: HBoxContainer = HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	panel.add_child(row)
	for skill_id in skills:
		var cell: VBoxContainer = VBoxContainer.new()
		cell.custom_minimum_size = Vector2(64, 80)
		cell.alignment = BoxContainer.ALIGNMENT_CENTER
		var icon: TextureRect = TextureRect.new()
		icon.custom_minimum_size = Vector2(48, 48)
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		var tex: Texture2D = _load_skill_icon(str(skill_id))
		if tex != null:
			icon.texture = tex
		var label: Label = Label.new()
		label.text = _skill_label(str(skill_id))
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 12)
		cell.add_child(icon)
		cell.add_child(label)
		row.add_child(cell)
	layer.add_child(panel)
	add_child(layer)


func _enabled_skill_ids() -> Array[String]:
	var out: Array[String] = []
	var game_config: Node = get_node_or_null("/root/GameConfig")
	if game_config == null:
		return out
	var cfg: Variant = game_config.get("config")
	if not cfg is Dictionary:
		return out
	var tuning: Variant = (cfg as Dictionary).get("tuning", {})
	if not tuning is Dictionary:
		return out
	var raw: Variant = (tuning as Dictionary).get("enabled_skills", [])
	if not raw is Array:
		return out
	for item in raw as Array:
		var sid: String = str(item).strip_edges()
		if sid != "" and sid not in out:
			out.append(sid)
	return out


func _skill_label(skill_id: String) -> String:
	match skill_id:
		"double_jump":
			return "二段跳"
		"ground_pound":
			return "下砸"
		"bomb":
			return "炸弹"
		"laser_beam":
			return "激光"
		"magnet":
			return "吸经验"
		"nova":
			return "爆发"
		_:
			return skill_id


func _load_skill_icon(skill_id: String) -> Texture2D:
	var path: String = "%s/%s.svg" % [ICONS_DIR, skill_id]
	if FileAccess.file_exists(path):
		var file: FileAccess = FileAccess.open(path, FileAccess.READ)
		if file != null:
			var svg: String = file.get_as_text()
			file.close()
			var image: Image = Image.new()
			if image.load_svg_from_string(svg, 3.0) == OK:
				return ImageTexture.create_from_image(image)
	var image2: Image = Image.create(48, 48, false, Image.FORMAT_RGBA8)
	image2.fill(Color(0.2, 0.7, 1.0, 1.0))
	return ImageTexture.create_from_image(image2)


func _load_modifier_scripts() -> void:
	_load_gd_dir(SANDBOX_DIR)


func _load_gd_dir(dir_path: String) -> void:
	var dir: DirAccess = DirAccess.open(dir_path)
	if dir == null:
		return
	dir.list_dir_begin()
	var entry: String = dir.get_next()
	while entry != "":
		if dir.current_is_dir():
			if entry != "." and entry != ".." and not entry.begins_with("."):
				_load_gd_dir("%s/%s" % [dir_path, entry])
		elif entry.ends_with(".gd") and not entry.begins_with("_"):
			_try_apply_script("%s/%s" % [dir_path, entry])
		entry = dir.get_next()
	dir.list_dir_end()


func _try_apply_script(path: String) -> void:
	var script_res: Resource = load(path)
	if script_res == null or not (script_res is GDScript):
		push_warning("AiSandboxBridge: skip invalid script %s" % path)
		return
	var script: GDScript = script_res as GDScript
	var instance: Object = script.new()
	if instance == null:
		return
	if instance.has_method("apply"):
		instance.call("apply", self)
	if instance is Node:
		var node: Node = instance as Node
		node.name = "AiMod_%s" % path.get_file().get_basename()
		add_child(node)


func _deep_merge(base: Dictionary, patch: Dictionary) -> Dictionary:
	var out: Dictionary = base.duplicate(true)
	for key in patch.keys():
		var pk: Variant = patch[key]
		if pk is Dictionary and out.has(key) and out[key] is Dictionary:
			out[key] = _deep_merge(out[key] as Dictionary, pk as Dictionary)
		else:
			out[key] = pk
	return out
