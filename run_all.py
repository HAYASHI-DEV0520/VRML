
import sys
import numpy as np
from scipy.spatial import Delaunay, QhullError


# =========================
# 設定
# =========================

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

EPS_X = 0.3
EPS_Y = 0.3

# 地面判定
RATE = 0.3
BORDER = 0.7

# 平滑化
SMOOTH_BORDER = 0.7
SMOOTH_ROUNDS = 3

# 曲率の閾値
THRESHOLD = 1.0


# =========================
# DSM読み込み
# =========================

def read_dad():
    coordinate_parts = []

    for filename in files:
        with open(filename) as f:
            data = np.loadtxt(
                f,
                usecols=(0, 1, 2),
                dtype=np.float32,
                ndmin=2
            )
            coordinate_parts.append(data)

    points = np.concatenate(coordinate_parts, axis=0)

    # Y座標の符号を反転
    points[:, 1] *= -1

    # NoDataと有限でない値を除外
    valid = np.isfinite(points).all(axis=1)
    valid &= points[:, 2] > -9999.0

    return points[valid]


try:
    points = read_dad()
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)

print("読み込んだ点数:", len(points))


# =========================
# グリッド作成
# =========================

def align_axis(values, eps):
    if not np.isfinite(values).all():
        raise ValueError("座標に有限でない値が含まれています")

    order = np.argsort(values)
    sorted_values = values[order]

    starts = np.r_[
        0,
        np.flatnonzero(np.diff(sorted_values) > eps) + 1
    ]

    ends = np.r_[starts[1:], values.size]

    centers = (
        np.add.reduceat(sorted_values, starts)
        / (ends - starts)
    )

    indices = np.empty(values.size, dtype=np.int32)

    for index, (start, end) in enumerate(zip(starts, ends)):
        indices[order[start:end]] = index

    return indices, centers


cols, x_grid = align_axis(points[:, 0], EPS_X)
rows, y_grid = align_axis(points[:, 1], EPS_Y)

grid = np.full(
    (len(y_grid), len(x_grid)),
    -1,
    dtype=int
)

grid[rows, cols] = np.arange(len(points))

print("グリッドの大きさ:", grid.shape)

with open("grid.dat", "w", encoding="utf-8") as f:
    for row in grid:
        f.write(" ".join(map(str, row)) + "\n")


# =========================
# 地面・建物の分類
# =========================

def zimen(grid, points, rate=0.3, border=0.7):
    grid = grid.copy()

    valid = grid >= 0
    indices = grid[valid]

    # 高さの低い順に並べる
    order = np.argsort(points[indices, 2])

    n = len(indices)
    seed_count = int(n * rate)

    seeds = indices[order[:seed_count]]

    ground = set(seeds)

    # 点番号からグリッド上の位置を取得
    cells = {
        grid[i, j]: (i, j)
        for i, j in np.argwhere(valid)
    }

    stack = list(seeds)

    while stack:
        current = stack.pop()

        i, j = cells[current]

        neighbors = [
            (i - 1, j),
            (i + 1, j),
            (i, j - 1),
            (i, j + 1)
        ]

        for ni, nj in neighbors:

            if not (
                0 <= ni < grid.shape[0]
                and 0 <= nj < grid.shape[1]
            ):
                continue

            neighbor = grid[ni, nj]

            if neighbor == -1:
                continue

            dz = (
                points[neighbor, 2]
                - points[current, 2]
            )

            if dz <= border and neighbor not in ground:
                ground.add(neighbor)
                stack.append(neighbor)

    return np.array(list(ground), dtype=int)


ground_indices = zimen(
    grid,
    points,
    rate=RATE,
    border=BORDER
)

# 地面と建物のマスク
ground_mask = np.zeros(len(points), dtype=bool)
ground_mask[ground_indices] = True

building_mask = ~ground_mask

ground_points = points[ground_mask].copy()
building_points = points[building_mask].copy()

print("地面の点数:", len(ground_points))
print("建物の点数:", len(building_points))


# =========================
# 分類後のグリッド作成
# =========================

def make_sub_grid(mask, rows, cols, shape):
    sub_grid = np.full(shape, -1, dtype=int)

    sub_grid[rows[mask], cols[mask]] = np.arange(
        np.count_nonzero(mask)
    )

    return sub_grid


ground_grid = make_sub_grid(
    ground_mask, rows, cols, grid.shape
)

building_grid = make_sub_grid(
    building_mask, rows, cols, grid.shape
)

# =========================
# 地面の平滑化
# =========================

def smooth_ground(points, ground_grid, border, rounds):

    smoothed_points = points.copy()

    for l in range(rounds):

        # 今回のラウンド開始時点の座標を保存
        old_points = smoothed_points.copy()

        # 今回のラウンドの更新結果を保存
        new_points = old_points.copy()

        for i in range(1, ground_grid.shape[0] - 1):
            for j in range(1, ground_grid.shape[1] - 1):

                center = ground_grid[i, j]

                if center == -1:
                    continue

                center_z = old_points[center, 2]

                # 上下左右の点番号
                neighbors = [
                    ground_grid[i-1, j],
                    ground_grid[i+1, j],
                    ground_grid[i, j-1],
                    ground_grid[i, j+1]
                ]

                neighbor_z = []

                for index in neighbors:

                    if index == -1:
                        continue

                    z = old_points[index, 2]

                    # 高さの差が閾値以下なら採用
                    if abs(z - center_z) <= border:
                        neighbor_z.append(z)

                # 条件を満たす隣接点がある場合
                if len(neighbor_z) > 0:

                    new_points[center, 2] = np.mean(neighbor_z)

        # 1ラウンド分の更新をまとめて反映
        smoothed_points = new_points

        print(f"平滑化ラウンド {l + 1}/{rounds} 完了")

    return smoothed_points


