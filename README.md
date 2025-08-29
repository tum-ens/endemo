# EnDeMo v3.0.0

The module calculates the forecast energy demand for a defined  geographical area. The result output includes the energy-related sectors (households; industry; traffic; commerce, trade and services).   

Note: This is a public version. The majority of the input data and output results are exemplary and are provided solely for the purpose of demonstrating the model's functionality. They should not be used for planning or analytical purposes.

## Features
...

## Documentation

The documentation of the source code can be found locally in folder docs/_build/html/index.html
Please open with it within a browser. 

Creating a bookmark within the browser can help you find the documentation more quickly when used often.

## Installation

### Git installation (developers only)
If you intend to further develop the software, please install the git version control system first. In Linux distributions, git can be installed via the package manager. For Windows, go to http://git-scm.com/. Remark: At step "Adjusting your PATH environment", select "Run Git from the Windows Command Prompt".

Then, in a directory of your choice, clone this repository by:
`git clone https://github.com/AmaduEpishev1/endemov3.0.0.git`

A better way to clone repositories is to use a password-protected SSH key. See the [Github documentation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) on how to add an SSH key to your account.

Continue at “Installation of endemo” below.

### Download (users only)
If you do not intend to further develop the software, pick the [latest release](https://github.com/AmaduEpishev1/endemov3.0.0.git) and download the zip file.

### Installation of endemo
We recommend using the Python distribution Anaconda or Mamba. If you don't want  to use it or already have an existing Python (version 3.10 recommended) installation, you can also download the required packages by yourself.

#### Anaconda/Mamba (recommended)

1. **[Anaconda (Python 3)](http://continuum.io/downloads)/[Mamba](https://github.com/conda-forge/miniforge#mambaforge)** Choose the 64-bit installer if possible.
   During the installation procedure, keep both checkboxes "modify PATH"  and "register Python" selected! If only higher Python versions are  available, you can switch to a specific Python Version by typing `conda install python=<version>`
2. Packages
   1. Download the environment file endemo-env.yml.
   2. Launch a new command prompt (Windows: Win+R, type "cmd", Enter / Linux: CTRL+Alt+T)
   3. Install it via conda or mamba by `conda env create -f endemo-env.yml`
   4. Install per terminal additional packages: `pip install brotli==1.1.0 dash==2.7.0 dash-bootstrap-components==1.4.1 flask==2.3.3 importlib-metadata==8.7.0 narwhals==1.37.1 plotly==6.0.1 typing-extensions==4.0.0 werkzeug==2.3.7 xlsxwriter==3.2.0 zstandard==0.23.0`
   5. Each time you open a new terminal for running endemo, you can activate the environment by `conda activate endemo2`.
   6. At first run, you may have to init conda or mamba by running `conda init`


#### Manually (the hard way)

For all packages, best take the latest release or release  candidate version. Both 32 bit and 64 bit versions work, though 64 bit  is recommended. The list of packages can be found in the environment file endemo-env.yml.

<a name="get-started"></a>
## Get started

After installation, got to the directory you downloaded or cloned endemo into and execute the script main.py by using the following on the command prompt (Windows) or Terminal (Linux) : python main.py.

The results will be stored in the folder output.

