using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using System.Web.Script.Serialization;

namespace KstAnalysisWizard
{
    internal class KstOptimizationFile
    {
        public int version { get; set; } = 1;
        public KstInputFile analysis_input { get; set; }
        public OptimizationData optimization { get; set; }
    }

    internal class OptimizationData
    {
        public List<ModifiedConstraint> modified_constraints { get; set; } = new List<ModifiedConstraint>();
        public List<CandidateMatrixItem> candidate_matrix { get; set; } = new List<CandidateMatrixItem>();
    }

    internal class ModifiedConstraint
    {
        public string type { get; set; }
        public int index { get; set; }
        public SearchSpace search_space { get; set; }
    }

    internal class SearchSpace
    {
        public string type { get; set; }
        public double[] origin { get; set; }
        public double[] direction { get; set; }
        public int num_steps { get; set; }
    }

    internal class CandidateMatrixItem
    {
        public int constraint_index { get; set; }
        public List<double[]> candidates { get; set; } = new List<double[]>();
    }

    /// <summary>
    /// Optimization Wizard: select constraint to optimize, search space type (discrete/line/plane/orient),
    /// generate candidate matrix and optimization plan JSON; run optimization and show results.
    /// </summary>
    public class OptimizationWizardForm : Form
    {
        private class KstOptimizationFile
        {
            public int version { get; set; } = 1;
            public KstInputFile analysis_input { get; set; }
            public OptimizationData optimization { get; set; }
        }

        private class OptimizationData
        {
            public List<ModifiedConstraint> modified_constraints { get; set; } = new List<ModifiedConstraint>();
            public List<CandidateMatrixItem> candidate_matrix { get; set; } = new List<CandidateMatrixItem>();
        }

        private class ModifiedConstraint
        {
            public string type { get; set; }
            public int index { get; set; }
            public SearchSpace search_space { get; set; }
        }

        private class SearchSpace
        {
            public string type { get; set; }
            public double[] origin { get; set; }
            public double[] direction { get; set; }
            public int num_steps { get; set; }
        }

        private class CandidateMatrixItem
        {
            public int constraint_index { get; set; }
            public List<double[]> candidates { get; set; } = new List<double[]>();
        }

        private ComboBox _comboConstraint;
        private ComboBox _comboSearchType;
        private TextBox _txtNumSteps;
        private TextBox _txtLineOrigin;
        private TextBox _txtLineDirection;
        private Button _btnGenerate;
        private Button _btnRun;
        private Button _btnLoadResults;
        private DataGridView _resultsGrid;
        private Label _lblStatus;
        private string _lastAnalysisPath;

        public OptimizationWizardForm(string analysisInputPath = null)
        {
            _lastAnalysisPath = analysisInputPath;
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            Text = "KST Optimization Wizard";
            Size = new Size(600, 480);
            StartPosition = FormStartPosition.CenterParent;
            FormBorderStyle = FormBorderStyle.Sizable;

            var topPanel = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 120, Padding = new Padding(8) };
            topPanel.Controls.Add(new Label { Text = "Constraint to optimize:", Width = 140 });
            _comboConstraint = new ComboBox { Width = 120, DropDownStyle = ComboBoxStyle.DropDownList };
            for (int i = 1; i <= 24; i++) _comboConstraint.Items.Add("CP" + i);
            _comboConstraint.SelectedIndex = 0;
            topPanel.Controls.Add(_comboConstraint);

            topPanel.Controls.Add(new Label { Text = "Search space:", Width = 100 });
            _comboSearchType = new ComboBox { Width = 140, DropDownStyle = ComboBoxStyle.DropDownList };
            _comboSearchType.Items.AddRange(new object[] { "Line", "Discrete", "Orient 1D", "Orient 2D" });
            _comboSearchType.SelectedIndex = 0;
            topPanel.Controls.Add(_comboSearchType);

            topPanel.Controls.Add(new Label { Text = "Steps:", Width = 40 });
            _txtNumSteps = new TextBox { Width = 50, Text = "5" };
            topPanel.Controls.Add(_txtNumSteps);

            topPanel.Controls.Add(new Label { Text = "Line origin (x,y,z):", Width = 120 });
            _txtLineOrigin = new TextBox { Width = 150, Text = "0, 0, 4" };
            topPanel.Controls.Add(_txtLineOrigin);
            topPanel.Controls.Add(new Label { Text = "Line direction (x,y,z):", Width = 120 });
            _txtLineDirection = new TextBox { Width = 150, Text = "0, 0, 1" };
            topPanel.Controls.Add(_txtLineDirection);

            _btnGenerate = new Button { Text = "Generate optimization plan", Width = 180 };
            _btnGenerate.Click += BtnGenerate_Click;
            topPanel.Controls.Add(_btnGenerate);
            _btnRun = new Button { Text = "Run optimization", Width = 120 };
            _btnRun.Click += BtnRun_Click;
            topPanel.Controls.Add(_btnRun);
            _btnLoadResults = new Button { Text = "Load results", Width = 100 };
            _btnLoadResults.Click += BtnLoadResults_Click;
            topPanel.Controls.Add(_btnLoadResults);

            _resultsGrid = new DataGridView
            {
                Dock = DockStyle.Top,
                Height = 180,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
                AllowUserToAddRows = false
            };
            _resultsGrid.Columns.Add("Candidate", "Candidate");
            _resultsGrid.Columns.Add("WTR", "WTR");
            _resultsGrid.Columns.Add("MTR", "MTR");
            _resultsGrid.Columns.Add("TOR", "TOR");