# 地面だけ平滑化
ground_points = smooth_ground(
    ground_points,
    ground_grid,
    border=SMOOTH_BORDER,
    rounds=SMOOTH_ROUNDS
)


# =========================
# 曲率計算
# =========================

def calc_curvs(points, grid, x_grid, y_grid):

    # -1は曲率を計算できない点
    curvs = np.full(len(points), -1.0)

    dx = 1.0
    dy = 1.0

    for i in range(1, len(y_grid) - 1):
        for k in range(1, len(x_grid) - 1):

            # 周囲8マスと中央に点があるか確認
            neighbors = [
                grid[i, k],
                grid[i, k+1],
                grid[i, k-1],
                grid[i+1, k],
                grid[i-1, k],
                grid[i+1, k+1],
                grid[i+1, k-1],
                grid[i-1, k+1],
                grid[i-1, k-1]
            ]

            if any(index == -1 for index in neighbors):
                continue

            center = grid[i, k]

            Dxx = (
                points[grid[i, k+1], 2]
                - 2 * points[center, 2]
                + points[grid[i, k-1], 2]
            ) / dx**2

            Dyy = (
                points[grid[i+1, k], 2]
                - 2 * points[center, 2]
                + points[grid[i-1, k], 2]
            ) / dy**2

            Dxy = (
                points[grid[i+1, k+1], 2]
                - points[grid[i+1, k-1], 2]
                - points[grid[i-1, k+1], 2]
                + points[grid[i-1, k-1], 2]
            ) / (4 * dx * dy)

            curv = np.sqrt(
                Dxx**2 + 2 * Dxy**2 + Dyy**2
            )

            curvs[center] = curv

    calculated = curvs[curvs >= 0]

    if len(calculated) > 0:
        print("曲率最大:", calculated.max())
        print("曲率最小:", calculated.min())
    else:
        print("曲率を計算できる点がありません")

    return curvs


# 地面と建物で別々に曲率を計算
ground_curvs = calc_curvs(
    ground_points,
    ground_grid,
    x_grid,
    y_grid
)

building_curvs = calc_curvs(
    building_points,
    building_grid,
    x_grid,
    y_grid
)


# =========================
# 点削減
# =========================

def reduce_points(points, curvs, threshold):

    keep = (curvs == -1) | (curvs >= threshold)

    return points[keep]


reduced_ground = reduce_points(
    ground_points,
    ground_curvs,
    THRESHOLD
)

reduced_building = reduce_points(
    building_points,
    building_curvs,
    THRESHOLD
)

print("削減後の地面:", len(reduced_ground))
print("削減後の建物:", len(reduced_building))


# =========================
# ドロネー三角形分割
# =========================

def triangulate(points):

    if len(points) < 3:
        return np.empty((0, 3), dtype=int)

    try:
        triangles = Delaunay(
            points[:, :2]
        ).simplices.copy()

    except QhullError:
        print("三角形分割できませんでした")
        return np.empty((0, 3), dtype=int)

    # 三角形の向きを統一
    for triangle in triangles:

        a = points[triangle[0]]
        b = points[triangle[1]]
        c = points[triangle[2]]

        cross = (
            (b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0])
        )

        if cross < 0:
            triangle[[1, 2]] = triangle[[2, 1]]

    return triangles


ground_triangles = triangulate(reduced_ground)
building_triangles = triangulate(reduced_building)

print("地面の三角形数:", len(ground_triangles))
print("建物の三角形数:", len(building_triangles))


# =========================
# VRML出力
# =========================

def write_shape(f, points, triangles, color):

    if len(points) == 0 or len(triangles) == 0:
        return

    f.write("Shape {\n")

    f.write("  appearance Appearance {\n")
    f.write("    material Material {\n")
    f.write(
        f"      diffuseColor {color[0]} {color[1]} {color[2]}\n"
    )
    f.write("    }\n")
    f.write("  }\n")

    f.write("  geometry IndexedFaceSet {\n")
    f.write("    solid FALSE\n")

    f.write("    coord Coordinate {\n")
    f.write("      point [\n")

    for point in points:
        # VRMLの座標順を X, Z, Y にする
        f.write(
            f"        {point[0]:.3f} "
            f"{point[2]:.3f} "
            f"{point[1]:.3f},\n"
        )

    f.write("      ]\n")
    f.write("    }\n")

    f.write("    coordIndex [\n")

    for triangle in triangles:
        f.write(
            f"      {triangle[0]}, "
            f"{triangle[1]}, "
            f"{triangle[2]}, -1,\n"
        )

    f.write("    ]\n")
    f.write("  }\n")
    f.write("}\n")


def write_vrml(
    path,
    ground_points,
    ground_triangles,
    building_points,
    building_triangles
):

    with open(path, "w", encoding="utf-8") as f:

        f.write("#VRML V2.0 utf8\n\n")

        # 地面：緑
        write_shape(
            f,
            ground_points,
            ground_triangles,
            (0.3, 0.7, 0.3)
        )

        # 建物：赤
        write_shape(
            f,
            building_points,
            building_triangles,
            (0.8, 0.2, 0.2)
        )


write_vrml(
    "terrain.wrl",
    reduced_ground,
    ground_triangles,
    reduced_building,
    building_triangles
)

print("VRML出力完了: terrain.wrl")
