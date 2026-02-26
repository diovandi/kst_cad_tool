using System;
using System.IO;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Windows.Forms;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.swpublished;
using KstAnalysisWizard;

namespace KstSwAddIn
{
    [ComVisible(true)]
    [Guid("C3D4E5F6-A7B8-9012-CDEF-123456789012")]
    [SwAddin(Description = "KST Constraint Analysis Wizard", Title = "KST Analysis Wizard", LoadAtStartup = false)]
    public class KstSwAddIn : ISwAddin
    {
        private const string SwAddInRegKey = @"SOFTWARE\SolidWorks\Addins\{C3D4E5F6-A7B8-9012-CDEF-123456789012}";

        [ComRegisterFunction]
        public static void RegisterFunction(Type t)
        {
            try
            {
                using (var key = Registry.LocalMachine.CreateSubKey(SwAddInRegKey))
                {
                    if (key != null)
                    {
                        key.SetValue(null, 0);
                        key.SetValue("Description", "KST Constraint Analysis Wizard");
                        key.SetValue("Title", "KST Analysis Wizard");
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Registration failed: " + ex.Message);
            }
        }

        [ComUnregisterFunction]
        public static void UnregisterFunction(Type t)
        {
            try
            {
                Registry.LocalMachine.DeleteSubKey(SwAddInRegKey, false);
            }
            catch { }
        }
        private SldWorks _swApp;
        private int _cookie;
        private CommandManager _cmdMgr;

        public bool ConnectToSW(object ThisSW, int cookie)
        {
            _swApp = (SldWorks)ThisSW;
            _cookie = cookie;
            try
            {
                _swApp.SetAddinCallbackInfo2(0, this, cookie);
                _cmdMgr = (CommandManager)_swApp.GetCommandManager(cookie);
                if (_cmdMgr != null)
                {
                    AddCommands();
                }
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show("KST Add-in ConnectToSW error: " + ex.Message);
                return false;
            }
        }

        public bool DisconnectFromSW()
        {
            try
            {
                if (_cmdMgr != null)
                {
                    RemoveCommands();
                    Marshal.ReleaseComObject(_cmdMgr);
                    _cmdMgr = null;
                }
                if (_swApp != null)
                {
                    Marshal.ReleaseComObject(_swApp);
                    _swApp = null;
                }
            }
            catch { }
            return true;
        }

        private void AddCommands()
        {
            const string wizardCmdId = "KstSw:AnalysisWizard";
            const string optimCmdId = "KstSw:OptimizationWizard";
            try
            {
                if (_cmdMgr.GetCommandGroup(cookie: _cookie) != null)
                    _cmdMgr.RemoveCommandGroup(_cookie);
            }
            catch { }

            CommandGroup cmdGroup = _cmdMgr.CreateCommandGroup2(_cookie, "KST Analysis", "KST Analysis Wizard", "KST Constraint Analysis", -1);
            if (cmdGroup == null) return;

            CommandItem cmdItem = cmdGroup.AddCommandItem2("KST Analysis Wizard", -1, "Open KST Constraint Analysis Wizard", "Define constraints from the model and run assembly rating analysis", wizardCmdId, "KstAnalysisWizard", (int)swCommandItemType_e.swMenuItem);
            if (cmdItem != null)
                cmdItem.OnActivate += OnWizardActivate;

            cmdItem = cmdGroup.AddCommandItem2("KST Optimization Wizard", -1, "Open KST Optimization Wizard", "Select constraint to optimize, define search space, run optimization", optimCmdId, "KstOptimizationWizard", (int)swCommandItemType_e.swMenuItem);
            if (cmdItem != null)
                cmdItem.OnActivate += OnOptimActivate;

            cmdGroup.HasMenu = false;
            cmdGroup.HasToolbar = true;
            cmdGroup.Activate();
        }

        private void RemoveCommands()
        {
            try
            {
                if (_cmdMgr != null)
                {
                    CommandGroup grp = _cmdMgr.GetCommandGroup(cookie: _cookie);
                    if (grp != null)
                        _cmdMgr.RemoveCommandGroup(_cookie);
                }
            }
            catch { }
        }

        private void OnWizardActivate()
        {
            try
            {
                var selector = new SwGeometrySelector(_swApp);
                var wizard = new ConstraintDefinitionWizard(selector);
                wizard.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show("KST Analysis Wizard error: " + ex.Message, "KST Add-in");
            }
        }

        private void OnOptimActivate()
        {
            try
            {
                var optimPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis", "wizard_input.json");
                var form = new OptimizationWizardForm(File.Exists(optimPath) ? optimPath : null);
                form.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show("KST Optimization Wizard error: " + ex.Message, "KST Add-in");
            }
        }
    }
}
