using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using Inventor;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Inventor Add-in server. Registers the "KST Analysis Wizard" ribbon button
    /// and launches the Constraint Definition Wizard on click.
    /// </summary>
    [Guid("E8A1B2C3-D4E5-4F67-8901-234567890ABC")]
    public class KstAddInServer : Inventor.ApplicationAddInServer
    {
        private Inventor.Application _inventorApp;
        private ButtonDefinition _wizardButtonDef;
        private ButtonDefinition _optimButtonDef;
        private const string AddInGuid = "E8A1B2C3-D4E5-4F67-8901-234567890ABC";

        public void Activate(Inventor.ApplicationAddInSite addInSiteObject, bool firstTime)
        {
            _inventorApp = addInSiteObject.Application;

            var ctrlDefs = _inventorApp.CommandManager.ControlDefinitions;
            try
            {
                _wizardButtonDef = ctrlDefs["Autodesk:KstAnalysis:WizardButton"] as ButtonDefinition;
            }
            catch
            {
                _wizardButtonDef = ctrlDefs.AddButtonDefinition(
                    "KST Analysis Wizard",
                    "Autodesk:KstAnalysis:WizardButton",
                    CommandTypesEnum.kEditMaskCmdType,
                    AddInGuid,
                    "Open KST Constraint Analysis Wizard",
                    "Define constraints from the model and run assembly rating analysis.",
                    null,
                    null,
                    ButtonDisplayEnum.kDisplayTextInLearningMode);
            }
            try
            {
                _optimButtonDef = ctrlDefs["Autodesk:KstAnalysis:OptimButton"] as ButtonDefinition;
            }
            catch
            {
                _optimButtonDef = ctrlDefs.AddButtonDefinition(
                    "KST Optimization Wizard",
                    "Autodesk:KstAnalysis:OptimButton",
                    CommandTypesEnum.kEditMaskCmdType,
                    AddInGuid,
                    "Open KST Optimization Wizard",
                    "Select constraint to optimize, define search space, generate plan and run optimization.",
                    null,
                    null,
                    ButtonDisplayEnum.kDisplayTextInLearningMode);
            }

            var ribbon = _inventorApp.UserInterfaceManager.Ribbons["Part"];
            if (ribbon != null)
            {
                var tab = ribbon.RibbonTabs["id_TabPartAssemble"];
                if (tab != null)
                {
                    var panel = tab.RibbonPanels["id_PanelAssemble"];
                    if (panel != null)
                    {
                        panel.CommandControls.AddButton(_wizardButtonDef, true);
                        panel.CommandControls.AddButton(_optimButtonDef, true);
                    }
                }
            }

            _wizardButtonDef.OnExecute += OnWizardButtonExecute;
            _optimButtonDef.OnExecute += OnOptimButtonExecute;
        }

        private void OnOptimButtonExecute(NameValueMap context)
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

        private void OnWizardButtonExecute(NameValueMap context)
        {
            try
            {
                var wizard = new ConstraintDefinitionWizard(_inventorApp);
                wizard.ShowDialog();
            }
            catch (Exception ex)
            {
                MessageBox.Show("KST Analysis Wizard error: " + ex.Message, "KST Add-in");
            }
        }

        public void Deactivate()
        {
            if (_wizardButtonDef != null)
            {
                _wizardButtonDef.OnExecute -= OnWizardButtonExecute;
                Marshal.ReleaseComObject(_wizardButtonDef);
            }
            if (_optimButtonDef != null)
            {
                _optimButtonDef.OnExecute -= OnOptimButtonExecute;
                Marshal.ReleaseComObject(_optimButtonDef);
            }
            if (_inventorApp != null)
            {
                Marshal.ReleaseComObject(_inventorApp);
                _inventorApp = null;
            }
            GC.WaitForPendingFinalizers();
            GC.Collect();
        }

        public void ExecuteCommand(int commandID) { }

        public object Automation => null;
    }
}
