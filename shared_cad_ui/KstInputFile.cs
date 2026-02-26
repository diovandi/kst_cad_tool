using System.Collections.Generic;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Data structure for the KST analysis input file.
    /// </summary>
    internal class KstInputFile
    {
        public int version { get; set; } = 1;
        public List<double[]> point_contacts { get; set; } = new List<double[]>();
        public List<double[]> pins { get; set; } = new List<double[]>();
        public List<double[]> lines { get; set; } = new List<double[]>();
        public List<double[]> planes { get; set; } = new List<double[]>();
    }
}
