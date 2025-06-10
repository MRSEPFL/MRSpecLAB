import os
import re
import pandas as pd
import numpy as np
from interface import utils

# from skimage import measure

from inout.read_coord import ReadlcmCoord, extract_reference

def get_coord_map(dir): 
    if dir is not None:
        
        pattern = re.compile(r"(\d+)_(\d+)_(\d+)\.coord$")  # Regex pattern

        coord_files = []
        max_m, max_n, max_k = 0, 0, 0  # Track max dimensions

        # Step 1: Recursively find all .coord files and extract indices
        for root, _, files in os.walk(dir):
            for filename in files:
                match = pattern.match(filename)
                if match:
                    m, n, k = map(int, match.groups())
                    filepath = os.path.join(root, filename)
                    coord_files.append((m, n, k, filepath))

                    # Update max size
                    max_m = max(max_m, m)
                    max_n = max(max_n, n)
                    max_k = max(max_k, k)

        # Step 2: Initialize LCM dict matrix
        lcm = {}  # Initialize as an empty dictionary

        # Step 3: Read each file and store data
        for m, n, k, filepath in coord_files:
            if m not in lcm:
                lcm[m] = {}
            if n not in lcm[m]:
                lcm[m][n] = {}

            if filepath and os.path.exists(filepath):
                lcm[m][n][k] = ReadlcmCoord(filepath)
            else:
                lcm[m][n][k] = {}
                print(f"{filepath} does not exist!")

        return max_m, max_n, max_k, lcm

    return None


# def get_coord_map(dir):

#     if dir is not None:
        
#         pattern = re.compile(r"(?:.*/)?(\d+)_(\d+)_(\d+)[\\/]\1_\2_\3\.coord$")  # Regex pattern

#         coord_files = []
#         max_m, max_n, max_k = 0, 0, 0  # Track max dimensions

#         # Step 1: Find all .coord files and extract indices
#         for filename in os.listdir(dir):
#             match = pattern.match(filename)
#             if match:
#                 m, n, k = map(int, match.groups())
#                 coord_files.append((m, n, k, os.path.join(dir, filename)))

#                 # Update max size
#                 max_m = max(max_m, m)
#                 max_n = max(max_n, n)
#                 max_k = max(max_k, k)

#         # # Step 2: Initialize LCM dict matrix
#         lcm = {}  # Initialize as an empty dictionary

#         # Step 3: Read each file and store data
#         for m, n, k, filepath in coord_files:
#             if m not in lcm:
#                 lcm[m] = {}  # Initialize m-th level dictionary
#             if n not in lcm[m]:
#                 lcm[m][n] = {}  # Initialize n-th level dictionary

#             if filepath:
#                 lcm[m][n][k] = ReadlcmCoord(filepath)  # Store in matrix
#             else:
#                 lcm[m][n][k] = {}  # Store an empty dictionary if the file does not exist
#                 print(f"{filepath} does not exist!")

#         return max_m, max_n, max_k, lcm
    
#     return None


