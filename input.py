data_wrl = []
with open("53394640_dsm_1m.dat") as f:
    for line in f:
        point_tmp = list(map(int, line.split()))
        dat_x = point_tmp[0]
        dat_y = point_tmp[1]
        dat_z = point_tmp[2]
        if dat_z == -9999.99:
            ...
        data_wrl.append([dat_x, dat_z, -1 * dat_y])
