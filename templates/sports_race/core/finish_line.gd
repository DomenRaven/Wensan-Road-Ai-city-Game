extends RefCounted
class_name FinishLine


static func is_reached(distance_px: float, track_length_px: float) -> bool:
	return distance_px >= track_length_px


static func get_finish_message(elapsed_sec: float, distance_m: int) -> String:
	return "冲线！用时 %d 秒，跑了 %dm！" % [int(elapsed_sec), distance_m]
