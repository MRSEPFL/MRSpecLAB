[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14866163.svg)](https://zenodo.org/records/14866163)

# Simple download and double-click application for windows users to process MRS(I) data.

--> download example datasets, basis sets and pipelines from [zenodo](https://zenodo.org/records/14866163).

--> .exe and .ext (Windows/Linux) executables available in the newest release.

--> source code available for other OS in this repository.

The MRSpecLAB platform is closely described in this publication: [PUBLICATION](insert link). For help please contact us under: MRSpecLAB@gmail.com.
If you would like to be kept updated about the newest additions and updates, please subscribe to the [mailinglist](https://forms.gle/AQjCQu7JHhiadrfx8).

A detailed user manual can be found in [MANUAL.md](/MANUAL.md).

# MRSpecLAB
MRSpecLAB is a graphical platform for the processing and analysis of magnetic resonance spectroscopy data, focusing on user-friendliness, automated use and modularity. Currently supported and tested formats are DICOM and Twix files for Siemens, .SDAT .SPAR for Philips, and NIFTI.
If you have data in another data format, we, for now, recommend converting it to NIFTI using the [spec2nii](https://github.com/wtclarke/spec2nii) package.

## Installation and usage

### Windows Executable
A Windows executable file (.exe) is available and can be run directly after downloading the .rar package. Place the zipped folder in your desired directory, unpack it, find the .exe file and double-click it. Depending on your setup the first time opening the program might take 1-2 min. 

- Currently this executable only contains the default processing nodes and does not retrieve any new ones from the github repository. If you desire to use your self-written processing nodes, or nodes written by other users, you can simply place the python script in the 'customer_nodes' folder of your toolbox folder and rerun the .exe file.

- Process your data in four simple steps:
  1) Load your data in the left data boxes (metabolite on top and water on the bottom (optional)).
  2) look at the provided processing pipeline and alternate if desired by clicking on the colorful chain icon on top.
  3) Input your .basis set and LCModel .control file by clicking the 'fitting options' button on top, otherwise a default will be loaded.
  4) Click the run button (either step-by-step [left] or in one go [right]).

 --> more options available, please refer to the detailed user [MANUAL.md](/MANUAL.md).
  
### Run the source code
To run this application from source (you will need a working python prepared environment), download and extract this repository. Required packages can be installed by running the following command in the repository folder:

```pip install -r requirements.txt```

The GUI can be opened by running `MRSpecLAB.py` with Python and is hoped to be self-explanatory. The program currently runs on Python versions 3.9, 3.10 and 3.11.

The application detects any nodes placed in the `customer_nodes` folder. The creation of custom nodes is detailed in the publication and user manual. A similar function might be planned for reading custom data types. You can also find a template script on the main github repository.

### Linux
On a Linux system, the pip command given above will probably try to build the wxPython package for your specific Linux distribution, which can take a very long time. A much quicker alternative is to abort the running command (Ctrl+C in the terminal window) and download the latest pre-built package (`.whl` file) from the [wxPython database](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/) according to your OS (folder) and Python (cpXXX) versions. You can then install it using the following command ([source](https://wxpython.org/pages/downloads/index.html)):

```pip install -f <path_to_whl_file> wxPython```

(Re-)running `pip install -r requirements.txt` should verify that installation and ensure no other packages are missing.

## License and used libraries
MRSpecLAB is released under the Apache 2.0 license.

Code was taken and modified from the 'suspect' library for file-reading and processing functions and the `gsnodegraph` library for the editor panel. Windows and Linux binaries for LCModel were compiled from the source code on [Georg Oeltzschner's repository](https://github.com/schorschinho/LCModel), and compressed and shipped alongside our application for a straight-forward installation. Standardised MRS header reading was taken and slightly modified from the [REMY project](https://github.com/agudmundson/mrs_in_mrs), reading in data, data conversion and header information read-in were taken from [spec2nii](https://github.com/wtclarke/spec2nii).

## Acknowledgements
<table>
  <tr>
    <td>
      <p align="center">
      <a href="https://www.snf.ch/en"> <img width="200" src="https://github.com/user-attachments/assets/db4bf8cf-0d36-4759-ac6c-0303a8e53207"/> </a>
      <a href="https://epfl.ch"> <img width="200" src="https://github.com/poldap/GlobalBioIm/blob/master/Doc/source/EPFL_Logo_Digital_RGB_PROD.png"/> </a>
      <a href="https://cibm.ch"> <img width="400" src="https://github.com/poldap/GlobalBioIm/blob/master/Doc/source/Logo-CIBM_variation-colour-72dpi.png"/> </a>
        </p>
    </td>
  </tr>
  <tr>
    <td>
      We acknowledge the support of the <a href="https://www.snf.ch/en">Swiss National Science Foundation </a>, the  <a href="https://epfl.ch">École Polytechnique Fédérale de Lausanne</a>, in Lausanne, Switzerland, and the <a href="https://cibm.ch">CIBM Center for Biomedical Imaging</a>, in Switzerland.
    </td>
  </tr>
</table>


# MRS Processing Overview Summary

---

## (1) Input Data Format

| Format | Extensions |
|--------|------------|
| NIfTI  | `.nii` |
| Siemens | `.IMA`, `.rda`, `.dat` |

---

## (2) Default Processing Functions

### Nodes & Tunable Parameter Descriptions

| Node | Tunable Parameter Descriptions |
|------|-------------------------------|
| Adaptive coil combination | Number of shots per measurement (int) |
| S/N² coil combination | Number of shots per measurement (int), proportion from the end of the FID to use as noise (float) |
| SVD coil combination | N/A |
| 3D Hanning Filter| Window Size X (int), Window Size Y (int), Window Size Z (int)|
| Frequency & Phase Alignment | Zero-padding factor (int), line-broadening factor (int), whether to perform frequency alignment (choice), whether to perform phase alignment (choice), reference peak range in ppm (vector), whether to set target to median (bool), or specify index of input data (string) |
| Phase Alignment (31P) | Zero-padding factor (int), line-broadening factor (int), reference peak range in ppm (vector), whether to set target to median (bool), or specify index of input data (string) |
| Eddy Current Correction | Gaussian width of the phase smoothing window (int) |
| Line Broadening | Line broadening factor (int) |
| Line Broadening CSI (Gaussian) | Linewidth (int) |
| Line Broadening (Gaussian) | Line broadening factor (int) |
| Zero Padding | Zero Padding factor (int) |
| Remove Bad Averages | Number of standard deviations for outlier removal (int), domain for z-test (choice: time/frequency), time value up to which to perform z-test (float) |
| Quality Matrix | N/A |
| Averaging | N/A |
| Block Averaging | Number of measurements in a block (int), number of averages per block (int), number of block types (int) |
| Moving Average | Window length (int) |
| S/N² Averaging | Number of measurements in a repetition (int), proportion of FID used as noise (float) |

---

## (3) Fitting

| Item | Description |
|------|-------------|
| Algorithm | LCModel |
| Input (optional) | `.basis`, `.control`, tissue segmentation files (GM, WM, CSF; probabilistic) (`.nii`) |

---

## (4) Output

| Type | Format |
|------|--------|
| MRSinMRS | `.csv` |
| Pipeline | `.pipe` |
| MRS Time Domain Data | `.raw` `.nii` |
| Time Data & Spectra Figures | `.pdf` |
| LCModel Output | `.coord`, `.ps`, `.table`, `.csv` |
| Analysis Report | `.html` |
