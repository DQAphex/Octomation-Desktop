import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.plugin_dependency_manager import PluginDependencyManager


class PluginDependencyManagerTests(unittest.TestCase):
    def make_manager(self, root: Path, **kwargs) -> PluginDependencyManager:
        return PluginDependencyManager(
            project_root=root,
            plugins_dir=root / "plugins",
            execution_dir=root,
            enabled=True,
            log=lambda _message: None,
            **kwargs,
        )

    def test_extracts_email_validator_from_pydantic_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self.make_manager(Path(tmp))
            exc = ImportError(
                "email-validator is not installed, run `pip install 'pydantic[email]'`"
            )

            specs, modules = manager.extract_missing_dependencies(exc)

            self.assertEqual(modules, [])
            self.assertIn("email-validator>=2.0.0", specs)
            self.assertNotIn("email-validator", specs)

    def test_extracts_missing_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = self.make_manager(Path(tmp))
            exc = ModuleNotFoundError("No module named 'paquete_inexistente_xyz'")

            specs, modules = manager.extract_missing_dependencies(exc)

            self.assertEqual(specs, [])
            self.assertEqual(modules, ["paquete_inexistente_xyz"])

    def test_classifies_local_missing_module_as_structure_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "documentation"
            plugin.mkdir(parents=True)
            (plugin / "documentation.py").write_text("", encoding="utf-8")
            manager = self.make_manager(root)

            info = manager.classify_failure(
                ModuleNotFoundError("No module named 'plugins.documentation.documentacion'"),
                plugin,
            )

            self.assertEqual(info.kind, "plugin_structure")
            self.assertIn("plugins.documentation.documentacion", info.missing)

    def test_reads_utf16_requirements_and_skips_dev_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            (plugin / "requirements.txt").write_text(
                "requests==2.34.2\nextra-package==1.0\n",
                encoding="utf-16",
            )
            (plugin / "requirements-dev.txt").write_text(
                "pytest==8.0\n", encoding="utf-8"
            )
            manager = self.make_manager(root)

            declared = manager.collect_declared_dependencies(plugin)
            specs = [spec for spec, _source in declared]

            self.assertIn("requests==2.34.2", specs)
            self.assertIn("extra-package==1.0", specs)
            self.assertNotIn("pytest==8.0", specs)

    def test_reads_pyproject_and_metadata_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            (plugin / "pyproject.toml").write_text(
                textwrap.dedent(
                    """
                    [project]
                    name = "demo"
                    version = "0.1.0"
                    dependencies = ["pandas>=2.0", "httpx"]
                    """
                ),
                encoding="utf-8",
            )
            (plugin / "metadata.json").write_text(
                '{"dependencies": ["python-dotenv>=1.0"]}',
                encoding="utf-8",
            )
            manager = self.make_manager(root)

            specs = [
                spec for spec, _source in manager.collect_declared_dependencies(plugin)
            ]

            self.assertIn("pandas>=2.0", specs)
            self.assertIn("httpx", specs)
            self.assertIn("python-dotenv>=1.0", specs)

    def test_scans_import_graph_and_ignores_local_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            (plugin / "helpers.py").write_text(
                "VALUE = 1\n", encoding="utf-8"
            )
            entry = plugin / "demo.py"
            entry.write_text(
                textwrap.dedent(
                    """
                    import os
                    import cv2
                    from helpers import VALUE
                    from fastapi import APIRouter
                    """
                ),
                encoding="utf-8",
            )
            manager = self.make_manager(root)

            missing = manager.scan_entry_imports(plugin, entry)
            missing_specs = {item.spec for item in missing}

            self.assertIn("opencv-python", missing_specs)
            self.assertNotIn("helpers", missing_specs)
            self.assertNotIn("os", missing_specs)
            self.assertNotIn("fastapi", missing_specs)

    def test_detects_emailstr_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            entry = plugin / "demo.py"
            entry.write_text(
                "from pydantic import BaseModel, EmailStr\n", encoding="utf-8"
            )
            manager = self.make_manager(root)
            real_available = manager._module_available
            manager._module_available = (
                lambda name: False
                if name == "email_validator"
                else real_available(name)
            )

            missing = manager.scan_entry_imports(plugin, entry)
            specs = {item.spec for item in missing}

            self.assertIn("email-validator>=2.0.0", specs)

    def test_installs_missing_declared_dependency_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            (plugin / "requirements.txt").write_text(
                "paquete-inexistente-xyz==1.0\n", encoding="utf-8"
            )
            manager = self.make_manager(root)
            commands = []

            def fake_pip(command):
                commands.append(command)
                return subprocess.CompletedProcess(command, 0, stdout="ok")

            manager._run_pip = fake_pip

            first = manager.ensure_plugin_dependencies(plugin, plugin_name="demo")
            second = manager.ensure_plugin_dependencies(plugin, plugin_name="demo")

            self.assertEqual(len(first), 1)
            self.assertEqual(first[0].status, "installed")
            self.assertEqual(second, [])
            self.assertEqual(len(commands), 1)

    def test_runtime_import_failure_installs_missing_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            manager = self.make_manager(root)
            manager._run_pip = lambda command: subprocess.CompletedProcess(
                command, 0, stdout="ok"
            )

            actions = manager.resolve_import_failure(
                plugin,
                ModuleNotFoundError("No module named 'paquete_runtime_xyz'"),
                "demo",
            )

            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0].status, "installed")

    def test_runtime_import_failure_does_not_install_local_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugin = root / "plugins" / "demo"
            plugin.mkdir(parents=True)
            (plugin / "helpers.py").write_text("", encoding="utf-8")
            manager = self.make_manager(root)
            manager._run_pip = lambda command: self.fail("No debería instalar")

            actions = manager.resolve_import_failure(
                plugin,
                ModuleNotFoundError("No module named 'helpers'"),
                "demo",
            )

            self.assertEqual(actions, [])


