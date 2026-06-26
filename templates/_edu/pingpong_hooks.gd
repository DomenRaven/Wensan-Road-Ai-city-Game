extends Node

## B7 pingpong 操作钩子（workspace 专用，不改 templates/pingpong/core 原件）
##
## generate/v2 集成（与 edu_action_bridge.gd 头注释一致）：
## 1. copy `templates/_edu/` 下桥与钩子到 `workspace/{session_id}/core/`
## 2. 注册 EduActionBridge Autoload
## 3. 在 `scenes/main.tscn` 添加子节点：
##    `[node name="EduHooks" type="Node" parent="."]` + `pingpong_hooks.gd`
##
## 自动上报 action_id（与 config/code_anchors/pingpong.json 对齐）：
## - rally：拍子击中球（球水平速度反向）
## - score：一方得分（ball.scored 信号）
## - power_smash：大力扣杀技能激活

const PowerSmashSkill := preload("res://core/skills/power_smash.gd")

const ACTION_RALLY: String = "rally"
const ACTION_SCORE: String = "score"
const ACTION_POWER_SMASH: String = "power_smash"

const MIN_VELOCITY_X: float = 8.0

var _ball: Area2D = null
var _ball_wired: bool = false
var _prev_vel_x_sign: int = 0
var _prev_power_smash_armed: bool = false
var _game_root: Node2D = null


func _ready() -> void:
	var main: Node = get_parent()
	if main == null:
		return
	_game_root = main.get_node_or_null("GameRoot") as Node2D
	if _game_root != null:
		_game_root.child_entered_tree.connect(_on_game_root_child_entered)
	call_deferred("_scan_scene")


func _on_game_root_child_entered(_child: Node) -> void:
	call_deferred("_scan_scene")


func _scan_scene() -> void:
	_wire_ball()
	_prev_vel_x_sign = 0
	_prev_power_smash_armed = false


func _wire_ball() -> void:
	_ball_wired = false
	_ball = null
	if _game_root == null:
		return
	var game: Node = _game_root.get_node_or_null("Game")
	if game == null:
		return
	var candidate: Node = game.get_node_or_null("Ball")
	if candidate == null or not candidate is Area2D:
		return
	_ball = candidate as Area2D
	if _ball.has_signal("scored") and not _ball.is_connected("scored", _on_ball_scored):
		_ball.scored.connect(_on_ball_scored)
	_ball_wired = true


func _physics_process(_delta: float) -> void:
	if not _ball_wired or _ball == null or not is_instance_valid(_ball):
		return
	_detect_rally()
	_detect_power_smash()


func _detect_rally() -> void:
	if not _ball.has_method("get_velocity"):
		return
	var vel: Vector2 = _ball.call("get_velocity") as Vector2
	if absf(vel.x) < MIN_VELOCITY_X:
		return
	var sign: int = 1 if vel.x > 0.0 else -1
	if _prev_vel_x_sign != 0 and sign != _prev_vel_x_sign:
		_emit_action(ACTION_RALLY)
	_prev_vel_x_sign = sign


func _detect_power_smash() -> void:
	if not PowerSmashSkill.is_enabled():
		return
	var armed: bool = bool(PowerSmashSkill._armed)
	if armed and not _prev_power_smash_armed:
		_emit_action(ACTION_POWER_SMASH)
	_prev_power_smash_armed = armed


func _on_ball_scored(_side: String) -> void:
	_emit_action(ACTION_SCORE)
	_prev_vel_x_sign = 0


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
