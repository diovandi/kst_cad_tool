using System;
using System.Collections.Generic;
using System.Windows.Forms;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Constraint Definition Wizard dialog. Shows a table with columns:
    /// Type (Point/Pin/Line/Plane), Location (Select), Orientation (Select).
    /// Uses IGeometrySelector for CAD-specific geometry picking; coordinates populate the table.
    /// "Analyze" generates the input file (JSON) for the Python/MATLAB backend.
    /// </summary>
    public class ConstraintDefinitionWizard : Form
    {
        private readonly IGeometrySelector _geometrySelector;
        private DataGridView _constraintGrid;
        private Button _btnAnalyze;
        private Button _btnAddRow;
        private Button _btnRemoveRow;
        private Label _lblResults;
        private int _nextRowIndex = 1;

        /// <summary>Create wizard with the given geometry selector (provided by the CAD add-in).</summary>
        public ConstraintDefinitionWizard(IGeometrySelector geometrySelector)
        {
            _geometrySelector = geometrySelector ?? throw new ArgumentNullException("geometrySelector");
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
            var pt = _geometrySelector.SelectPoint("Select a point or face center for constraint location.");
            if (pt == null || pt.Location == null || pt.Location.Length < 3) return;
            var locStr = string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:G}, {1:G}, {2:G}", pt.Location[0], pt.Location[1], pt.Location[2]);
            _constraintGrid.Rows[rowIndex].Cells[1].Value = locStr;
        }

        private void SelectOrientation(int rowIndex)
        {
            // Prefer axis (edge/cylinder) for direction; fallback to plane normal (face).
            var axis = _geometrySelector.SelectAxis("Select an edge or cylindrical face for constraint orientation (axis).");
            if (axis != null && axis.Location != null && axis.Location.Length >= 3 && axis.Direction != null && axis.Direction.Length >= 3)
            {
                var orientStr = string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:G}, {1:G}, {2:G}", axis.Direction[0], axis.Direction[1], axis.Direction[2]);
                _constraintGrid.Rows[rowIndex].Cells[2].Value = orientStr;
                return;
            }
            var plane = _geometrySelector.SelectPlane("Select a face for constraint normal (orientation).");
            if (plane != null && plane.Normal != null && plane.Normal.Length >= 3)
            {
                var orientStr = string.Format(System.Globalization.CultureInfo.InvariantCulture, "{0:G}, {1:G}, {2:G}", plane.Normal[0], plane.Normal[1], plane.Normal[2]);
                _constraintGrid.Rows[rowIndex].Cells[2].Value = orientStr;
            }
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
                _lblResults.Text = "Input file written to:\r\n" + path + "\r\n\r\nRun Python (kst_rating_tool) or MATLAB to analyze.";
            }
            catch (Exception ex)
            {
                _lblResults.Text = "Error: " + ex.Message;
            }
        }
    }
}
