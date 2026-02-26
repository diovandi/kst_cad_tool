using System;
using System.Windows.Forms;

namespace KstSwAddIn
{
    /// <summary>
    /// Small modal form shown while user selects geometry in SolidWorks.
    /// User selects in the model, then clicks OK; we read the selection in the add-in.
    /// </summary>
    public class SelectPromptForm : Form
    {
        public bool Done { get; private set; }
        public bool Cancelled { get; private set; }

        public SelectPromptForm(string prompt)
        {
            Text = "KST — Select in model";
            Size = new System.Drawing.Size(320, 120);
            StartPosition = FormStartPosition.CenterParent;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            var lbl = new Label
            {
                Text = prompt ?? "Select geometry in the SolidWorks model, then click OK.",
                AutoSize = false,
                Dock = DockStyle.Top,
                Height = 44,
                Padding = new Padding(8),
                TextAlign = System.Drawing.ContentAlignment.MiddleCenter
            };
            var btnOk = new Button { Text = "OK", DialogResult = DialogResult.OK, Width = 80 };
            var btnCancel = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Width = 80 };
            btnOk.Click += (s, e) => { Done = true; Cancelled = false; Close(); };
            btnCancel.Click += (s, e) => { Done = true; Cancelled = true; Close(); };
            var panel = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 40, FlowDirection = FlowDirection.RightToLeft };
            panel.Controls.Add(btnCancel);
            panel.Controls.Add(btnOk);
            Controls.Add(panel);
            Controls.Add(lbl);
        }
    }
}
