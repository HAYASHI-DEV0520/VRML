import sys
import numpy as np
from scipy.spatial import Delaunay

files = [
    "53394610_dsm_1m.dat",
    "53394611_dsm_1m.dat",
    "53394620_dsm_1m.dat",
    "53394621_dsm_1m.dat",
    "53394630_dsm_1m.dat",
    "53394631_dsm_1m.dat",
    "53394640_dsm_1m.dat",
    "53394641_dsm_1m.dat",
]


def read_dad():
    """グリッド作成に使うX座標と符号反転したY座標を読み込む."""
    coordinate_parts = []

    for filename in files:
        with open(filename) as f:
            coordinate_parts.append(
                np.loadtxt(f, usecols=(0, 1, 2), dtype=np.float32, ndmin=2)
            )

    points = np.concatenate(coordinate_parts, axis=0)
    points[:, 1] *= -1
    return points




#近い値で グループ化
def align_axis(values, eps):
    if not np.isfinite(values).all():
        raise ValueError("座標に有限でない値が含まれています")

    order = np.argsort(values)
    sorted_values = values[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_values) > eps) + 1]
    ends = np.r_[starts[1:], values.size]
    centers = np.add.reduceat(sorted_values, starts) / (ends - starts)

    indices = np.empty(values.size, dtype=np.int32)
    for index, (start, end) in enumerate(zip(starts, ends)):
        indices[order[start:end]] = index

    return indices, centers







def calc_curvs(points, grid):
    """曲率を計算しpointsのインデックス順にcurvsに曲率値を格納 必ず残す点(外周など)は-1を返す."""
    curvs = [-1] * len(points)  #初期値-1は 計算されずに-1だったらその点は残す
    dx = 1.0
    dy = 1.0 #格子間隔 1 (定数でいいのか?)ß

    for i in range(1, len(y_grid)-1):
        for k in range(1, len(x_grid)-1):
            # grid[i, k]からpointsのインデックスを取得し、その点の2列目(Z座標)で曲率計算
            # iはY方向, kはX方向
            if np.any(grid[i-1:i+2, k-1:k+2] < 0):
                continue
            Dxx = (points[grid[i, k+1], 2] - 2 * points[grid[i, k], 2] + points[grid[i, k-1], 2]) / dx**2

            Dyy = (points[grid[i+1, k], 2] - 2 * points[grid[i, k], 2] + points[grid[i-1, k], 2]) / dy**2

            Dxy = (points[grid[i+1, k+1], 2] - points[grid[i+1, k-1], 2] - points[grid[i-1, k+1], 2] + points[grid[i-1, k-1], 2]) / (4 * dx * dy)

            curv = np.sqrt(Dxx**2 + 2 * Dxy**2 + Dyy**2)

            curvs[grid[i, k]] = curv

    print("\n曲率最大", max(curvs))
    print("曲率最小", min(curvs))

    strs = '\n'.join(map(str,curvs))
    with open("curvs.txt", 'wt') as f:
        f.write(strs)
    return curvs
def reduce_points2(points, curvs, sikii):
    """曲率(ラプラシアンの絶対値):curvsが 閾値:sikii 以上の点と、格子の外周の点だけ残す."""
    reduced_points = []

    for i in range(len(points)):
        if curvs[i] == -1 or curvs[i] >= sikii:
            reduced_points.append(points[i])

    return reduced_points


def miss_point(points, grid):#ここを自分で作る＃二次元配列のgridを受け取り、欠損値を補完する関数を作る
    #欠損値(-9999.99)を補完する.
    
    L = []
    #欠損点を見つけたら、その点の周囲八つを見て小さい方から見て4番目の値を欠損点の値にする

    #すべての点で欠損点を探す
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if points[grid[i][j], 2] == -9999.99:
                #周囲八つの点を見て小さい方から見て4番目の値を欠損点の値にする
                neighbors = []
                for x in range(-1, 2):
                    for y in range(-1, 2):
                        if x == 0 and y == 0:#自分自身の点は除外する
                            continue
                        if 0 <= i + x < len(grid) and 0 <= j + y < len(points[grid[i + x], 2]):
                            if points[grid[i + x][j + y], 2] != -9999.99:
                                neighbors.append(points[grid[i + x][j + y], 2])
                neighbors.sort()
                points[grid[i][j], 2] = neighbors[(len(neighbors) - 1) // 2]#小さい方から見て4番目の値を欠損点の値にする
    

try:
    points = read_dad()
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)


