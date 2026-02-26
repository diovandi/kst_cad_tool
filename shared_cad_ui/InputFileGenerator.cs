using System;
using System.Collections.Generic;
using System.IO;
using System.Windows.Forms;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Generates KST analysis input file from wizard constraint table.
    /// Output format: JSON (generic format for analysis script).
    /// </summary>
    public static class InputFileGenerator
    {
        /// <summary>
        /// Write input file from current grid data. Returns path of written file.
        /// </summary>
        public static string WriteInputFile(DataGridView grid)
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, "wizard_input.json");

            var cpList = new List<double[]>();
            for (int i = 0; i < grid.Rows.Count; i++)
            {
                var type = (grid.Rows[i].Cells[0].Value ?? "Point").ToString();
                var locStr = (grid.Rows[i].Cells[1].Value ?? "").ToString();
                var orientStr = (grid.Rows[i].Cells[2].Value ?? "").ToString();
                if (string.IsNullOrWhiteSpace(locStr) || string.IsNullOrWhiteSpace(orientStr))
                    continue;
                if (type.Equals("Point", StringComparison.OrdinalIgnoreCase))
                {
                    var loc = ParseDoubles(locStr, 3);
                    var orient = ParseDoubles(orientStr, 3);
                    if (loc != null && orient != null)
                        cpList.Add(new[] { loc[0], loc[1], loc[2], orient[0], orient[1], orient[2] });
                }
            }

            var sb = new System.Text.StringBuilder();
            sb.Append("{\"version\":1,\"point_contacts\":[");
            for (int i = 0; i < cpList.Count; i++)
            {
                if (i > 0) sb.Append(",");
                sb.Append("[");
                for (int j = 0; j < cpList[i].Length; j++) { if (j > 0) sb.Append(","); sb.Append(cpList[i][j].ToString("G", System.Globalization.CultureInfo.InvariantCulture)); }
                sb.Append("]");
            }
            sb.Append("],\"pins\":[],\"lines\":[],\"planes\":[]}");
            File.WriteAllText(path, sb.ToString());

            return path;
        }

        private static double[] ParseDoubles(string s, int expectedCount)
        {
            var parts = s.Split(new[] { ',', ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < expectedCount) return null;
            var d = new double[expectedCount];
            for (int i = 0; i < expectedCount; i++)
                if (!double.TryParse(parts[i], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out d[i])) return null;
            return d;
        }
    }
}
