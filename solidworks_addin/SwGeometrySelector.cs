using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using KstAnalysisWizard;

namespace KstSwAddIn
{
    /// <summary>
    /// SolidWorks implementation of IGeometrySelector.
    /// Uses a prompt form so the user can select in the model, then we read SelectionManager.
    /// </summary>
    public class SwGeometrySelector : IGeometrySelector
    {
        private readonly SldWorks _swApp;

        public SwGeometrySelector(SldWorks swApp)
        {
            _swApp = swApp ?? throw new ArgumentNullException("swApp");
        }

        public GeometryPoint SelectPoint(string prompt)
        {
            var form = new SelectPromptForm(prompt ?? "Select a face, edge, or vertex for constraint location. Then click OK.");
            form.ShowDialog();
            if (form.Cancelled) return null;
            return GetPointFromSelection();
        }

        public GeometryAxis SelectAxis(string prompt)
        {
            var form = new SelectPromptForm(prompt ?? "Select an edge or cylindrical face for constraint axis. Then click OK.");
            form.ShowDialog();
            if (form.Cancelled) return null;
            return GetAxisFromSelection();
        }

        public GeometryPlane SelectPlane(string prompt)
        {
            var form = new SelectPromptForm(prompt ?? "Select a planar face for constraint normal. Then click OK.");
            form.ShowDialog();
            if (form.Cancelled) return null;
            return GetPlaneFromSelection();
        }

        private ModelDoc2 GetActiveDoc()
        {
            return _swApp?.ActiveDoc as ModelDoc2;
        }

        private GeometryPoint GetPointFromSelection()
        {
            var doc = GetActiveDoc();
            if (doc == null) return null;
            var selMgr = doc.SelectionManager;
            if (selMgr == null || selMgr.GetSelectedObjectCount2(-1) < 1) return null;
            try
            {
                var obj = selMgr.GetSelectedObject6(1, -1, null);
                if (obj == null) return null;
                double[] pt = GetPointFromEntity(obj);
                if (pt != null) return new GeometryPoint(pt);
            }
            finally
            {
                if (selMgr != null) Marshal.ReleaseComObject(selMgr);
            }
            return null;
        }

        private static double[] GetPointFromEntity(object entity)
        {
            if (entity is IFace2 face)
            {
                try
                {
                    var surf = face.GetSurface() as ISurface;
                    if (surf != null)
                    {
                        double uMin = 0, uMax = 0, vMin = 0, vMax = 0;
                        face.GetUVBounds(ref uMin, ref uMax, ref vMin, ref vMax);
                        double u = (uMin + uMax) / 2, v = (vMin + vMax) / 2;
                        double[] evalData = (double[])surf.Evaluate(u, v, 0, 0, 0, 0);
                        Marshal.ReleaseComObject(surf);
                        if (evalData != null && evalData.Length >= 3)
                            return new[] { evalData[0], evalData[1], evalData[2] };
                    }
                }
                catch { }
                return null;
            }
            if (entity is IEdge edge)
            {
                try
                {
                    var curve = edge.GetCurve() as ICurve;
                    if (curve != null)
                    {
                        double start = 0, end = 1;
                        curve.GetEndParams(ref start, ref end);
                        double t = (start + end) / 2;
                        double[] pt = new double[3];
                        curve.Evaluate2(t, 0, pt);
                        Marshal.ReleaseComObject(curve);
                        return pt;
                    }
                }
                catch { }
                return null;
            }
            if (entity is IVertex vertex)
            {
                try
                {
                    var pt = vertex.GetPoint();
                    if (pt != null)
                    {
                        double[] xyz = new[] { pt.X, pt.Y, pt.Z };
                        Marshal.ReleaseComObject(pt);
                        return xyz;
                    }
                }
                catch { }
                return null;
            }
            return null;
        }

