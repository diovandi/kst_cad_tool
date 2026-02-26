using System;
using System.IO;
using System.Windows.Forms;
using System.Web.Script.Serialization;

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

            var inputData = new KstInputFile();
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
                        inputData.point_contacts.Add(new[] { loc[0], loc[1], loc[2], orient[0], orient[1], orient[2] });
                }
            }

            var serializer = new JavaScriptSerializer();
            var json = serializer.Serialize(inputData);
            File.WriteAllText(path, json);

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
