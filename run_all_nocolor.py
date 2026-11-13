
import os
import time
import numpy as np
from scipy.spatial import Delaunay


# ==============================
# 設定
# ==============================

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

NODATA = -9999.99

EPS_X = 0.3
EPS_Y = 0.3

# 地面判定の設定
GROUND_RATE = 0.3
GROUND_BORDER = 0.7


# ==============================
# 点群データの読み込み
# ==============================

def read_dad(filename):
    """DSMファイルを読み込む."""

    data = np.loadtxt(filename, dtype=np.float32)

    data[:, 1] *= -1

    valid = (
        (data[:, 2] != NODATA)
        & np.isfinite(data).all(axis=1)
    )

    return data[valid]


# ==============================
# 座標軸の整列
# ==============================

def align_axis(values, eps):
    """近い座標値をまとめて格子座標を作成する."""

    order = np.argsort(values)
    sorted_values = values[order]

    group_start = np.r_[
        0,
        np.where(np.diff(sorted_values) > eps)[0] + 1
    ]

    group_end = np.r_[group_start[1:], len(values)]

    centers = np.add.reduceat(
        sorted_values,
        group_start
    ) / (group_end - group_start)

    group_ids = np.repeat(
        np.arange(len(group_start)),
        group_end - group_start
    )

    indices = np.empty(len(values), dtype=np.int32)
    indices[order] = group_ids

    return centers, indices


# ==============================
# 地面判定
# ==============================

def judge_ground(grid, points, rate=0.3, border=0.7):
    """下位rateの点をシードにして、上下左右に地面判定を広げる."""

    valid = grid >= 0

    # 有効な格子セルと点群のインデックス
    flat_grid = grid.ravel()
    valid_cells = np.flatnonzero(flat_grid >= 0)
    valid_indices = flat_grid[valid_cells]

    # 地面判定用の配列
    ground_mask = np.zeros(len(points), dtype=bool)

    # 下位rateの点をシードにする
    seed_count = int(len(valid_indices) * rate)

    if seed_count == 0:
        return ground_mask

    z_values = points[valid_indices, 2]

    order = np.argpartition(
        z_values,
        seed_count - 1
    )[:seed_count]

    seeds = valid_indices[order]

    ground_mask[seeds] = True

    # 点群のインデックスから格子セルを取得できるようにする
    point_to_cell = np.full(
        len(points),
        -1,
        dtype=np.int32
    )

    point_to_cell[valid_indices] = valid_cells

    # シードの格子セルをスタックに入れる
    stack = point_to_cell[seeds].tolist()

    rows, cols = grid.shape

    print("地面判定を広げています...")

    while stack:

        current_cell = stack.pop()

        current_index = flat_grid[current_cell]

        current_z = points[current_index, 2]

        row = current_cell // cols
        col = current_cell % cols

        # 上下左右の近傍セル
        if row > 0:
            neighbors = (
                current_cell - cols,
                current_cell + cols,
                current_cell - 1 if col > 0 else -1,
                current_cell + 1 if col < cols - 1 else -1
            )
        else:
            neighbors = (
                -1,
                current_cell + cols,
                current_cell - 1 if col > 0 else -1,
                current_cell + 1 if col < cols - 1 else -1
            )

        for neighbor_cell in neighbors:

            if neighbor_cell == -1:
                continue

            neighbor_index = flat_grid[neighbor_cell]

            if neighbor_index == -1:
                continue

            if ground_mask[neighbor_index]:
                continue

            neighbor_z = points[neighbor_index, 2]

            # 上りはborder以下、下りは制限なし
            dz = neighbor_z - current_z

            if dz <= border:

                ground_mask[neighbor_index] = True
                stack.append(neighbor_cell)

    return ground_mask


# ==============================
# 曲率計算
# ==============================

