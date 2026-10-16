# VRML

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
