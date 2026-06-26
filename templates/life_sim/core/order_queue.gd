extends RefCounted
class_name LifeSimOrderQueue

var orders_completed: int = 0
var orders_to_win: int = 3
var current_dish: String = "田园沙拉"
var patience_sec: float = 30.0
var patience_left: float = 30.0
var coins_earned: int = 0
var coins_per_order: int = 10


func configure(dish_id: String, count_to_win: int, patience: float, reward: int) -> void:
	current_dish = dish_id
	orders_to_win = count_to_win
	patience_sec = patience
	patience_left = patience
	coins_per_order = reward


func reset_patience() -> void:
	patience_left = patience_sec


func tick(delta: float) -> void:
	if patience_left > 0.0:
		patience_left = maxf(0.0, patience_left - delta)


func complete_order() -> int:
	orders_completed += 1
	var bonus: float = clampf(patience_left / patience_sec, 0.5, 1.0)
	var payout: int = int(round(float(coins_per_order) * bonus))
	coins_earned += payout
	reset_patience()
	return payout


func is_won() -> bool:
	return orders_completed >= orders_to_win


func get_order_label() -> String:
	return "订单 %d/%d · 需要 %s" % [orders_completed + 1, orders_to_win, current_dish]
