"""
Fusion 360 command: KST Optimization Wizard.
Opens the tkinter Optimization Wizard (constraint selection, search space, run optimization).
"""

import adsk.core
import os
import sys

_ADDIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ADDIN_DIR not in sys.path:
    sys.path.insert(0, _ADDIN_DIR)
if not os.path.exists(os.path.join(_ADDIN_DIR, "kst_rating_tool")):
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_ADDIN_DIR)))
    _src = os.path.join(_REPO_ROOT, "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)


class OptimizationCommand:
    _handlers = []

    @classmethod
    def register(cls, cmd_id, panel):
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_defs = ui.commandDefinitions
        cmd_def = cmd_defs.addButtonDefinition(
            cmd_id,
            "KST Optimization Wizard",
            "Open KST Optimization Wizard",
            ""
        )
        cls._handlers.append(cmd_def.commandCreated.add(cls._on_command_created))
        if panel:
            panel.controls.addCommand(cmd_def)

    @classmethod
    def _on_command_created(cls, args):
        args.command.execute.add(cls._on_execute)

    @classmethod
    def _on_execute(cls, args):
        app = adsk.core.Application.get()
        try:
            from ui import analysis_wizard
            analysis_wizard.run_optimization_wizard()
        except Exception as e:
            app.userInterface.messageBox("KST Optimization Wizard error: {}".format(str(e)))