        private GeometryAxis GetAxisFromSelection()
        {
            var doc = GetActiveDoc();
            if (doc == null) return null;
            var selMgr = doc.SelectionManager;
            if (selMgr == null || selMgr.GetSelectedObjectCount2(-1) < 1) return null;
            try
            {
                var obj = selMgr.GetSelectedObject6(1, -1, null);
                if (obj == null) return null;
                if (obj is IEdge edge)
                {
                    var axis = AxisFromEdge(edge);
                    if (axis != null) return axis;
                }
                if (obj is IFace2 face)
                {
                    var axis = AxisFromCylindricalFace(face);
                    if (axis != null) return axis;
                }
            }
            finally
            {
                if (selMgr != null) Marshal.ReleaseComObject(selMgr);
            }
            return null;
        }

        private static GeometryAxis AxisFromEdge(IEdge edge)
        {
            try
            {
                var curve = edge.GetCurve() as ICurve;
                if (curve == null) return null;
                double start = 0, end = 1;
                curve.GetEndParams(ref start, ref end);
                double[] pt1 = new double[3], pt2 = new double[3];
                curve.Evaluate2(start, 0, pt1);
                curve.Evaluate2(end, 0, pt2);
                Marshal.ReleaseComObject(curve);
                double[] loc = new[] { (pt1[0] + pt2[0]) / 2, (pt1[1] + pt2[1]) / 2, (pt1[2] + pt2[2]) / 2 };
                double dx = pt2[0] - pt1[0], dy = pt2[1] - pt1[1], dz = pt2[2] - pt1[2];
                double len = Math.Sqrt(dx * dx + dy * dy + dz * dz);
                if (len < 1e-10) return null;
                double[] dir = new[] { dx / len, dy / len, dz / len };
                return new GeometryAxis(loc, dir);
            }
            catch { return null; }
        }

        private static GeometryAxis AxisFromCylindricalFace(IFace2 face)
        {
            try
            {
                var surf = face.GetSurface() as ISurface;
                if (surf == null) return null;
                double uMid = 0.5, vMid = 0.5;
                double[] pt = new double[3], normal = new double[3];
                surf.Evaluate2(uMid, vMid, 0, pt, normal);
                Marshal.ReleaseComObject(surf);
                double len = Math.Sqrt(normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]);
                if (len < 1e-10) return null;
                normal[0] /= len; normal[1] /= len; normal[2] /= len;
                return new GeometryAxis(pt, normal);
            }
            catch { return null; }
        }

        private GeometryPlane GetPlaneFromSelection()
        {
            var doc = GetActiveDoc();
            if (doc == null) return null;
            var selMgr = doc.SelectionManager;
            if (selMgr == null || selMgr.GetSelectedObjectCount2(-1) < 1) return null;
            try
            {
                var obj = selMgr.GetSelectedObject6(1, -1, null);
                if (obj == null) return null;
                if (obj is IFace2 face)
                {
                    try
                    {
                        double[] pt = null, n = null;
                        var surf = face.GetSurface() as ISurface;
                        if (surf != null)
                        {
                            double uMin = 0, uMax = 0, vMin = 0, vMax = 0;
                            face.GetUVBounds(ref uMin, ref uMax, ref vMin, ref vMax);
                            double u = (uMin + uMax) / 2, v = (vMin + vMax) / 2;
                            double[] evalData = (double[])surf.Evaluate(u, v, 0, 0, 0, 0);
                            if (evalData != null && evalData.Length >= 6)
                            {
                                pt = new[] { evalData[0], evalData[1], evalData[2] };
                                n = new[] { evalData[3], evalData[4], evalData[5] };
                                double len = Math.Sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
                                if (len > 1e-10) { n[0] /= len; n[1] /= len; n[2] /= len; }
                            }
                            Marshal.ReleaseComObject(surf);
                        }
                        if (pt != null && n != null)
                            return new GeometryPlane(pt, n);
                    }
                    catch { }
                }
            }
            finally
            {
                if (selMgr != null) Marshal.ReleaseComObject(selMgr);
            }
            return null;
        }
    }
}