def calc_curvs(points):
    """格子を利用して各点の曲率を計算する."""

    curvs = np.full(len(points), -1.0)

    dx = 1.0
    dy = 1.0

    valid = grid >= 0

    z_grid = np.full(grid.shape, np.nan)
    z_grid[valid] = points[grid[valid], 2]

    valid_window = (
        valid[1:-1, 1:-1]
        & valid[1:-1, :-2]
        & valid[1:-1, 2:]
        & valid[:-2, 1:-1]
        & valid[2:, 1:-1]
        & valid[:-2, :-2]
        & valid[:-2, 2:]
        & valid[2:, :-2]
        & valid[2:, 2:]
    )

    Dxx = (
        z_grid[1:-1, 2:]
        - 2 * z_grid[1:-1, 1:-1]
        + z_grid[1:-1, :-2]
    ) / dx**2

    Dyy = (
        z_grid[2:, 1:-1]
        - 2 * z_grid[1:-1, 1:-1]
        + z_grid[:-2, 1:-1]
    ) / dy**2

    Dxy = (
        z_grid[2:, 2:]
        - z_grid[2:, :-2]
        - z_grid[:-2, 2:]
        + z_grid[:-2, :-2]
    ) / (4 * dx * dy)

    curvature = np.sqrt(
        Dxx**2 + 2 * Dxy**2 + Dyy**2
    )

    center_indices = grid[1:-1, 1:-1][valid_window]

    curvs[center_indices] = curvature[valid_window]

    return curvs


# ==============================
# 点群削減
# ==============================

def reduce_points2(points, curvs, sikii):
    """曲率が閾値以上の点と、曲率未計算の点を残す."""

    keep = (curvs == -1) | (curvs >= sikii)

    return points[keep]


# ==============================
# VRML出力
# ==============================

def write_vrml(path, points, triangles, ground_mask):
    """地面と非地面を二色に分けてVRMLを出力する."""

    vrml_points = np.column_stack([
        points[:, 0],
        points[:, 2],
        points[:, 1]
    ])

    with open(path, "w") as f:

        f.write("#VRML V2.0 utf8\n")

        f.write("Shape {\n")

        f.write(
            "  appearance Appearance {\n"
            "    material Material {\n"
            "      diffuseColor 1 1 1\n"
            "      ambientIntensity 0.25\n"
            "    }\n"
            "  }\n"
        )

        f.write("  geometry IndexedFaceSet {\n")
        f.write("    solid FALSE\n")

        # 座標
        f.write("    coord Coordinate {\n")
        f.write("      point [\n")

        for point in vrml_points:
            f.write(
                f"        {point[0]} "
                f"{point[1]} "
                f"{point[2]},\n"
            )

        f.write("      ]\n")
        f.write("    }\n")

        # 頂点ごとの色
        f.write("    colorPerVertex TRUE\n")
        f.write("    color Color {\n")
        f.write("      color [\n")

        for is_ground in ground_mask:

            if is_ground:
                # 地面：緑
                color = (0.1, 0.8, 0.1)
            else:
                # 非地面：赤
                color = (0.9, 0.1, 0.1)

            f.write(
                f"        {color[0]} "
                f"{color[1]} "
                f"{color[2]},\n"
            )

        f.write("      ]\n")
        f.write("    }\n")

        # 三角形の接続情報
        f.write("    coordIndex [\n")

        for triangle in triangles:
            f.write(
                f"        {triangle[0]},"
                f"{triangle[1]},"
                f"{triangle[2]},-1,\n"
            )

        f.write("    ]\n")

        f.write("  }\n")
        f.write("}\n")


# ==============================
# メイン処理
# ==============================

start_time = time.time()


# 1. 点群データの読み込み

print("点群データを読み込んでいます...")

data_list = []

for filename in files:

    print(filename)

    data = read_dad(filename)
    data_list.append(data)

points = np.vstack(data_list)

print("読み込んだ点数:", len(points))


# 2. 格子の作成

print("格子を作成しています...")

