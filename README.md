[![image](https://github.com/user-attachments/assets/18f9149c-1511-449d-87f5-c326037c501c)](https://zenodo.org/records/14866163?preview=1)

SIMPLE DOWNLOAD AND DOUBLE-CLICK APPLICATION FOR WINDOWS USERS TO PROCESS MRS(I) DATA.

--> source code available for other OS.

The MRspecLAB platform is closely described in this publication: [PUBLICATION](insert link).

A detailed user manual can be found in [MANUAL.md](/MANUAL.md).

# MRSpecLAB
MRSpecLAB is a graphical platform for the processing and analysis of magnetic resonance spectroscopy data, focusing on user-friendliness, automated use and modularity. Currently supported and tested formats are DICOM and Twix files for Siemens, .SDAT .SPAR for Philips, and NIFTI.
If you have data in another data format, we, for now, recommend converting it to NIFTI using the [spec2nii](https://github.com/wtclarke/spec2nii) package.

## Installation and usage

### Windows Executable
A Windows executable file (.exe) is available and can be run directly after downloading the .rar package. Place the zipped folder in your desired directory, unpack it, find the .exe file and double-click it. Depending on your setup the first time opening the program might take 1-2 min. 

- Currently this executable only contains the default processing nodes and does not retrieve any new ones from the github repository. If you desire to use your self-written processing nodes, or nodes written by other users, you can simply place the python script in the 'customer_nodes' folder of your toolbox folder and rerun the .exe file.

- Process your data in four simple steps:
  1) Load your data in the left data boxes (metabolite on top and water on the bottom (optional))
  2) look at the provided processing pipeline and alternate if desired by clicking on the colorful chain icon on top
  3) Input your .basis set and LCModel .control file by clicking the 'fitting options' button on top
  4) Click the run button (either step-by-step [left] or in one go [right])

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
MRspecLAB is released under the Apache 2.0 license.

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
      We acknowledges the support of the <a href="https://www.snf.ch/en">Swiss National Science Foundation </a>, the  <a href="https://epfl.ch">École Polytechnique Fédérale de Lausanne</a>, in Lausanne, Switzerland, and the <a href="https://cibm.ch">CIBM Center for Biomedical Imaging</a>, in Switzerland.
    </td>
  </tr>
</table>
