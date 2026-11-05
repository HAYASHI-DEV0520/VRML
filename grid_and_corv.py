import sys
import numpy as np

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


def fill_99():
    """
    欠損値(-9999.99)を補完する.
    """

try:
    points = read_dad()
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)


print(len(points))


# 調整するパラメータ 同じグループにまとめる許容幅
EPS_X = 0.3
EPS_Y = 0.3

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

with open("grid.dat", "w", encoding="utf-8") as f:
    for row in grid:
        f.write(" ".join(map(str, row)) + "\n")

def reduce_points(points,threshold):
    """曲率(ラプラシアンの絶対値)が threshold 以上の点と、格子の外周の点だけ残す."""
    keep = np.zeros(len(points), dtype=bool) #残す点はTrue.
    dx = 1.0
    dy = 1.0 #格子間隔 1 (定数でいいのか?)
    
    # 外周の点はすべて残す
    keep[grid[0, :]] = True
    keep[grid[-1, :]] = True
    keep[grid[:, 0]] = True
    keep[grid[:, -1]] = True

    for i in range(1, len(y_grid)-1):
        for k in range(1, len(x_grid)-1):
            # grid[i, k]からpointsのインデックスを取得し、その点の2列目(Z座標)で曲率計算
            # iはY方向, kはX方向?
            Dxx = (
                points[grid[i, k+1], 2]
                - 2 * points[grid[i, k], 2]
                + points[grid[i, k-1], 2]
            ) / dx**2

            Dyy = (
                points[grid[i+1, k], 2]
                - 2 * points[grid[i, k], 2]
                + points[grid[i-1, k], 2]
            ) / dy**2

            Dxy = (
                points[grid[i+1, k+1], 2]
                - points[grid[i+1, k-1], 2]
                - points[grid[i-1, k+1], 2]
                + points[grid[i-1, k-1], 2]
            ) / (4 * dx * dy)

            curv = np.sqrt(Dxx**2 + 2 * Dxy**2 + Dyy**2)

            if curv >= threshold:
                keep[grid[i, k]] = True
    return points[keep]