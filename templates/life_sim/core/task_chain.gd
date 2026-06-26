extends RefCounted
class_name LifeSimTaskChain

enum Step { GET, PROCESS, DELIVER }

var current_step: Step = Step.GET


func reset() -> void:
	current_step = Step.GET


func advance() -> void:
	match current_step:
		Step.GET:
			current_step = Step.PROCESS
		Step.PROCESS:
			current_step = Step.DELIVER
		Step.DELIVER:
			current_step = Step.GET


func get_step_label() -> String:
	match current_step:
		Step.GET:
			return "① 点击菜园收获"
		Step.PROCESS:
			return "② 点击灶台烹饪"
		Step.DELIVER:
			return "③ 点击顾客上菜"
	return ""


func get_target_hotspot() -> String:
	match current_step:
		Step.GET:
			return "farm"
		Step.PROCESS:
			return "stove"
		Step.DELIVER:
			return "customer"
	return ""
