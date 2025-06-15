import os
import numpy
import mapvbvd
import suspect.io
import pydicom.dicomio
import nibabel, json
from suspect import MRSData
from suspect.io._common import complex_array_from_iter
from suspect.io.twix import calculate_orientation
from suspect._transforms import rotation_matrix
from .read_header import DataReaders
import interface.utils as utils

def load_file(filepath):
    header = None
    ext = os.path.splitext(filepath)[-1][1:].lower()
    if ext == "ima":
        data, header = load_ima_from_suspect(filepath)
        
    elif ext == "dcm":
        data = load_dicom(filepath) # suspect's load_dicom doesn't work
        header, _ = DataReaders().siemens_ima(filepath, None)
        if header["Nucleus"] != "1H":
            data.ppm0 = 0
    elif ext == "dat":
        data = loadVBVD(filepath)
        header, _ = DataReaders().siemens_twix(filepath, None)
    elif ext == "sdat":
        data = suspect.io.load_sdat(filepath, None) # should find .spar
        spar = filepath.lower()[:-5] + ".spar"
        if os.path.exists(spar):
            header, _ = DataReaders().philips_spar(spar, None)
    elif ext == "rda":
        data, header = load_rda(filepath) # no rda in DataReaders; we only need Sequence and Nucleus for processing
    elif ext == "nii" or filepath.endswith(".nii.gz"):
        data, header = load_nifti(filepath) # no nii in DataReaders
        ext = "nii"
    else:
        return None, None, None, None
    vendor = None
    if ext in ["ima", "dat"]: vendor = "siemens"
    elif ext == "sdat": vendor = "philips"
    if not isinstance(data, list): data = [data]
    return data, header, ext, vendor

def loadVBVD(filepath):
    twixobj = mapvbvd.mapVBVD(filepath, quiet=True)
    if isinstance(twixobj, list):
        if len(twixobj) == 1: twixobj = twixobj[0]
        if len(twixobj) == 2: twixobj = twixobj[1] # twixobj[0] is reference noise
        else:
            utils.log_error("Multiple acquisitions found in Twix file.")
            return None

    twixobj.image.removeOS = False
    data = twixobj.image['']
    data = numpy.squeeze(data)
    axes = twixobj.image.sqzDims
    # print(axes, data.shape)
    
    ave_per_rep = 1
    for i in range(len(axes)-1, -1, -1):
        if axes[i] not in ["Col", "Cha", "Ave", "Rep"]:
            data = numpy.mean(data, axis=i) # violence
    if 'Ave' in axes: ave_per_rep = data.shape[axes.index('Ave')]
    if 'Ave' in axes and 'Rep' in axes: # transform [Col, Cha, Ave, Rep] into [Rep*Ave, Cha, Col]
        data = numpy.transpose(data, (axes.index('Rep'), axes.index('Ave'), axes.index('Cha'), axes.index('Col')))
        data = numpy.reshape(data, (data.shape[0] * data.shape[1], data.shape[2], data.shape[3]))
    elif 'Rep' in axes:
        data = numpy.transpose(data, (axes.index('Rep'), axes.index('Cha'), axes.index('Col')))
    elif 'Ave' in axes:
        data = numpy.transpose(data, (axes.index('Ave'), axes.index('Cha'), axes.index('Col')))
    data = numpy.conj(data)

    # parameters
    if "DwellTime" in twixobj.hdr["Config"]:
        dt = twixobj.hdr["Config"]["DwellTime"] * 1e-9 # ns to s
    else:
        dt = twixobj.hdr["Config"]["DwellTimeSig"] * 1e-9 # ns to s
    f0 = twixobj.hdr["Config"]["Frequency"] * 1e-6 # Hz to MHz
    te = float(twixobj.hdr["Meas"]["alTE"].split()[0]) * 1e-3 # us to ms
    tr = float(twixobj.hdr["Meas"]["alTR"].split()[0]) * 1e-3 # us to ms

    transform = get_transform(twixobj)
    metadata = {
        "ave_per_rep": ave_per_rep
    }
    
    return [MRSData(data[i], dt, f0, te=te, tr=tr, transform=transform, metadata=metadata) for i in range(data.shape[0])] # separate repetitions