print(len(points))


# 調整するパラメータ 同じグループにまとめる許容幅
EPS_X = 0.3
EPS_Y = 0.3

cols, x_grid = align_axis(points[:, 0], EPS_X)
rows, y_grid = align_axis(points[:, 1], EPS_Y)

#del points

print("X方向の列数:", len(x_grid))
print("Y方向の行数:", len(y_grid))

# 2次元配列を作成（-1は点が存在しない場所）
grid = np.full(
    (len(y_grid), len(x_grid)),
    -1,
    dtype=int
)

# 格子に元の点の番号を格納
grid[rows, cols] = np.arange(len(rows))

miss_point(points, grid)

before = len(points)

print("元の点数", before)
if (input("ENTERでtxtから読み込み")):
    curvs = calc_curvs(points, grid)
else:
    try:
        with open("curvs.txt", "rt") as f:
            curvs = [float(line) for line in f.read().splitlines()]
    except FileNotFoundError:
        curvs = calc_curvs(points, grid)

# 以下に閾値を
i = 1
reduced_points = reduce_points2(points, curvs, i)
after = len(reduced_points)

print(
    "sikii =", i,
    "点数:", after,
    "削減率:", 1 - after / before
    )
points_to_vrml= np.asarray(reduced_points)

"""
ここから追加 VRML化の処理

"""


def triangulate(points):
    """XY平面でドロネー三角形分割する."""
    xy_points = [[p[0], p[1]] for p in points]
    triangles = Delaunay(xy_points).simplices   #面を構成する３点インデックスの組がtrianglesに.
    # 三角形の頂点を反時計回りに統一
    for triangle in triangles:
        a = points[triangle[0]]
        b = points[triangle[1]]
        c = points[triangle[2]]

        cross = (
            (b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0])
        )

        if cross < 0:   #クロス積が負の時は時計回りなのでreverse
            triangle.reverse()

    return triangles


def write_vrml(path, points, triangles):
    """点群と三角形からVRMLファイルを出力する."""

    # VRMLの座標: x=X, y=Z(高さ), z=-Y
    vrml_points = np.column_stack([
        points[:, 0],
        points[:, 2],
        points[:, 1]
    ])

    with open(path, "w") as f:
        f.write("#VRML V2.0 utf8\n")

        f.write("Shape {\n")
        f.write(
            "  appearance Appearance { material Material { "
            "diffuseColor 1 1 1 ambientIntensity 0.25 "
            "emissiveColor 0.05 0.05 0.05 } }\n"
        )
        f.write("  geometry IndexedFaceSet {\n")
        f.write("    solid FALSE\n")
        f.write("    coord Coordinate {\n")
        f.write("      point [\n")

        for point in vrml_points:
            line = (
                str(point[0]) + " " +
                str(point[1]) + " " +
                str(point[2]) + ",\n"
            )
            f.write(line)
        f.write("      ]\n")
        f.write("    }\n")
        f.write("    coordIndex [\n")

        for triangle in triangles:
            f.write(
                str(triangle[0]) + "," +
                str(triangle[1]) + "," +
                str(triangle[2]) + ",-1,\n"
            )
        f.write("    ]\n")
        f.write("  }\n")
        f.write("}\n")


triangles = triangulate(points_to_vrml)

print("三角形数:", len(triangles))

write_vrml("sikii_1.wrl", points_to_vrml, triangles)

print("VRML出力: sikii_1.wrl")