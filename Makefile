# Run these targets from INSIDE the dev container (see docker-compose.yml / docs/docker.md),
# where UE_ROOT and the bind-mounted repo/engine paths are already set up.
.PHONY: help editor game

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

editor: ## Launch the Unreal Editor (Blocks project)
	$(UE_ROOT)/Engine/Binaries/Linux/UnrealEditor /workspace/ProjectAirSim/unreal/Blocks/Blocks.uproject

game: ## Launch the Unreal Blocks project directly in Game mode
	$(UE_ROOT)/Engine/Binaries/Linux/UnrealEditor /workspace/ProjectAirSim/unreal/Blocks/Blocks.uproject -game
