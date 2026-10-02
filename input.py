def read_dad():
    """
    元データとVRMLでは異なるので、
    X座標はそのまま保持
    Y座標を-Z座標に変換
    Z座標をy座標に変換する.
    """
    data_wrl = []
    with open("53394640_dsm_1m.dat") as f:
        for line in f:
            point_tmp = list(map(int, line.split()))
            dat_x = point_tmp[0]
            dat_y = point_tmp[1]
            dat_z = point_tmp[2]
            data_wrl.append([dat_x, dat_z, -1 * dat_y])
    return data_wrl

def fill_99():
    """
    欠損値(-9999.99)を補完する.
    """
    