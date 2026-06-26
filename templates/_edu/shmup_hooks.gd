extends Node

## B7 shmup 操作钩子（workspace 专用，不改 templates/shmup/core 原件）
##
## generate/v2 集成（与 edu_action_bridge.gd 头注释一致）：
## 1. copy `templates/_edu/` 下桥与钩子到 `workspace/{session_id}/core/`
## 2. 注册 EduActionBridge Autoload
## 3. 在 `scenes/main.tscn` 添加子节点：
##    `[node name="EduHooks" type="Node" parent="."]` + `shmup_hooks.gd`
##
## 自动上报 action_id（与 config/code_anchors/shmup.json 对齐）：
## - kill_enemy：敌机 `destroyed` 信号（主）+ spawner.enemy_destroyed（备）
## - hit：玩家受伤
## - pickup：拾取道具（powerup.collected 信号）

const ACTION_KILL_ENEMY: String = "kill_enemy"
const ACTION_HIT: String = "hit"
const ACTION_PICKUP: String = "pickup"

const INVINCIBLE_SEC: float = 0.8
const GAME_RESCAN_SEC: float = 0.4

var _player: Area2D = null
var _prev_hp: int = -1
var _hit_invincible_timer: float = 0.0
var _wired_powerups: Dictionary = {}
var _wired_spawners: Dictionary = {}
var _wired_enemies: Dictionary = {}
var _wired_enemy_containers: Dictionary = {}
var _game_root: Node2D = null
var _powerups_root: Node2D = null
var _rescan_timer: SceneTreeTimer = null


func _ready() -> void:
	var main: Node = get_parent()
	if main == null:
		return
	_game_root = main.get_node_or_null("GameRoot") as Node2D
	if _game_root != null:
		_game_root.child_entered_tree.connect(_on_game_root_child_entered)
		for child: Node in _game_root.get_children():
			_bind_game_scene(child)
	call_deferred("_scan_scene")


func _on_game_root_child_entered(child: Node) -> void:
	_bind_game_scene(child)
	_schedule_game_rescan()


func _schedule_game_rescan() -> void:
	if _rescan_timer != null and _rescan_timer.time_left > 0.0:
		return
	_rescan_timer = get_tree().create_timer(GAME_RESCAN_SEC)
	_rescan_timer.timeout.connect(_rescan_active_game)


func _rescan_active_game() -> void:
	_rescan_timer = null
	if _game_root == null:
		return
	for child: Node in _game_root.get_children():
		_bind_game_scene(child)
	_scan_scene()


func _bind_game_scene(child: Node) -> void:
	var game: Node2D = child as Node2D
	if game == null:
		return
	var powerups: Node2D = game.get_node_or_null("Powerups") as Node2D
	if powerups != null and powerups != _powerups_root:
		if _powerups_root != null and _powerups_root.child_entered_tree.is_connected(_on_powerup_spawned):
			_powerups_root.child_entered_tree.disconnect(_on_powerup_spawned)
		_powerups_root = powerups
		if not _powerups_root.child_entered_tree.is_connected(_on_powerup_spawned):
			_powerups_root.child_entered_tree.connect(_on_powerup_spawned)
	_wire_enemy_spawner(game)


func _wire_enemy_spawner(game: Node2D) -> void:
	var spawner: Node = game.get_node_or_null("EnemySpawner")
	if spawner == null:
		return
	var id: int = spawner.get_instance_id()
	if not _wired_spawners.has(id):
		if spawner.has_signal("enemy_destroyed"):
			if not spawner.is_connected("enemy_destroyed", _on_enemy_destroyed):
				spawner.enemy_destroyed.connect(_on_enemy_destroyed)
		_wired_spawners[id] = true
	_wire_enemies_container(spawner)


func _wire_enemies_container(spawner: Node) -> void:
	var enemies: Node = spawner.get_node_or_null("Enemies")
	if enemies == null:
		return
	var container_id: int = enemies.get_instance_id()
	if not _wired_enemy_containers.has(container_id):
		if not enemies.child_entered_tree.is_connected(_on_enemy_spawned):
			enemies.child_entered_tree.connect(_on_enemy_spawned)
		_wired_enemy_containers[container_id] = true
	for child: Node in enemies.get_children():
		_wire_enemy_node(child)


func _on_enemy_spawned(child: Node) -> void:
	_wire_enemy_node(child)


func _wire_enemy_node(node: Node) -> void:
	if not node is Area2D:
		return
	var enemy: Area2D = node as Area2D
	var enemy_id: int = enemy.get_instance_id()
	if _wired_enemies.has(enemy_id):
		return
	if enemy.has_signal("destroyed"):
		if not enemy.is_connected("destroyed", _on_enemy_destroyed_direct):
			enemy.destroyed.connect(_on_enemy_destroyed_direct)
	_wired_enemies[enemy_id] = true


func _on_powerup_spawned(_child: Node) -> void:
	call_deferred("_wire_powerups")


func _scan_scene() -> void:
	_wire_player()
	_wire_powerups()


func _wire_player() -> void:
	var players: Array[Node] = get_tree().get_nodes_in_group("player")
	if players.is_empty():
		_player = null
		_prev_hp = -1
		return
	var candidate: Node = players[0]
	if candidate is Area2D:
		_player = candidate as Area2D
	else:
		_player = null
		_prev_hp = -1
		return
	if _player.has_signal("hp_changed") and not _player.is_connected("hp_changed", _on_player_hp_changed):
		_player.hp_changed.connect(_on_player_hp_changed)
	_prev_hp = _read_player_hp()


func _wire_powerups() -> void:
	for node: Node in _find_powerup_nodes():
		var id: int = node.get_instance_id()
		if _wired_powerups.has(id):
			continue
		if not node.has_signal("collected"):
			continue
		if not node.is_connected("collected", _on_powerup_collected):
			node.connect("collected", _on_powerup_collected)
		_wired_powerups[id] = true


func _find_powerup_nodes() -> Array[Node]:
	var found: Array[Node] = []
	if _powerups_root != null:
		for child: Node in _powerups_root.get_children():
			found.append(child)
		return found
	for node: Node in get_tree().get_nodes_in_group("powerup"):
		found.append(node)
	return found


func _physics_process(delta: float) -> void:
	_tick_hit_invincibility(delta)


func _tick_hit_invincibility(delta: float) -> void:
	if _hit_invincible_timer <= 0.0:
		return
	_hit_invincible_timer = maxf(0.0, _hit_invincible_timer - delta)


func _on_enemy_destroyed(_score_value: int, _enemy: Area2D) -> void:
	_emit_action(ACTION_KILL_ENEMY)


func _on_enemy_destroyed_direct(
	_enemy: Area2D,
	_score_value: int,
	_drop_rate: float,
	_is_boss: bool
) -> void:
	_emit_action(ACTION_KILL_ENEMY)


func _on_player_hp_changed(current_hp: int, _max_hp: int) -> void:
	if _prev_hp >= 0 and current_hp < _prev_hp:
		_emit_action(ACTION_HIT)
		_hit_invincible_timer = INVINCIBLE_SEC
	_prev_hp = current_hp


func _on_powerup_collected(_pickup: Area2D, _powerup_name: String) -> void:
	_emit_action(ACTION_PICKUP)


func _read_player_hp() -> int:
	if _player == null or not is_instance_valid(_player):
		return -1
	if _player.get("_hp") != null:
		return int(_player.get("_hp"))
	return -1


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
