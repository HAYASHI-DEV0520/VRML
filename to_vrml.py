"""DSMの点群をドロネー三角形分割し、IndexedFaceSetのVRMLファイルにする.

使い方: python to_vrml.py 出力.wrl 入力1.dat [入力2.dat ...] [--threshold 曲率の閾値m]
"""
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.spatial import Delaunay

NODATA = -9999.0
CURVATURE_THRESHOLD = 0.5  # 調整するパラメータ(m)。大きいほど点が減る


def read_points(filenames):
    parts = [np.loadtxt(f, usecols=(0, 1, 2), dtype=np.float64, ndmin=2) for f in filenames]
    return np.concatenate(parts, axis=0)


def fill_missing(points):
    """1m格子とみなし、欠損(-9999.99)と抜けた格子点をラプラス方程式で補間して全点を返す."""
    x0, y0 = points[:, 0].min(), points[:, 1].min()
    xi = np.rint(points[:, 0] - x0).astype(int)
    yi = np.rint(points[:, 1] - y0).astype(int)
    h, w = yi.max() + 1, xi.max() + 1
    z = np.full((h, w), np.nan)
    valid = points[:, 2] > NODATA
    z[yi[valid], xi[valid]] = points[valid, 2]

    unknown = np.isnan(z)
    n_unknown = int(unknown.sum())
    if n_unknown:
        index = np.full((h, w), -1)
        index[unknown] = np.arange(n_unknown)
        rows, cols, vals = [], [], []
        rhs = np.zeros(n_unknown)
        diag = np.zeros(n_unknown)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ys, xs = np.nonzero(unknown)
            ny, nx = ys + dy, xs + dx
            inside = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            me = index[ys[inside], xs[inside]]
            ny, nx = ny[inside], nx[inside]
            diag[me] += 1
            known = ~unknown[ny, nx]
            np.add.at(rhs, me[known], z[ny[known], nx[known]])
            rows.append(me[~known]); cols.append(index[ny[~known], nx[~known]])
            vals.append(np.full((~known).sum(), -1.0))
        rows.append(np.arange(n_unknown)); cols.append(np.arange(n_unknown)); vals.append(diag)
        a = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                       shape=(n_unknown, n_unknown)).tocsc()
        z[unknown] = spsolve(a, rhs)

    gy, gx = np.mgrid[0:h, 0:w]
    return np.column_stack([gx.ravel() + x0, gy.ravel() + y0, z.ravel()]), n_unknown, (h, w)


def reduce_points(points, shape, threshold):
    """曲率(ラプラシアンの絶対値)が threshold 以上の点と、格子の外周の点だけ残す."""
    h, w = shape
    z = points[:, 2].reshape(h, w)
    p = np.pad(z, 1, mode="edge")
    curvature = np.abs(p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] - 4 * z)
    keep = curvature >= threshold
    keep[0, :] = keep[-1, :] = keep[:, 0] = keep[:, -1] = True
    return points[keep.ravel()]


def triangulate(points):
    """XY平面でドロネー三角形分割し、上から見て反時計回りの頂点番号を返す."""
    triangles = Delaunay(points[:, :2]).simplices
    a, b, c = (points[triangles[:, i], :2] for i in range(3))
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    clockwise = cross < 0
    triangles[clockwise] = triangles[clockwise][:, ::-1]
    return triangles


def write_vrml(path, points, triangles):
    # VRMLの座標: x=X, y=Z(高さ), z=-Y
    vrml_points = np.column_stack([points[:, 0], points[:, 2], -points[:, 1]])
    with open(path, "w") as f:
        f.write("#VRML V2.0 utf8\n")
        cx, cz = vrml_points[:, 0].mean(), vrml_points[:, 2].mean()
        span = max(np.ptp(vrml_points[:, 0]), np.ptp(vrml_points[:, 2]))
        f.write("NavigationInfo { type [\"EXAMINE\", \"ANY\"] headlight TRUE visibilityLimit 0 }\n")
        f.write(f"Viewpoint {{ position {cx:.2f} {span * 1.5:.2f} {cz:.2f} orientation 1 0 0 -1.5708 }}\n")
        f.write("DirectionalLight { direction -0.4 -1 -0.3 color 1 0.97 0.9 intensity 0.9 ambientIntensity 0.35 }\n")
        f.write("Shape {\n  appearance Appearance { material Material { diffuseColor 1 1 1 ambientIntensity 0.25 emissiveColor 0.05 0.05 0.05 } }\n  geometry IndexedFaceSet {\n    solid FALSE\n")
        f.write("    coord Coordinate {\n      point [\n")
        np.savetxt(f, vrml_points, fmt="%.2f", delimiter=" ", newline=",\n", header="", comments="")
        f.write("      ]\n    }\n    coordIndex [\n")
        np.savetxt(f, np.column_stack([triangles, np.full(len(triangles), -1)]),
                   fmt="%d", delimiter=",", newline=",\n")
        f.write("    ]\n  }\n}\n")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if "--threshold" in sys.argv:
        i = sys.argv.index("--threshold")
        CURVATURE_THRESHOLD = float(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    pts, n_filled, shape = fill_missing(read_points(sys.argv[2:]))
    print("補間した点:", n_filled)
    full = pts
    pts = reduce_points(pts, shape, CURVATURE_THRESHOLD)
    print("削減後の点:", len(pts), f"({len(pts) / len(full):.1%})")
    tri = triangulate(pts)
    print("点:", len(pts), "三角形:", len(tri))
    from scipy.interpolate import LinearNDInterpolator
    err = np.abs(LinearNDInterpolator(Delaunay(pts[:, :2]), pts[:, 2])(full[:, :2]) - full[:, 2])
    print(f"元データとの高さ誤差: 平均 {np.nanmean(err):.3f}m 最大 {np.nanmax(err):.2f}m")
    write_vrml(sys.argv[1], pts, tri)
