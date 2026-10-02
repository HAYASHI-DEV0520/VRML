"""スペース区切りのファイルを読み込むサンプルプログラム。

入力例 (data.txt):
    apple 120 3
    banana 80 5
    orange 100 2

使い方:
    python read_space_sample.py data.txt
"""

import sys


def read_space_separated(path):
    """各行をスペース(連続した空白も可)で分割し、リストのリストとして返す。"""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:  # 空行は飛ばす
                continue
            rows.append(line.split())  # 引数なしの split() は連続空白もまとめて区切る
    return rows


def main():
    if len(sys.argv) != 2:
        print("使い方: python read_space_sample.py <ファイル名>")
        sys.exit(1)

    path = sys.argv[1]

    try:
        rows = read_space_separated(path)
    except FileNotFoundError:
        print(f"ファイルが見つかりません: {path}")
        sys.exit(1)

    for number, row in enumerate(rows, start=1):
        print(f"{number}行目: {row}")

    # 例: 2列目を数値として合計する (数値でない行は無視)
    total = 0.0
    for row in rows:
        if len(row) >= 2:
            try:
                total += float(row[1])
            except ValueError:
                pass
    print(f"2列目の合計: {total}")


if __name__ == "__main__":
    main()