x_grid, x_indices = align_axis(
    points[:, 0],
    EPS_X
)

y_grid, y_indices = align_axis(
    points[:, 1],
    EPS_Y
)

grid = np.full(
    (len(y_grid), len(x_grid)),
    -1,
    dtype=np.int32
)

grid[y_indices, x_indices] = np.arange(
    len(points),
    dtype=np.int32
)

print("格子のサイズ:", grid.shape)

np.savetxt("grid.dat", grid, fmt="%d")


# 3. 地面判定

print("\n地面・非地面の判定を開始します...")

ground_mask = judge_ground(
    grid,
    points,
    rate=GROUND_RATE,
    border=GROUND_BORDER
)

ground_count = np.count_nonzero(ground_mask)
building_count = len(points) - ground_count

print("地面・非地面の判定終了")
print("地面の点数:", ground_count)
print("非地面の点数:", building_count)
print("地面判定割合:", GROUND_RATE)
print("上りの高さ上限:", GROUND_BORDER, "m")


# 4. 曲率の計算

if os.path.exists("curvs.txt"):

    answer = input(
        "\ncurvs.txtが存在します。再計算しますか？ (y/n): "
    )

else:
    answer = "y"


if answer.lower() == "y":

    print("曲率を計算しています...")

    curvs = calc_curvs(points)

    np.savetxt("curvs.txt", curvs)

else:

    print("curvs.txtを読み込んでいます...")

    curvs = np.loadtxt("curvs.txt")

    if len(curvs) != len(points):
        print("点数が一致しないため、曲率を再計算します。")
        curvs = calc_curvs(points)
        np.savetxt("curvs.txt", curvs)


# 5. 点数と削減率の比較

before = len(points)

print("\n--- 曲率の閾値による比較 ---")

for sikii in (0, 1, 1.2):

    reduced_points = reduce_points2(
        points,
        curvs,
        sikii
    )

    after = len(reduced_points)

    print(
        "sikii =", sikii,
        "点数:", after,
        "削減率:", 1 - after / before
    )


# 6. VRML用の閾値を入力

vrml_threshold = float(
    input("\nVRML用の曲率の閾値を入力してください: ")
)


# 7. 点群を削減

print("点群を削減しています...")

keep = (
    (curvs == -1)
    | (curvs >= vrml_threshold)
)

vrml_points = points[keep]

# 削減後の点群に対応する地面判定結果
ground_for_vrml = ground_mask[keep]

after = len(vrml_points)

print("VRML用の点数:", after)
print("削減率:", 1 - after / before)

print(
    "削減後の地面点数:",
    np.count_nonzero(ground_for_vrml)
)

print(
    "削減後の非地面点数:",
    len(ground_for_vrml) - np.count_nonzero(ground_for_vrml)
)


# 8. Delaunay三角形分割

print("Delaunay三角形分割をしています...")

triangles = Delaunay(
    vrml_points[:, :2]
).simplices

# 三角形の向きを統一
triangle_xy = vrml_points[triangles, :2]

cross = (
    (triangle_xy[:, 1, 0] - triangle_xy[:, 0, 0])
    * (triangle_xy[:, 2, 1] - triangle_xy[:, 0, 1])
    -
    (triangle_xy[:, 1, 1] - triangle_xy[:, 0, 1])
    * (triangle_xy[:, 2, 0] - triangle_xy[:, 0, 0])
)

reverse = cross < 0

triangles[reverse] = triangles[reverse][:, [0, 2, 1]]

print("三角形の数:", len(triangles))


# 9. VRML出力

print("VRMLファイルを出力しています...")

write_vrml(
    "terrain_4.wrl",
    vrml_points,
    triangles,
    ground_for_vrml
)


# 10. 実行時間

end_time = time.time()

print("\n--- 完了 ---")
print("最終点数:", after)
print("削減率:", 1 - after / before)
print("実行時間:", round(end_time - start_time, 2), "秒")
