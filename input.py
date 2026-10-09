import sys
 
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


def write_dad(data, path="converted_coordinates.txt"):
    """変換後の座標をスペース区切りでファイルに保存する."""
    with open(path, "w", encoding="utf-8") as f:
        for dat_x, dat_y, dat_z in data:
            f.write(f"{dat_x} {dat_y} {dat_z}\n")


def fill_99():
    """
    欠損値(-9999.99)を補完する.
    """

try:
    data = read_dad()
    write_dad(data)
except FileNotFoundError as error:
    print(f"ファイルが見つかりません: {error.filename}")
    sys.exit(1)

print("変換結果を converted_coordinates.txt に保存しました。")