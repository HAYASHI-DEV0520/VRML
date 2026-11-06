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
]#リストとしてすべてのファイルを読み込んでいる。


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


def miss_point(grid):#ここを自分で作る＃二次元配列のgridを受け取り、欠損値を補完する関数を作る
    #欠損値(-9999.99)を補完する.
    
    L = []
    #欠損点を見つけたら、その点の周囲八つを見て小さい方から見て4番目の値を欠損点の値にする

    #すべての点で欠損点を探す
    for i in range(len(grid[0])):
        for j in range(len(grid[1])):
            if grid[i][j] == -9999.99:
                #周囲八つの点を見て小さい方から見て4番目の値を欠損点の値にする
                neighbors = []
                for x in range(-1, 2):
                    for y in range(-1, 2):
                        if x == 0 and y == 0:#自分自身の点は除外する
                            continue
                        if i + x >= 0 and i + x < len(grid[0]) and j + y >= 0 and j + y < len(grid[1]):
                            if grid[i + x][j + y] != -9999.99:
                                neighbors.append(grid[i + x][j + y])
                neighbors.sort()
                grid[i][j] = neighbors[len(neighbors) // 2]#小さい方から見て4番目の値を欠損点の値にする
    



try:
    points = read_dad()
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)


print(len(points))


# 調整するパラメータ
EPS_X = 0.3
EPS_Y = 0.3

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