class PluginManagerIntegrationTests(unittest.TestCase):
    def test_plugin_manager_installs_and_loads_plugin(self):
        from fastapi import FastAPI

        from core.plugin_manager import PluginManager

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plugins = root / "plugins"
            plugin = plugins / "demo"
            plugin.mkdir(parents=True)
            (plugins / "__init__.py").write_text("", encoding="utf-8")
            (plugin / "__init__.py").write_text("", encoding="utf-8")
            (plugin / "demo.py").write_text(
                textwrap.dedent(
                    """
                    import paquete_autoload_xyz
                    from fastapi import APIRouter

                    router = APIRouter()
                    """
                ),
                encoding="utf-8",
            )

            sys.path.insert(0, str(root))
            module_name = "paquete_autoload_xyz"
            try:
                sys.modules.pop(module_name, None)
                app = FastAPI()
                manager = PluginManager(app=app, project_root=root)
                manager.dependency_manager._report_path = (
                    root / "data" / "plugin_dependencies.json"
                )

                def fake_pip(command):
                    (root / f"{module_name}.py").write_text(
                        "VALUE = 1\n", encoding="utf-8"
                    )
                    return subprocess.CompletedProcess(command, 0, stdout="ok")

                manager.dependency_manager._run_pip = fake_pip
                manager.discover_and_load()

                self.assertTrue(manager.loaded_plugins)
                self.assertEqual(manager.failed_plugins, [])
                self.assertTrue(
                    any(
                        action["spec"] == "paquete-autoload-xyz"
                        and action["status"] == "installed"
                        for action in manager.dependency_manager.get_actions()
                    )
                )
            finally:
                sys.path.remove(str(root))
                sys.modules.pop(module_name, None)
                sys.modules.pop("plugins.demo.demo", None)
                sys.modules.pop("plugins.demo", None)
                for name in ("plugins",):
                    sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
