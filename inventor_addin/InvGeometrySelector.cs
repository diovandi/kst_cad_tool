using System;
using System.Runtime.InteropServices;
using Inventor;

namespace KstAnalysisWizard
{
    /// <summary>
    /// Inventor implementation of IGeometrySelector. Uses Inventor's selection/pick APIs
    /// to let the user pick points, edges (axis), and faces (plane) from the model.
    /// </summary>
    public class InvGeometrySelector : IGeometrySelector
    {
        private readonly Application _invApp;

        public InvGeometrySelector(Application inventorApp)
        {
            _invApp = inventorApp ?? throw new ArgumentNullException("inventorApp");
        }

        public GeometryPoint SelectPoint(string prompt)
        {
            object picked = PickEntity(prompt, SelectionFilterEnum.kPartFaceFilter);
            if (picked == null) return null;

            try
            {
                if (picked is Face)
                {
                    var face = (Face)picked;
                    return PointFromFace(face);
                }
                if (picked is Edge)
                {
                    var edge = (Edge)picked;
                    return PointFromEdge(edge);
                }
                if (picked is Vertex)
                {
                    var vertex = (Vertex)picked;
                    return PointFromVertex(vertex);
                }
            }
            finally
            {
                if (picked != null) Marshal.ReleaseComObject(picked);
            }
            return null;
        }

        public GeometryAxis SelectAxis(string prompt)
        {
            object picked = PickEntity(prompt, SelectionFilterEnum.kPartEdgeFilter);
            if (picked == null)
                picked = PickEntity(prompt ?? "Select cylindrical face", SelectionFilterEnum.kPartCylinderFilter);
            if (picked == null) return null;

            try
            {
                if (picked is Edge)
                {
                    var edge = (Edge)picked;
                    return AxisFromEdge(edge);
                }
                if (picked is Face)
                {
                    var face = (Face)picked;
                    return AxisFromCylindricalFace(face);
                }
            }
            finally
            {
                if (picked != null) Marshal.ReleaseComObject(picked);
            }
            return null;
        }

        public GeometryPlane SelectPlane(string prompt)
        {
            object picked = PickEntity(prompt, SelectionFilterEnum.kPartPlanarFaceFilter);
            if (picked == null)
                picked = PickEntity(prompt ?? "Select face", SelectionFilterEnum.kPartFaceFilter);
            if (picked == null) return null;

            try
            {
                if (picked is Face)
                {
                    var face = (Face)picked;
                    return PlaneFromFace(face);
                }
            }
            finally
            {
                if (picked != null) Marshal.ReleaseComObject(picked);
            }
            return null;
        }

        private object PickEntity(string prompt, SelectionFilterEnum filter)
        {
            try
            {
                _invApp.UserInterfaceManager.StatusBarText = prompt ?? "Select entity";
                object picked = _invApp.CommandManager.Pick(filter, prompt ?? "Select entity");
                _invApp.UserInterfaceManager.StatusBarText = "";
                if (picked != null)
                    return picked;
            }
            catch (Exception)
            {
                _invApp.UserInterfaceManager.StatusBarText = "";
            }
            return null;
        }

        private static GeometryPoint PointFromFace(Face face)
        {
            try
            {
                SurfaceEvaluator eval = face.Evaluator;
                Point pt = eval.GetPointAtParam(0.5, 0.5);
                double[] point = new[] { pt.X, pt.Y, pt.Z };
                Marshal.ReleaseComObject(pt);
                Marshal.ReleaseComObject(eval);
                return new GeometryPoint(point);
            }
            catch
            {
                try
                {
                    SurfaceEvaluator eval = face.Evaluator;
                    double[] point = new double[3];
                    eval.GetPointAtParam(0.5, 0.5, point);
                    Marshal.ReleaseComObject(eval);
                    return new GeometryPoint(point);
                }
                catch { return null; }
            }
        }

