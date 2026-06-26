extends RefCounted
class_name DoubleJumpSkill

## Prefabricated skill — jump logic wired in player_runner.gd


static func is_enabled() -> bool:
	return GameConfig.has_skill("double_jump")
