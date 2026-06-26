extends RefCounted
class_name ScoreManager

signal score_changed(player_points: int, ai_points: int)
signal match_won(winner: String)

var player_score: int = 0
var ai_score: int = 0
var points_to_win: int = 5


func configure(points: int) -> void:
	points_to_win = maxi(1, points)
	reset()


func reset() -> void:
	player_score = 0
	ai_score = 0
	score_changed.emit(player_score, ai_score)


func add_point_to_player() -> void:
	player_score += 1
	score_changed.emit(player_score, ai_score)
	_check_win("player")


func add_point_to_ai() -> void:
	ai_score += 1
	score_changed.emit(player_score, ai_score)
	_check_win("ai")


func _check_win(winner: String) -> void:
	if player_score >= points_to_win or ai_score >= points_to_win:
		match_won.emit(winner)


func format_score() -> String:
	return "%d : %d" % [player_score, ai_score]
