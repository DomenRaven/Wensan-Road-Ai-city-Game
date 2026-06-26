extends RefCounted
class_name TimerBarHelper


static func setup(bar: ProgressBar, total_sec: float) -> void:
	bar.min_value = 0.0
	bar.max_value = total_sec
	bar.value = 0.0
	bar.visible = true


static func set_elapsed(bar: ProgressBar, elapsed_sec: float) -> void:
	bar.value = clampf(elapsed_sec, bar.min_value, bar.max_value)


static func hide_bar(bar: ProgressBar) -> void:
	bar.visible = false
	bar.value = 0.0
