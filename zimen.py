import numpy as np
def zimen(grid):

    a=np.array([grid])#全データ入れる

    a=a[np.argsort(a[:,2])]#座標で並び替え

    n=len(a)

    zim=a[:n//4].copy#４ぶんの１

    for i in range(len(grid)):
        for j in range(len(grid[i])):
            p=grid[i][j]
            if np.any(np.all(zim==p, axis=1)):
                continue
            neightbors = []
            if i>0:
                neightbors.append(grid[i-1][j])
            if i<len(grid)-1:
                neightbors.append(grid[i+1][j])
            if j>0:
                neightbors.append(grid[i][j-1])
            if j<len(grid[i])-1:
                neightbors.append(grid[i][j+1])
            if any(abs(p[2]-q[2])<2 for q in neightbors):
                zim=np.vstack((zim,p))


            