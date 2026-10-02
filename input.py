def read_dad_data():
    """
    元データとVRMLでは異なるので、
    X座標はそのまま保持
    Y座標を-Z座標に変換
    Z座標をy座標に変換する.
    """
    data_wrl = []
    with open("53394640_dsm_1m.dat") as f:
        for line in f:
            dat_x, dat_y, dat_z = map(int, line.split())
            if dat_z == -9999.99:
                ... #欠損処理.
            data_wrl.append([
                value * sign
                for value, sign in zip(
                    (dat_x, dat_z, dat_y),
                    (1, 1, -1),
                )
            ])
# comment