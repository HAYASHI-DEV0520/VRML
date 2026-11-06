import numpy as np
from sklearn.cluster import DBSCAN

points = np.array([
    [0.0, 0.0],
    [2.5, 0.0],
    [2.4, 0.8],
    [4.8, 1.6],
    [12.5, 3.8],
    [0.0, 0.0]
])

# 調整するパラメータ
EPS_X = 0.3
EPS_Y = 0.3

def align_axis(values, eps):
    labels = DBSCAN(
        eps=eps,
        min_samples=1
    ).fit_predict(values.reshape(-1, 1))

    centers = np.array([
        values[labels == i].mean()
        for i in np.unique(labels)
    ])

    return centers[labels], np.sort(centers)

x, x_grid = align_axis(points[:, 0], EPS_X)
y, y_grid = align_axis(points[:, 1], EPS_Y)

aligned = np.column_stack((x, y))

print("整列後:", aligned)
print("X方向の列数:", len(x_grid))
print("Y方向の行数:", len(y_grid))


# 各点の整数インデックスを求める
cols = np.searchsorted(x_grid, x)
rows = np.searchsorted(y_grid, y)

# 2次元配列を作成（-1は点が存在しない場所）
grid = np.full(
    (len(y_grid), len(x_grid)),
    -1,
    dtype=int
)

# 格子に元の点の番号を格納
for i, (r, c) in enumerate(zip(rows, cols)):
    grid[r, c] = i

print(grid)