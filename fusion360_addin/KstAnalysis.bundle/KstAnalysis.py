"""
KST Analysis Wizard - Fusion 360 Add-in entry point.

Run from Fusion 360: Scripts and Add-Ins -> Add-Ins tab -> KST Analysis Wizard -> Run.
Registers "KST Analysis Wizard" and "KST Optimization Wizard" commands.
"""

import adsk.core
import adsk.fusion
import os
import sys

# Add add-in dir; add repo src only if kst_rating_tool is not bundled inside add-in
_ADDIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _ADDIN_DIR not in sys.path:
    sys.path.insert(0, _ADDIN_DIR)
_bundled = os.path.exists(os.path.join(_ADDIN_DIR, "kst_rating_tool"))
if not _bundled:
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_ADDIN_DIR)))
    _src = os.path.join(_REPO_ROOT, "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)


def run(context):
    """Fusion 360 add-in entry. Register commands."""
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        cmd_defs = ui.commandDefinitions
        panel = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if panel is None:
            panel = ui.allToolbarPanels.itemById("AddInsPanel")

        # KST Analysis Wizard command
        analysis_cmd_id = "KstAnalysis_Wizard"
        if cmd_defs.itemById(analysis_cmd_id):
            cmd_defs.itemById(analysis_cmd_id).deleteMe()
        import commands.analysis_command as ac
        ac.AnalysisCommand.register(analysis_cmd_id, panel)

        # KST Optimization Wizard command
        optim_cmd_id = "KstAnalysis_OptimWizard"
        if cmd_defs.itemById(optim_cmd_id):
            cmd_defs.itemById(optim_cmd_id).deleteMe()
        import commands.optimization_command as oc
        oc.OptimizationCommand.register(optim_cmd_id, panel)

    except Exception as e:
        if ui:
            ui.messageBox("KST Add-in run error: {}".format(str(e)))


def stop(context):
    """Clean up when add-in is stopped."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        for cmd_id in ("KstAnalysis_Wizard", "KstAnalysis_OptimWizard"):
            cmd = ui.commandDefinitions.itemById(cmd_id)
            if cmd:
                cmd.deleteMe()
    except Exception:
        pass
