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

#使わない
def reduce_points(points,sikii):
    
    keep = np.zeros(len(points), dtype=bool) #pointsと同じ長さの配列をFalseで初期化,これから残す点はTrueに更新.
    curvs = np.zeros(len(points))
    dx = 1.0
    dy = 1.0 #格子間隔 1 (定数でいいのか?)
    
    

    for i in range(0, len(y_grid)):
        for k in range(0, len(x_grid)):
            if i == 0 or i == (len(y_grid) - 1 or k == 0 or k == (len(x_grid) - 1)):
                keep[grid[i][k]] = True # 外周の点はすべて残す.
            # grid[i, k]からpointsのインデックスを取得し、その点の2列目(Z座標)で曲率計算
            # iはY方向, kはX方向?
            Dxx = (points[grid[i, k+1], 2] - 2 * points[grid[i, k], 2] + points[grid[i, k-1], 2]) / dx**2

            Dyy = (points[grid[i+1, k], 2] - 2 * points[grid[i, k], 2] + points[grid[i-1, k], 2]) / dy**2

            Dxy = (points[grid[i+1, k+1], 2] - points[grid[i+1, k-1], 2]- points[grid[i-1, k+1], 2]+ points[grid[i-1, k-1], 2]) / (4 * dx * dy)

            curv = np.sqrt(Dxx**2 + 2 * Dxy**2 + Dyy**2) 
            curvs[grid[i, k]] = curv
            if curv >= sikii:
                keep[grid[i, k]] = True #残す点はTrueに更新.
    print("\n曲率最大", curvs.max())
    print("曲率最小", curvs.min())
    
    return points[keep]

def calc_curvs(points):
    """曲率を計算しpointsのインデックス順にcurvsに曲率値を格納 必ず残す点(外周など)は-1を返す."""
    curvs = [-1] * len(points)  #初期値-1は 計算されずに-1だったらその点は残す
    dx = 1.0
    dy = 1.0 #格子間隔 1 (定数でいいのか?)

    for i in range(1, len(y_grid)-1):
        for k in range(1, len(x_grid)-1):
            # grid[i, k]からpointsのインデックスを取得し、その点の2列目(Z座標)で曲率計算
            # iはY方向, kはX方向
            Dxx = (points[grid[i, k+1], 2] - 2 * points[grid[i, k], 2] + points[grid[i, k-1], 2]) / dx**2

            Dyy = (points[grid[i+1, k], 2] - 2 * points[grid[i, k], 2] + points[grid[i-1, k], 2]) / dy**2

            Dxy = (points[grid[i+1, k+1], 2] - points[grid[i+1, k-1], 2] - points[grid[i-1, k+1], 2] + points[grid[i-1, k-1], 2]) / (4 * dx * dy)

            curv = np.sqrt(Dxx**2 + 2 * Dxy**2 + Dyy**2)

            curvs[grid[i, k]] = curv

    print("\n曲率最大", curvs.max())
    print("曲率最小", curvs.min())

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

before = len(points)

print("元の点数", before)
if (input("ENTERでtxtから読み込み")):
    curvs = np.array(calc_curvs(points))
else:
    with open("curvs.txt", "rt") as f:
        curvs = [float(line) for line in f.read().splitlines()]
for i in (1, 2, 4):
    after = len(reduce_points2(points, curvs, i))

    print(
        "sikii =", i,
        "点数:", after,
        "削減率:", 1 - after / before
    )