def get_transform(twixobj):
    pos_sag = twixobj.hdr["Config"]["VoI_Position_Sag"]
    pos_cor = twixobj.hdr["Config"]["VoI_Position_Cor"]
    pos_tra = twixobj.hdr["Config"]["VoI_Position_Tra"]
    if pos_sag == '': pos_sag = 0
    if pos_cor == '': pos_cor = 0
    if pos_tra == '': pos_tra = 0
    pos_sag = float(pos_sag)
    pos_cor = float(pos_cor)
    pos_tra = float(pos_tra)
    
    normal_sag = twixobj.hdr["Config"]["VoI_Normal_Sag"]
    normal_cor = twixobj.hdr["Config"]["VoI_Normal_Cor"]
    normal_tra = twixobj.hdr["Config"]["VoI_Normal_Tra"]
    if normal_sag == '': normal_sag = 0
    if normal_cor == '': normal_cor = 0
    if normal_tra == '': normal_tra = 0
    normal_sag = float(normal_sag)
    normal_cor = float(normal_cor)
    normal_tra = float(normal_tra)

    ro_fov = float(twixobj.hdr["Config"]["VoI_RoFOV"])
    pe_fov = float(twixobj.hdr["Config"]["VoI_PeFOV"])
    slice_thickness = float(twixobj.hdr["Config"]["VoI_SliceThickness"])
    in_plane_rot = twixobj.hdr["Config"]["VoI_InPlaneRotAngle"]
    if in_plane_rot == '': in_plane_rot = 0
    
    normal_vector = numpy.array([normal_sag, normal_cor, normal_tra])
    if calculate_orientation(normal_vector) == "SAG": x_vector = numpy.array([0, 0, 1])
    else: x_vector = numpy.array([-1, 0, 0])
    orthogonal_x = x_vector - numpy.dot(x_vector, normal_vector) * normal_vector
    orthonormal_x = orthogonal_x / numpy.linalg.norm(orthogonal_x)
    rot_matrix = rotation_matrix(in_plane_rot, normal_vector)
    row_vector = numpy.dot(rot_matrix, orthonormal_x)
    column_vector = numpy.cross(row_vector, normal_vector)
    transform = transformation_matrix(row_vector, column_vector, [pos_sag, pos_cor, pos_tra], [ro_fov, pe_fov, slice_thickness])
    return transform

# adapted from suspect._transforms
def transformation_matrix(x_vector, y_vector, translation, spacing):
    matrix = numpy.zeros((4, 4), dtype=float) # removed deprecated numpy.float
    matrix[:3, 0] = x_vector
    matrix[:3, 1] = y_vector
    z_vector = numpy.cross(x_vector, y_vector)
    matrix[:3, 2] = z_vector
    matrix[:3, 3] = numpy.array(translation)
    matrix[3, 3] = 1.0
    spacing = list(spacing)
    while len(spacing) < 4:
        spacing.append(1.0)
    for i in range(4):
        for j in range(4):
            matrix[i, j] *= spacing[j]
    return matrix

# adapted from suspect.io.load_dicom
def load_dicom(filename):
    dataset = pydicom.dicomio.read_file(filename)
    sw = dataset[0x0018, 0x9052].value
    dt = 1.0 / sw
    f0 = dataset[0x0018, 0x9098].value
    te = float(dataset[0x5200, 0x9229][0][0x0018, 0x9114][0][0x0018, 0x9082].value)
    tr = float(dataset[0x5200, 0x9229][0][0x0018, 0x9112][0][0x0018, 0x0080].value)
    ppm0 = dataset[0x0018, 0x9053].value
    rows = dataset[0x0028, 0x0010].value
    cols = dataset[0x0028, 0x0011].value
    frames = dataset[0x0028, 0x0008].value
    num_second_spectral = dataset[0x0028, 0x9001].value
    num_points = dataset[0x0028, 0x9002].value
    data_shape = [frames, rows, cols, num_second_spectral, 4*num_points]
    data_iter = iter(dataset[0x5600, 0x0020])
    data = complex_array_from_iter(data_iter, shape=data_shape, chirality=-1)
    return MRSData(data, dt, f0=f0, te=te, tr=tr, ppm0=ppm0)

def load_rda(filepath):
    header = {}
    dt = None
    tr = None
    te = None
    f0 = None
    vector_size = None
    CSIMatrix_Size = [0, 0, 0]
    filebytes = open(filepath, 'rb').read()
    headerend = filebytes.find(">>> End of header <<<".encode('utf-8')) + 21
    headerstr = filebytes[:headerend].decode('utf-8')
    data = filebytes[headerend:]
    data = data[len(data) % 16:]
    for line in headerstr.split('\n'):
        if line.startswith('Nucleus: '):
            header["Nucleus"] = line.split(':')[1].strip()
            continue
        if line.startswith('SequenceName: '):
            header["Sequence"] = line.split(':')[1].strip()
            continue
        if line.startswith('TR: '):
            tr = float(line.split(':')[1].strip()) # ms
            continue
        if line.startswith('TE: '):
            te = float(line.split(':')[1].strip()) # ms
            continue
        if line.startswith('DwellTime: '):
            dt = float(line.split(':')[1].strip()) * 1e-6 # us
            continue
        if line.startswith('MRFrequency: '):
            f0 = float(line.split(':')[1].strip().replace(',', '.')) # MHz
            continue
        if line.startswith('VectorSize: '):
            vector_size = int(line.split(':')[1].strip())
            continue
        # For CSI
        if line.startswith('CSIMatrixSize[0]: '):
            CSIMatrix_Size[0] = int(line.split(':')[1].strip())
            header["CSIMatrix_Size[0]"] = CSIMatrix_Size[0]
            continue
        if line.startswith('CSIMatrixSize[1]: '):
            CSIMatrix_Size[1] = int(line.split(':')[1].strip())
            header["CSIMatrix_Size[1]"] = CSIMatrix_Size[1]
            continue
        if line.startswith('CSIMatrixSize[2]: '):
            CSIMatrix_Size[2] = int(line.split(':')[1].strip())
            header["CSIMatrix_Size[2]"] = CSIMatrix_Size[2]
            continue
    utils.log_info(f"CSIMatrix_Size: {CSIMatrix_Size}")
    ppm0 = 4.7 if header["Nucleus"] == "1H" else 0
    datamatrix = numpy.frombuffer(data, dtype=numpy.float64)
    utils.log_info(f"Shape of the datamatrix: {datamatrix.shape}")

    if not (CSIMatrix_Size[0] == 1 and CSIMatrix_Size[1] == 1 and CSIMatrix_Size[2] == 1): # CSI
        datamatrix = datamatrix[::2] + 1j * datamatrix[1::2]
        data = datamatrix.reshape(CSIMatrix_Size[0], CSIMatrix_Size[1], CSIMatrix_Size[2], vector_size)
        # data = numpy.squeeze(datamatrix)
    else: # SVS
        data = datamatrix[::2] + 1j * datamatrix[1::2]  
    # assert data.size == vector_size
    utils.log_info(f"Shape of the data: {data.shape}")
    return MRSData(data, dt, f0=f0, te=te, tr=tr, ppm0=ppm0), header

