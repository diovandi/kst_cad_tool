using System;
using System.IO;

namespace KstAnalysisWizard
{
    public static class Logger
    {
        public static string LogPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis", "error_log.txt");

        public static bool LogError(Exception ex)
        {
            try
            {
                var dir = Path.GetDirectoryName(LogPath);
                if (!Directory.Exists(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                string message = string.Format("[{0}] Exception:{1}{1}{2}{1}{1}",
                    DateTime.Now,
                    Environment.NewLine,
                    ex.ToString());

                File.AppendAllText(LogPath, message);
                return true;
            }
            catch
            {
                return false;
            }
        }
    }
}
