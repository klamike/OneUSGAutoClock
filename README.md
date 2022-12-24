# OneUSGAutoClock

Functionally this script is almost the same as [Shaun-Regenbaum/OneUSGAutomaticClock](https://github.com/Shaun-Regenbaum/OneUSGAutomaticClock) except:
- This version can be run on a headless Raspberry Pi so you don't need to keep your computer on all day
- This version relies on external management of `chromedriver`
- This version has [healthchecks.io](https://healthchecks.io) integration for success/failure pinging and [touchbar status](https://github.com/klamike/btt-healthchecks).
- This version supports multiple jobs (see also the [onejob](https://github.com/klamike/OneUSGAutoClock/tree/onejob) branch)

### USE AT YOUR OWN RISK
___

## Installation

1. Clone this repo
    - `git clone https://github.com/klamike/OneUSGAutoClock.git`
2. Install dependencies
    - [Python 3.9](https://www.python.org/downloads/)
    - [chromedriver](https://chromedriver.chromium.org)
      - `sudo apt install chromium-chromedriver` on Raspberry Pi
      - `brew install chromedriver` on MacOS
    - [selenium](https://pypi.org/project/selenium/), [rich](https://github.com/Textualize/rich) using `pip install selenium rich`
3. Set environment variables
    - Edit `config_example.py` with your information and rename it to `config.py`
4. Run the script using `python oneusg.py`

___

## Usage

### CLI usage

1. Run the script using `python oneusg.py`
   - If you need to stop the script early, make sure to manually clock out.
   - If you want to close your SSH connection and keep the script running you can use `nohup`/`screen`/`tmux`