def get_conc_map(info):
    """
    Generate a concentration map based on provided metabolite and reference data.
    """
    lcm = info["coord"]
    metab_to_plot = info["metab_to_plot"]
    slice_idx = info["slice"]
    use_ref = info.get("use_ref", False)
    metab_ref = info.get("metab_ref", None)
    scaling = info.get("scaling", 1)

    # Determine the matrix size based on dimension
    dim_size_map = {
        0: [info["sz"][1], info["sz"][2]],
        1: [info["sz"][0], info["sz"][2]],
        2: [info["sz"][0], info["sz"][1]],
    }
    
    sz = dim_size_map.get(info["dim"])
    if not sz:
        utils.log_error("Invalid map dimension!")
        return None

    # Initialize matrices
    conc = np.zeros(sz)
    crlb = np.zeros(sz)
    c_ref = np.zeros(sz)
    
    conc_ref = np.zeros(sz)
    crlb_ref = np.zeros(sz)
    c_ref_ref = np.zeros(sz)

    try:
        if info["dim"] == 0:
            # Populate matrices
            for i in range(sz[0] - 1):
                for j in range(sz[1] - 1):
                    c = retrieve_conc_value(lcm[slice_idx][i + 1][j + 1], metab_to_plot)
                    conc[i, j], crlb[i, j], c_ref[i, j] = c['c'], c['SD'], c['c_ref']

                    if metab_ref and metab_ref != "None":
                        c_ref_val = retrieve_conc_value(lcm[slice_idx][i + 1][j + 1], metab_ref)
                        conc_ref[i, j], crlb_ref[i, j], c_ref_ref[i, j] = (
                            c_ref_val['c'], c_ref_val['SD'], c_ref_val['c_ref']
                        )

        elif info["dim"] == 1:
            # Populate matrices
            for i in range(sz[0] - 1):
                for j in range(sz[1] - 1):
                    c = retrieve_conc_value(lcm[i + 1][slice_idx][j + 1], metab_to_plot)
                    conc[i, j], crlb[i, j], c_ref[i, j] = c['c'], c['SD'], c['c_ref']

                    if metab_ref and metab_ref != "None":
                        c_ref_val = retrieve_conc_value(lcm[i + 1][slice_idx][j + 1], metab_ref)
                        conc_ref[i, j], crlb_ref[i, j], c_ref_ref[i, j] = (
                            c_ref_val['c'], c_ref_val['SD'], c_ref_val['c_ref']
                        )

        elif info["dim"] == 2:
            # Populate matrices
            for i in range(sz[0] - 1):
                for j in range(sz[1] - 1):
                    c = retrieve_conc_value(lcm[i + 1][j + 1][slice_idx], metab_to_plot)
                    conc[i, j], crlb[i, j], c_ref[i, j] = c['c'], c['SD'], c['c_ref']

                    if metab_ref and metab_ref != "None":
                        c_ref_val = retrieve_conc_value(lcm[i + 1][j + 1][slice_idx], metab_ref)
                        conc_ref[i, j], crlb_ref[i, j], c_ref_ref[i, j] = (
                            c_ref_val['c'], c_ref_val['SD'], c_ref_val['c_ref']
                        )
        else:
            utils.log_error("Invalid dimension selected!")
            return None
    except IndexError as e:
        utils.log_error(f"IndexError: {e}")
        return None

    # # Populate matrices
    # for i in range(sz[0] - 1):
    #     for j in range(sz[1] - 1):
    #         c = retrieve_conc_value(lcm[slice_idx][i + 1][j + 1], metab_to_plot)
    #         conc[i, j], crlb[i, j], c_ref[i, j] = c['c'], c['SD'], c['c_ref']

    #         if metab_ref and metab_ref != "None":
    #             c_ref_val = retrieve_conc_value(lcm[slice_idx][i + 1][j + 1], metab_ref)
    #             conc_ref[i, j], crlb_ref[i, j], c_ref_ref[i, j] = (
    #                 c_ref_val['c'], c_ref_val['SD'], c_ref_val['c_ref']
    #             )

    # Apply reference correction if needed
    if use_ref and metab_ref and metab_ref != "None":
        conc_masked = conc / conc_ref
        mask_ref = np.ones(sz)
        mask_ref[crlb_ref > info["crlb_threshold"]] = 0
    else:
        conc_masked = conc
        mask_ref = np.ones(sz)

    # Apply metabolite CRLB mask
    mask_metabo = np.ones(sz)
    mask_metabo[crlb > info["crlb_threshold"]] = 0

    # Apply both masks
    conc_masked *= mask_metabo * mask_ref

    # Replace zeros with NaN for better visualization
    conc_masked[conc_masked == 0] = np.nan

    return conc_masked * scaling

def retrieve_conc_value(lcm, metname):
    """Retrieve the value from lcm['conc']['name'] if it matches metaname."""
    for temp_c in lcm['conc']:
        if temp_c['name'] == metname:
            # print(temp_c['name'])
            return temp_c
    return None  # Return None if not found

def load_excel(filename):
    """
    Helper function to load data from an Excel file with multiple sheets.
    Each sheet contains data for one slice in the format (12, 12).
    """
    data = []
    for ls in range(1, 9):  # Assume sheets are named 'Slice1', 'Slice2', ..., 'Slice8'
        sheet_name = f'Slice{ls}'
        # Read each sheet and add it to the data list as a 2D array
        sheet_data = pd.read_excel(filename, sheet_name=sheet_name, header=None).values
        data.append(sheet_data)
    
    return np.stack(data, axis=-1)  # Stack into a 3D array with shape (12, 12, 8)

def create_brain_mask(slice_data):
    # Set a threshold to create a binary image
    threshold = 100  # Adjust threshold as necessary
    binary_image = slice_data > threshold

    # Get the dimensions of the image
    rows, cols = binary_image.shape

    # Define the center of the image
    center_x = cols // 2
    center_y = rows // 2

    # Detect boundaries in the binary image
    # boundaries = measure.find_contours(binary_image, level=0.5)

    # Initialize an empty mask with False (0) values
    mask = np.zeros_like(binary_image, dtype=bool)

    # Initialize a queue for the flood fill algorithm, starting from the center
    queue = [(center_y, center_x)]
    mask[center_y, center_x] = True  # Start point is part of the mask

    # Perform the flood fill from the center until a boundary is encountered
    while queue:
        # Pop the first pixel position from the queue
        y, x = queue.pop(0)

        # Check the 4-connected neighbors (up, down, left, right)
        neighbors = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]

        for ny, nx in neighbors:
            # Check if the neighbor is within bounds and not already part of the mask
            if 0 <= ny < rows and 0 <= nx < cols and not mask[ny, nx]:
                # If the neighbor is within the binary region and not a boundary
                if binary_image[ny, nx]:
                    # Add to the mask
                    mask[ny, nx] = True
                    # Add to the queue to continue growing
                    queue.append((ny, nx))
    return mask

def get_metabolite_list(filename):
    """Retrieve the metabolite list from the given file."""

    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        return None  # Or raise an exception: raise FileNotFoundError(f"File '{filename}' not found.")

    lcm = ReadlcmCoord(filename)
    ref = extract_reference(filename)

    if ref is None:
        print(f"Reference is not found.")
    else:
        print(f"Reference is '{ref}'.")

    metab_list = [metab['name'] for metab in lcm['conc']]
    # metab_list_with_ref = [name + ref for name in metab_list]
    # # Combine both lists
    # combined_metab_list = metab_list + metab_list_with_ref
    # return combined_metab_list 
    return metab_list