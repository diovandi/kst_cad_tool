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

        class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, args):
                cls._on_command_created(args)

        created_handler = _CommandCreatedHandler()
        cmd_def.commandCreated.add(created_handler)
        cls._handlers.append(created_handler)

        if panel:
            panel.controls.addCommand(cmd_def)

    @classmethod
    def _on_command_created(cls, args):
        cmd = args.command

        class _ExecuteHandler(adsk.core.CommandEventHandler):
            def __init__(self):
                super().__init__()

            def notify(self, event_args):
                cls._on_execute(event_args)

        exec_handler = _ExecuteHandler()
        cmd.execute.add(exec_handler)
        cls._handlers.append(exec_handler)

    @classmethod
    def _on_execute(cls, args):
        app = adsk.core.Application.get()
        try:
            from ui import analysis_wizard
            analysis_wizard.run_optimization_wizard()
        except Exception as e:
            app.userInterface.messageBox("KST Optimization Wizard error: {}".format(str(e)))