def load_nifti(filepath):
    img: nibabel.nifti2.Nifti2Image = nibabel.load(filepath)
    hdr_ext_codes = img.header.extensions.get_codes()
    mrs_hdr_ext = json.loads(img.header.extensions[hdr_ext_codes.index(44)].get_content())

    if img.header.get_value_label("datatype") == "complex128":
        data = img.get_fdata(dtype=numpy.complex128)
    elif img.header.get_value_label("datatype") == "complex64":
        data = img.get_fdata(dtype=numpy.complex64)
    else:
        utils.log_error(f"Unknown datatype in NIfTI file {filepath}.")
        return None, None
    if not all([d == 1 for d in data.shape[:3]]):
        utils.log_error("Multi-voxel data not supported.")
        return None, None
    data = data[0, 0, 0] # single voxel data
    coilcombined = True
    ave_per_rep = 1
    if len(data.shape) == 1:
        data = numpy.expand_dims(data, axis=0)     
    else:
        order = [0, 0, 0, 0]
        mapping = {"DIM_MEAS": 0, "DIM_DYN": 1, "DIM_EDIT": 2, "DIM_COIL": 3}
        for i in range(len(data.shape) - 1):
            key = f"dim_{i+5}"
            if key in mrs_hdr_ext:
                if mrs_hdr_ext[key] in mapping:
                    order[mapping[mrs_hdr_ext[key]]] = i + 1
                    if mrs_hdr_ext[key] == "DIM_COIL": coilcombined = False
                    if mrs_hdr_ext[key] == "DIM_EDIT": ave_per_rep = data.shape[i+1]
                else:
                    utils.log_warning(f"Unknown dimension {mrs_hdr_ext[key]} in NIfTI file {filepath}.")
                    data = numpy.mean(data, axis=i+1)
        order = [i for i in order if i != 0].append(0)
        data = numpy.transpose(data, order)
    if coilcombined: data = numpy.reshape(data, (numpy.prod(data.shape[:-1]), data.shape[-1]))
    else: data = numpy.reshape(data, (numpy.prod(data.shape[:-2]), data.shape[-2], data.shape[-1]))
    
    dt = img.header["pixdim"][4]
    if img.header["xyzt_units"] & 16: # dt in ms or us
        if img.header["xyzt_units"] & 8:
            dt = dt * 1e-6 # us to s
        else: dt = dt * 1e-3 # ms to s

    try: f0 = mrs_hdr_ext["SpectrometerFrequency"][0] # MHz
    except: utils.log_error("SpectrometerFrequency not found in header extension.")
    try: te = mrs_hdr_ext["EchoTime"] * 1e3 # s to ms
    except: utils.log_error("Echo time not found in header extension")
    try: tr = mrs_hdr_ext["RepetitionTime"] * 1e3 # s to ms
    except: utils.log_error("Repetition time time not found in header extension")

    header = {}
    header["Nucleus"] = mrs_hdr_ext["ResonantNucleus"][0]
    header["Sequence"] = None
    if "SequenceName" in mrs_hdr_ext:
        header["Sequence"] = mrs_hdr_ext["SequenceName"]
    elif "siemens_sequence_info" in mrs_hdr_ext and "sequence" in mrs_hdr_ext["siemens_sequence_info"]:
        header["Sequence"] = mrs_hdr_ext["siemens_sequence_info"]["sequence"]
    
    transform = numpy.array(img.header.get_best_affine())
    metadata = {
        "ave_per_rep": ave_per_rep
    }
    return [MRSData(data[i], dt, f0, te=te, tr=tr, transform=transform, metadata=metadata) for i in range(data.shape[0])], header

def load_ima_from_suspect(filepath):
    data = suspect.io.load_siemens_dicom(filepath)
    header, _ = DataReaders().siemens_ima(filepath, None)
    for key in ["Nucleus", "nucleus"]:
        if key in header.keys():
            nucleus = header[key]
            if nucleus != "1H":
                data.ppm0 = 0
    return data, header
