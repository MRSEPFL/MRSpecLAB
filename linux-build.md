## Guide for building Linux executable on Ubuntu
- Make sure `tk-dev` is installed **before** installing Python, as MRSinMRS.py depends on it (even though no tkinter window is opened...):
```sh
sudo apt update
sudo apt install tk-dev
```
- Install `python3.10` for best compatibility; this must be done from the deadsnakes repository, as the Ubuntu package manager only maintains the latest one. The first command ensures the `add-apt-repository` exists:
```sh
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv
```
- To be safe regarding the tkinter install, create a virtual environment using the full path to `/usr/bin/python3.10`; also clone this repository:
```sh
/usr/bin/python3.10 -m venv venv_mrs
git clone https://github.com/MRSEPFL/MRspecLAB.git
```
- Install wxPython from the wxPython repository URL, as the version on pip requires building from source, which is long and can be hard to set up. **Do not change `22.04` to `24.04`**; gsnodegraph enforces wxPython version 4.2.1 specifically, which was not specially built for 24.04. You can use `20.04` if you have an older Ubuntu version:
```sh
../venv_mrs/bin/python3.10 -m pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04 wxPython==4.2.1
```
- The wxPython version defaults to the `libtiff.so.5` binary when built in a portable environment, but Ubuntu 24.04 uses `libtiff.so.6`. Ensure the availability of version 5 using the following commands ([source](https://askubuntu.com/questions/1540324/libtiff5-removed-after-ubuntu-24-04-installation-how-to-install-again)); this creates `.deb` files in the working directory, which can be deleted once both commands succeed:
```sh
wget http://security.ubuntu.com/ubuntu/pool/main/t/tiff/libtiff5_4.3.0-6ubuntu0.10_amd64.deb http://mirrors.kernel.org/ubuntu/pool/main/t/tiff/libtiffxx5_4.3.0-6ubuntu0.10_amd64.deb http://security.ubuntu.com/ubuntu/pool/main/t/tiff/libtiff5-dev_4.3.0-6ubuntu0.10_amd64.deb
sudo apt install ./libtiff5_4.3.0-6ubuntu0.10_amd64.deb ./libtiffxx5_4.3.0-6ubuntu0.10_amd64.deb ./libtiff5-dev_4.3.0-6ubuntu0.10_amd64.deb 
```
- Install the remaining Python requirements as usual, as well as `pyinstaller` required to create the executable file:
```sh
cd MRspecLAB
../venv_mrs/bin/python3.10 -m pip install -r requirements.txt
../venv_mrs/bin/python3.10 -m pip install pyinstaller
```
- You can finally run the build command, and run the executable to test it:
```sh
../venv_mrs/bin/python3.10 pyinstaller.py
./dist/MRSpecLAB
```