import os.path
from collections import OrderedDict
from typing import Set

from loguru import logger

from .util import run_user_script, run_internal_script, get_script_output
from .util import try_run_internal_script, try_get_script_output
# Only used for type hints, package-relative import not possible due to circular reference
import orchestra.model.configuration


class Action:
    def __init__(self, name, script, config):
        self.name = name
        self.config: "orchestra.model.configuration.Configuration" = config
        self._explicit_dependencies: Set[Action] = set()
        self._script = script

    def run(self, pretend=False, **kwargs):
        logger.info(f"Executing {self}")
        if not pretend:
            self._run(**kwargs)

    def _run(self, **kwargs):
        """Executes the action"""
        self._run_user_script(self.script)

    @property
    def script(self):
        """Unless _run is overridden, should return the script to run"""
        return self._script

    def add_explicit_dependency(self, dependency):
        self._explicit_dependencies.add(dependency)

    @property
    def dependencies(self):
        return self._explicit_dependencies.union(self._implicit_dependencies())

    @property
    def dependencies_for_hash(self):
        return self._explicit_dependencies.union(self._implicit_dependencies_for_hash())

    def _implicit_dependencies(self):
        return set()

    def _implicit_dependencies_for_hash(self):
        return self._implicit_dependencies()

    def is_satisfied(self):
        """Returns true if the action is satisfied."""
        raise NotImplementedError()

    @property
    def environment(self) -> OrderedDict:
        """Returns additional environment variables provided to the script to be run"""
        return self.config.global_env()

    @property
    def _target_name(self):
        raise NotImplementedError("Action subclasses must implement _target_name")

    @property
    def name_for_info(self):
        return f"{self.name} {self._target_name}"

    @property
    def name_for_graph(self):
        return self.name_for_info

    @property
    def name_for_components(self):
        return self._target_name

    def __str__(self):
        return f"Action {self.name} of {self._target_name}"

    def __repr__(self):
        return self.__str__()

    def _run_user_script(self, script, cwd=None):
        run_user_script(script, environment=self.environment, cwd=cwd)

    def _run_internal_script(self, script, cwd=None):
        run_internal_script(script, environment=self.environment, cwd=cwd)

    def _try_run_internal_script(self, script, cwd=None):
        return try_run_internal_script(script, environment=self.environment, cwd=cwd)

    def _get_script_output(self, script, cwd=None):
        return get_script_output(script, environment=self.environment, cwd=cwd)

    def _try_get_script_output(self, script, cwd=None):
        return try_get_script_output(script, environment=self.environment, cwd=cwd)


class ActionForComponent(Action):
    def __init__(self, name, component, script, config):
        super().__init__(name, script, config)
        self.component = component

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["SOURCE_DIR"] = os.path.join(self.config.sources_dir, self.component.name)
        return env

    @property
    def _target_name(self):
        return self.component.name


class ActionForBuild(ActionForComponent):
    def __init__(self, name, build, script, config):
        super().__init__(name, build.component, script, config)
        self.build = build

    @property
    def environment(self) -> OrderedDict:
        env = super().environment
        env["BUILD_DIR"] = os.path.join(self.config.builds_dir,
                                        self.build.component.name,
                                        self.build.name)
        env["TMP_ROOT"] = os.path.join(env["TMP_ROOTS"], self.build.safe_name)
        return env

    @property
    def _target_name(self):
        return self.build.qualified_name
