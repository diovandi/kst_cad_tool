using System;
using System.Collections.Generic;
using System.Windows.Forms;
using Inventor;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Constraint Definition Wizard dialog. Shows a table with columns:
    /// Type (Point/Pin/Line/Plane), Location (Select), Orientation (Select).
    /// User selects geometry in the CAD model; coordinates populate the table.
    /// "Analyze" generates the input file and runs MATLAB (or compiled executable).
    /// </summary>
    public class ConstraintDefinitionWizard : Form
    {
        private readonly Inventor.Application _inventorApp;
        private DataGridView _constraintGrid;
        private Button _btnAnalyze;
        private Button _btnAddRow;
        private Button _btnRemoveRow;
        private Label _lblResults;
        private int _nextRowIndex = 1;

        public ConstraintDefinitionWizard(Inventor.Application inventorApp)
        {
            _inventorApp = inventorApp;
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            Text = "KST Constraint Definition Wizard";
            Size = new System.Drawing.Size(700, 500);
            StartPosition = FormStartPosition.CenterParent;
            FormBorderStyle = FormBorderStyle.Sizable;

            _constraintGrid = new DataGridView
            {
                Dock = DockStyle.Top,
                Height = 250,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
                AllowUserToAddRows = false,
                ReadOnly = false
            };
            _constraintGrid.Columns.Add("Type", "Type");
            _constraintGrid.Columns.Add("Location", "Location (x,y,z)");
            _constraintGrid.Columns.Add("Orientation", "Orientation (nx,ny,nz or axis)");
            var btnLoc = new DataGridViewButtonColumn { Name = "SelectLoc", HeaderText = "Select Loc", Text = "Select", UseColumnTextForButtonValue = true };
            var btnOrient = new DataGridViewButtonColumn { Name = "SelectOrient", HeaderText = "Select Orient", Text = "Select", UseColumnTextForButtonValue = true };
            _constraintGrid.Columns.Add(btnLoc);
            _constraintGrid.Columns.Add(btnOrient);
            _constraintGrid.CellClick += ConstraintGrid_CellClick;

            var btnPanel = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40 };
            _btnAddRow = new Button { Text = "Add constraint", Width = 120 };
            _btnRemoveRow = new Button { Text = "Remove selected", Width = 120 };
            _btnAnalyze = new Button { Text = "Analyze", Width = 120 };
            _btnAddRow.Click += (s, e) => AddConstraintRow();
            _btnRemoveRow.Click += (s, e) => RemoveSelectedRow();
            _btnAnalyze.Click += (s, e) => RunAnalysis();
            btnPanel.Controls.Add(_btnAddRow);
            btnPanel.Controls.Add(_btnRemoveRow);
            btnPanel.Controls.Add(_btnAnalyze);

            _lblResults = new Label
            {
                Dock = DockStyle.Fill,
                AutoSize = false,
                Text = "Define constraints above, then click Analyze.",
                Padding = new Padding(8)
            };

            Controls.Add(_lblResults);
            Controls.Add(btnPanel);
            Controls.Add(_constraintGrid);

            AddConstraintRow();
        }

        private void ConstraintGrid_CellClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            var colName = _constraintGrid.Columns[e.ColumnIndex].Name;
            if (colName == "SelectLoc")
                SelectLocation(e.RowIndex);
            else if (colName == "SelectOrient")
                SelectOrientation(e.RowIndex);
        }

        private void SelectLocation(int rowIndex)
        {
            MessageBox.Show("Select a point or face in the model for location.\n\nGeometry selection will use Inventor SelectSet/InteractionEvents; implement in add-in with Inventor API.", "Select Location");
        }

        private void SelectOrientation(int rowIndex)
        {
            MessageBox.Show("Select a face (for normal) or edge (for axis) in the model for orientation.\n\nImplement with Inventor API Face.Evaluator.GetNormal or edge direction.", "Select Orientation");
        }

        private void AddConstraintRow()
        {
            _constraintGrid.Rows.Add("Point", "", "", "Select", "Select");
            _nextRowIndex++;
        }

        private void RemoveSelectedRow()
        {
            if (_constraintGrid.CurrentRow != null && !_constraintGrid.CurrentRow.IsNewRow)
                _constraintGrid.Rows.RemoveAt(_constraintGrid.CurrentRow.Index);
        }

        private void RunAnalysis()
        {
            try
            {
                var path = InputFileGenerator.WriteInputFile(_constraintGrid);
                _lblResults.Text = "Input file written to:\r\n" + path + "\r\n\r\nRun MATLAB or compiled executable to analyze. Integration coming next.";
            }
            catch (Exception ex)
            {
                _lblResults.Text = "Error: " + ex.Message;
            }
        }
    }
}
