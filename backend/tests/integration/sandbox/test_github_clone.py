"""
Phase 3.5: GitHub Clone Integration Tests

These tests verify that sandbox workers can clone GitHub repositories
and checkout feature branches on startup.
"""


class TestGitHubEnvVars:
    """Test that spawner passes GitHub credentials to sandbox."""

    def test_spawner_accepts_github_env_vars(self):
        """
        SPEC: DaytonaSpawnerService should accept GitHub credentials via extra_env.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()

        # spawn_for_task accepts extra_env parameter
        import inspect

        sig = inspect.signature(spawner.spawn_for_task)
        params = list(sig.parameters.keys())

        assert "extra_env" in params


class TestWorkerScriptGitClone:
    """Test that worker scripts include GitHub clone functionality."""

    def test_worker_script_clones_repo_on_startup(self):
        """
        SPEC: Worker script should clone repo if GITHUB_TOKEN is provided.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Verify clone logic exists
        assert "git clone" in script or "clone_repo" in script
        assert "GITHUB_TOKEN" in script
        assert "GITHUB_REPO" in script

    def test_claude_worker_script_clones_repo_on_startup(self):
        """
        SPEC: Claude worker script should clone repo if GITHUB_TOKEN is provided.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify clone logic exists
        assert "git clone" in script or "clone_repo" in script
        assert "GITHUB_TOKEN" in script
        assert "GITHUB_REPO" in script

    def test_worker_script_checks_out_branch(self):
        """
        SPEC: Worker script should checkout the feature branch after cloning.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Verify branch checkout
        assert "checkout" in script.lower()
        assert "BRANCH_NAME" in script

    def test_claude_worker_script_checks_out_branch(self):
        """
        SPEC: Claude worker script should checkout the feature branch after cloning.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Verify branch checkout
        assert "checkout" in script.lower()
        assert "BRANCH_NAME" in script


class TestWorkerScriptGracefulFallback:
    """Test that workers handle missing GitHub credentials gracefully."""

    def test_worker_script_handles_missing_github_gracefully(self):
        """
        SPEC: Worker should start normally even without GitHub credentials.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Should have conditional check for GITHUB vars
        assert "if" in script.lower() and "GITHUB" in script

    def test_claude_worker_script_handles_missing_github_gracefully(self):
        """
        SPEC: Claude worker should start normally even without GitHub credentials.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Should have conditional check for GITHUB vars
        assert "if" in script.lower() and "GITHUB" in script


class TestWorkerScriptGitConfig:
    """Test that worker scripts configure git properly."""

    def test_worker_script_configures_git_user(self):
        """
        SPEC: Worker should configure git user for commits.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_worker_script()

        # Should configure git identity (either literal or as subprocess array)
        has_git_config = "git config" in script.lower() or (
            '"git"' in script and '"config"' in script
        )
        assert has_git_config

    def test_claude_worker_script_configures_git_user(self):
        """
        SPEC: Claude worker should configure git user for commits.
        """
        from omoi_os.services.daytona_spawner import DaytonaSpawnerService

        spawner = DaytonaSpawnerService()
        script = spawner._get_claude_worker_script()

        # Should configure git identity (either literal or as subprocess array)
        has_git_config = "git config" in script.lower() or (
            '"git"' in script and '"config"' in script
        )
        assert has_git_config
