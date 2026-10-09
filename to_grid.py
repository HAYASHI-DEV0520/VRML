import sys
import numpy as np
from sklearn.cluster import DBSCAN
 
def read_dad():
    """
    元データとVRMLでは異なるので、
    X座標はそのまま保持
    Y座標を-Z座標に変換
    Z座標をy座標に変換する.
    """
    data_wrl = []
    
    with open("53394610_dsm_1m.dat") as f:
        for line in f:
            dat_x, dat_y, dat_z = map(float, line.split())
            if dat_z == -9999.99:
                ... #欠損処理.
            data_wrl.append([
                value * sign
                for value, sign in zip(
                    (dat_x, dat_z, dat_y),
                    (1, 1, -1),
                )
            ])
    return data_wrl


def fill_99():
    """
    欠損値(-9999.99)を補完する.
    """

try:
    data = read_dad()
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)


print(data[0:100])


points = np.array([[dat_x, dat_y, dat_z] for dat_x, dat_z, dat_y in data])

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
