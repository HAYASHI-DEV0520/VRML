# VRML

## 削減後の点群表示

8つのDSMデータを同じフォルダーに置き、NumPy、SciPy、Plotlyをインストールして実行する。

```sh
./.venv/bin/python -m pip install numpy scipy plotly
./.venv/bin/python grid_and_corv.py
```

入力待ちでEnterを押すと、既存の `curvs.txt` を読み込む。別の文字を入力すると曲率を再計算する。処理後、`reduced_points_1.html`、`reduced_points_2.html`、`reduced_points_4.html` をブラウザーで開くと、各閾値の点群を3D表示できる。

表示は操作しやすいように最大20万点に間引き、タイトルに削減後の総点数と表示点数を示す。元の点群や削減点数は変わらない。

## 3Dグリッドビューア

`grid.dat`と8つのDSMデータを同じフォルダーに置き、次のコマンドで起動する。

```sh
./.venv/bin/python view_grid.py
```

表示されたURLをブラウザーで開くと、3D点群を回転・拡大縮小し、格子の行と列を指定して点と四近傍を確認できる。

## VRML出力

DSMデータから、環境光付きの指向性光源(`DirectionalLight`)を含むVRML地形を生成する。

```sh
python to_vrml.py output.wrl input1.dat input2.dat
```

`--threshold`で簡略化の閾値を指定できる。値を小さくすると地形の細部が多く残る。

やることリスト

・元データのXYZ座標がVRMLでは異なるので、X座標はそのまま保持、Y座標を -Z座標に変換、z座標をy座標に変換する。  
・欠損点を補正する。  
→元データのz座標が-9999.99になっているとき、四近傍のいずれかの点と同じ座標にする。