        private static GeometryPoint PointFromEdge(Edge edge)
        {
            try
            {
                double[] point = new double[3];
                edge.GetPointAtParam(0.5, point);
                return new GeometryPoint(point);
            }
            catch { return null; }
        }

        private static GeometryPoint PointFromVertex(Vertex vertex)
        {
            try
            {
                Point point = vertex.Point;
                double[] loc = new[] { point.X, point.Y, point.Z };
                Marshal.ReleaseComObject(point);
                return new GeometryPoint(loc);
            }
            catch { return null; }
        }

        private static GeometryAxis AxisFromEdge(Edge edge)
        {
            try
            {
                double[] startPt = new double[3], endPt = new double[3];
                edge.GetPointAtParam(0.0, startPt);
                edge.GetPointAtParam(1.0, endPt);
                double[] loc = new[] { (startPt[0] + endPt[0]) / 2, (startPt[1] + endPt[1]) / 2, (startPt[2] + endPt[2]) / 2 };
                double dx = endPt[0] - startPt[0], dy = endPt[1] - startPt[1], dz = endPt[2] - startPt[2];
                double len = Math.Sqrt(dx * dx + dy * dy + dz * dz);
                if (len < 1e-10) return null;
                double[] dir = new[] { dx / len, dy / len, dz / len };
                return new GeometryAxis(loc, dir);
            }
            catch { return null; }
        }

        private static GeometryAxis AxisFromCylindricalFace(Face face)
        {
            try
            {
                SurfaceEvaluator eval = face.Evaluator;
                Point pt = eval.GetPointAtParam(0.5, 0.5);
                double[] origin = new[] { pt.X, pt.Y, pt.Z };
                Marshal.ReleaseComObject(pt);
                double[] axis = new double[3];
                eval.GetNormal(0.5, 0.5, axis);
                Marshal.ReleaseComObject(eval);
                double len = Math.Sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2]);
                if (len < 1e-10) return null;
                axis[0] /= len; axis[1] /= len; axis[2] /= len;
                return new GeometryAxis(origin, axis);
            }
            catch
            {
                try
                {
                    SurfaceEvaluator eval = face.Evaluator;
                    double[] origin = new double[3], axis = new double[3];
                    eval.GetPointAtParam(0.5, 0.5, origin);
                    eval.GetNormal(0.5, 0.5, axis);
                    Marshal.ReleaseComObject(eval);
                    double len = Math.Sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2]);
                    if (len < 1e-10) return null;
                    axis[0] /= len; axis[1] /= len; axis[2] /= len;
                    return new GeometryAxis(origin, axis);
                }
                catch { return null; }
            }
        }

        private static GeometryPlane PlaneFromFace(Face face)
        {
            try
            {
                SurfaceEvaluator eval = face.Evaluator;
                Point pt = eval.GetPointAtParam(0.5, 0.5);
                double[] point = new[] { pt.X, pt.Y, pt.Z };
                Marshal.ReleaseComObject(pt);
                double[] normal = new double[3];
                eval.GetNormal(0.5, 0.5, normal);
                Marshal.ReleaseComObject(eval);
                double len = Math.Sqrt(normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]);
                if (len < 1e-10) return null;
                normal[0] /= len; normal[1] /= len; normal[2] /= len;
                return new GeometryPlane(point, normal);
            }
            catch
            {
                try
                {
                    SurfaceEvaluator eval = face.Evaluator;
                    double[] point = new double[3], normal = new double[3];
                    eval.GetPointAtParam(0.5, 0.5, point);
                    eval.GetNormal(0.5, 0.5, normal);
                    Marshal.ReleaseComObject(eval);
                    double len = Math.Sqrt(normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]);
                    if (len < 1e-10) return null;
                    normal[0] /= len; normal[1] /= len; normal[2] /= len;
                    return new GeometryPlane(point, normal);
                }
                catch { return null; }
            }
        }
    }
}
