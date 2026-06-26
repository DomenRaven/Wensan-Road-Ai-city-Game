extends RefCounted


static func format_run_hud(
	title: String,
	distance_m: int,
	elapsed_sec: int,
	time_left: float,
	sprint_ready: bool
) -> String:
	var sprint_text: String = ""
	if GameConfig.has_skill("sprint_burst"):
		sprint_text = "  冲刺就绪" if sprint_ready else "  冲刺冷却"
	return "%s  距离 %dm  用时 %ds  剩余 %ds%s" % [
		title,
		distance_m,
		elapsed_sec,
		int(ceil(time_left)),
		sprint_text
	]
