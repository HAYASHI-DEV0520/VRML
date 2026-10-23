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
    h = 1 #格子間隔 1 (定数でいいのか?)
    for i in range(len(x_grid)):
        if(i == 0 or i == len(x_grid)-1):
            continue # 角は飛ばす?.
        for k in range(len(y_grid)):
            if(k == 0 or k == len(y_grid)-1):
                continue # 角は飛ばす?.
            # grid[i][k]に対して
           
            z = points[grid[i-1:i+2, k-1:k+2], 2]  # 高さ成分を取得

            Dxx = (z[2, 1] - 2*z[1, 1] + z[0, 1]) / h**2
            Dyy = (z[1, 2] - 2*z[1, 1] + z[1, 0]) / h**2
            Dxy = (
                z[2, 2] - z[2, 0]
                - z[0, 2] + z[0, 0]
            ) / (4*h**2)

            curv = np.sqrt(Dxx**2 + 2*Dxy**2 + Dyy**2)
            if curv >= threshold: # 閾値以上なら
                ... #削減
