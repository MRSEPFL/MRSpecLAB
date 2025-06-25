import sys
import ants
import pickle
import numpy as np

with open(sys.argv[1], "rb") as f:
    args_in = pickle.load(f)

seg_files = args_in[0]
centre = args_in[1]
transform = args_in[2]
out_path = args_in[3]

wm_img, gm_img, csf_img = tuple([ants.image_read(f) for f in seg_files])
thickness = np.array([np.max(np.abs(np.array(transform)[:3, i])) for i in range(3)])
i1 = ants.transform_physical_point_to_index(wm_img, centre - thickness / 2).astype(int)
i2 = ants.transform_physical_point_to_index(wm_img, centre + thickness / 2).astype(int)
for i in range(3):
    if i1[i] > i2[i]: i1[i], i2[i] = i2[i], i1[i]
wm_gm_csf_sums = [np.sum(img.numpy()[i1[0]:i2[0], i1[1]:i2[1], i1[2]:i2[2]]) for img in [wm_img, gm_img, csf_img]]

with open(out_path, "wb") as f:
    pickle.dump(wm_gm_csf_sums, f)