            _lblStatus = new Label { Dock = DockStyle.Fill, AutoSize = false, Padding = new Padding(8), Text = "Load analysis input or generate plan, then run optimization (MATLAB or Python)." };

            Controls.Add(_lblStatus);
            Controls.Add(_resultsGrid);
            Controls.Add(topPanel);
        }

        private void BtnGenerate_Click(object sender, EventArgs e)
        {
            try
            {
                int constraintIndex = _comboConstraint.SelectedIndex + 1;
                int steps = int.Parse(_txtNumSteps.Text);
                if (steps < 1 || steps > 100) steps = 5;
                double[] origin = ParseDoubles(_txtLineOrigin.Text, 3);
                double[] direction = ParseDoubles(_txtLineDirection.Text, 3);
                if (origin == null) origin = new[] { 0.0, 0.0, 4.0 };
                if (direction == null) direction = new[] { 0.0, 0.0, 1.0 };
                Normalize(direction);

                var serializer = new JavaScriptSerializer();
                var optimFile = new KstOptimizationFile();

                var analysisPath = !string.IsNullOrEmpty(_lastAnalysisPath) && File.Exists(_lastAnalysisPath)
                    ? _lastAnalysisPath
                    : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis", "wizard_input.json");

                if (File.Exists(analysisPath))
                {
                    var fileContent = File.ReadAllText(analysisPath);
                    try
                    {
                        optimFile.analysis_input = serializer.Deserialize<KstInputFile>(fileContent);
                    }
                    catch (InvalidOperationException)
                    {
                        // Fallback if file format or deserialization fails
                        optimFile.analysis_input = GetDefaultAnalysisInput();
                    }
                    catch (ArgumentException)
                    {
                        // Fallback if file format or deserialization fails
                        optimFile.analysis_input = GetDefaultAnalysisInput();
                    }
                }
                else
                {
                    optimFile.analysis_input = GetDefaultAnalysisInput();
                }

                var modCon = new ModifiedConstraint
                {
                    type = "point",
                    index = constraintIndex,
                    search_space = new SearchSpace
                    {
                        type = "line",
                        origin = origin,
                        direction = direction,
                        num_steps = steps
                    }
                };

                var candItem = new CandidateMatrixItem
                {
                    constraint_index = constraintIndex
                };

                for (int k = 0; k <= steps; k++)
                {
                    double t = (double)k / steps;
                    double x = origin[0] + t * direction[0];
                    double y = origin[1] + t * direction[1];
                    double z = origin[2] + t * direction[2];
                    candItem.candidates.Add(new[] { x, y, z, 0.0, 0.0, -1.0 });
                }

                optimFile.optimization = new OptimizationData();
                optimFile.optimization.modified_constraints.Add(modCon);
                optimFile.optimization.candidate_matrix.Add(candItem);

                var json = serializer.Serialize(optimFile);

                var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis");
                Directory.CreateDirectory(dir);
                var path = Path.Combine(dir, "wizard_optimization.json");
                File.WriteAllText(path, json);
                _lastAnalysisPath = Path.Combine(dir, "wizard_input.json");
                _lblStatus.Text = "Optimization plan written to:\r\n" + path;
            }
            catch (Exception ex)
            {
                if (Logger.LogError(ex))
                {
                    _lblStatus.Text = "An unexpected error occurred. Details were written to the log file:\r\n" + Logger.LogPath;
                }
                else
                {
                    _lblStatus.Text = "An unexpected error occurred.";
                }
            }
        }

        private KstInputFile GetDefaultAnalysisInput()
        {
            var input = new KstInputFile();
            input.point_contacts.Add(new[] { 0.0, 0.0, 0.0, 0.0, 0.0, 1.0 });
            return input;
        }

        private void BtnRun_Click(object sender, EventArgs e)
        {
            MessageBox.Show("Run MATLAB script run_wizard_optimization.m or Python optimization with the generated wizard_optimization.json path. Results will be in results_wizard_optim.txt. Then click Load results.", "Run optimization");
        }

        private void BtnLoadResults_Click(object sender, EventArgs e)
        {
            var path = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis", "results_wizard_optim.txt");
            if (!File.Exists(path))
            {
                _lblStatus.Text = "Results file not found. Run optimization first (MATLAB run_wizard_optimization.m or Python).";
                return;
            }
            _resultsGrid.Rows.Clear();
            var lines = File.ReadAllLines(path);
            for (int i = 1; i < lines.Length; i++)
            {
                var parts = lines[i].Split('\t');
                if (parts.Length >= 4)
                    _resultsGrid.Rows.Add(parts[0], parts[1], parts[2], parts[3]);
            }
            _lblStatus.Text = "Loaded " + (_resultsGrid.Rows.Count) + " result(s) from results_wizard_optim.txt.";
        }

        private static double[] ParseDoubles(string s, int count)
        {
            if (string.IsNullOrWhiteSpace(s)) return null;
            var parts = s.Split(new[] { ',', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < count) return null;
            var d = new double[count];
            for (int i = 0; i < count; i++)
                if (!double.TryParse(parts[i], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out d[i])) return null;
            return d;
        }

        private static void Normalize(double[] v)
        {
            double n = Math.Sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
            if (n > 1e-10) { v[0] /= n; v[1] /= n; v[2] /= n; }
        }
    }
}
