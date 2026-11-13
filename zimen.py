    import numpy as np
    def zimen(grid,points):
        #有効点を抽出
        valid=grid>=0
        indices=grid[valid]

        #z座標を低い順に並べる
        order=np.argsort(points[indices,2])

        #1/4を地面に
        n=len(indices)
        seeds=indices[order[:n//4]]
        ground=set(seeds)

        stack=list(seeds)
        while stack:
            current=stack.pop()
            #現在の点の座標
            i,j=np.where(grid==current)
            #近傍の点
            neighbors=[(i-1,j),(i+1,j),(i,j-1),(i,j+1)]
            for ni,nj in neighbors:
                if not (0<=ni<grid.shape[0] and 0<=nj<grid.shape[1]):
                    continue
                neighbor=grid[ni,nj]
                if neighbor==-1:
                    continue
                dz=abs(points[neighbor,2]-points[current,2])
                if dz<2:
                    ground.add(neighbor)
                    stack.append(neighbor)
        return np.array(list(ground))    
            