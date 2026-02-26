using System;
using System.IO;

namespace KstAnalysisWizard
{
    public static class Logger
    {
        private static string LogPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "KstAnalysis", "error_log.txt");

        public static void LogError(Exception ex)
        {
            try
            {
                var dir = Path.GetDirectoryName(LogPath);
                if (!Directory.Exists(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                string message = string.Format("[{0}] Error: {1}\nStack Trace: {2}\n\n",
                    DateTime.Now, ex.Message, ex.StackTrace);

                File.AppendAllText(LogPath, message);
            }
            catch
            {
                // If logging fails, we suppress the exception to avoid crashing the application during error handling.
            }
        }
    }
}
