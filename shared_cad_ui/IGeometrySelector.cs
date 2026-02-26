using System;

namespace KstAnalysisWizard
{
    /// <summary>
    /// CAD-agnostic interface for picking geometry (point, axis, plane) from the host CAD application.
    /// Each CAD add-in (Inventor, SolidWorks, etc.) implements this and passes it to the wizard forms.
    /// </summary>
    public interface IGeometrySelector
    {
        /// <summary>Prompt user to select a point; returns location [x,y,z] or null if cancelled.</summary>
        GeometryPoint SelectPoint(string prompt);

        /// <summary>Prompt user to select an axis (e.g. edge or cylinder); returns location + direction or null if cancelled.</summary>
        GeometryAxis SelectAxis(string prompt);

        /// <summary>Prompt user to select a plane (e.g. face); returns point on plane + normal or null if cancelled.</summary>
        GeometryPlane SelectPlane(string prompt);
    }

    /// <summary>3D point (location only).</summary>
    public class GeometryPoint
    {
        public double[] Location { get; private set; }
        public GeometryPoint(double[] location) { Location = location ?? new double[0]; }
    }

    /// <summary>Axis: point on axis + unit direction vector.</summary>
    public class GeometryAxis
    {
        public double[] Location { get; private set; }
        public double[] Direction { get; private set; }
        public GeometryAxis(double[] location, double[] direction)
        {
            Location = location ?? new double[0];
            Direction = direction ?? new double[0];
        }
    }

    /// <summary>Plane: point on plane + unit normal.</summary>
    public class GeometryPlane
    {
        public double[] Location { get; private set; }
        public double[] Normal { get; private set; }
        public GeometryPlane(double[] location, double[] normal)
        {
            Location = location ?? new double[0];
            Normal = normal ?? new double[0];
        }
    }
}
