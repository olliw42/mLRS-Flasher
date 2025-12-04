<p align="left"><a href="https://raw.githubusercontent.com/olliw42/mLRS-docu/main/logos/mLRS_logo_long_w_slogan_1280x768.png"><img src="https://raw.githubusercontent.com/olliw42/mLRS-docu/main/logos/mLRS_logo_long_w_slogan_1280x768.png" align="center" height="153" width="256" ></a>

# mLRS Flasher Desktop App #

Link to the [mLRS project](https://github.com/olliw42/mLRS).


## Installation ##

### Windows ###

mLRSFlasher is based on Python, and thus needs a full Python3 installation on your system. Not very Win-like, we know, and we appologize for this. 

- Install Python3 on your system, if you don't yet have it. Ensure that Python is in the PATH (the usual Python installation tutorials tell how to check that).
- Download the github repo and ensure you have unpacked it if you downloaded it as zip.
- Install dependencies by running `pip install -r requirements.txt`
    - You will need "pillow", "requests", "pyserial", "customtkinter", "tk", "pymavlink"
- Run the mLRS_Flasher.py script.
    - ***Note***: mLRS_Flasher needs the rights to write to disk and modify files on disk.

### MacOS ###

#### Run the Flasher ####

````
./run_mLRS_Flasher_mac.sh
````

### Linux ###

TBD


## Disclaimer ##

You of course use the app fully at your own risk.


