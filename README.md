# Course Checker

A script that automatically checks for available seats in full university courses that use the Banner registration system. When a seat becomes available in a monitored course, the script sends an email notification and exits.

## Features

* **Automated checking**: Runs at a configurable interval to check for open seats.

* **Email notifications**: Sends an email alert immediately when a spot opens up.

* **SMS notifications**: Sends an SMS alert using public email to SMS gateways.

* **Multi-course support**: Monitor multiple courses at once.

* **Configurable**: Easily adapt to different universities by changing URLs in the config file.

* **Lightweight**: Uses direct API calls which are fast and reliable.

* **Debug mode**: Includes a debug flag for verbose logging and testing email settings.

## Setup

Follow these steps to get the script running.

### 1. Prerequisites

* Python 3.6+

* `pip` for installing packages

### 2. Installation

Clone this repository or download the files to your server or local machine.

```
git clone <your-repository-url>
cd <repository-directory>
```

### 3. Create a virtual environment

It's highly recommended to use a virtual environment to manage dependencies.


##### Create the environment

```
python3 -m venv venv
```

##### Activate it (Linux/macOS)

```
source venv/bin/activate
```

##### Activate it (Windows)

```
.\venv\Scripts\activate
```

### 4. Install dependencies

```
pip install requests
```

### 5. Configure the script

Follow the example config file `config.json` and edit it with your specific details.

**term_id** can usually be acquired via /StudentRegistrationSsb/ssb/classSearch/getTerms?offset=1&max=10 

**sender_password**: you will need to generate an app password in gmail. It will be shown to you with spaces for readability, but enter it without spaces in the config. Instructions on how to do that can be found [here](https://support.google.com/accounts/answer/185833).

**sms_gateway_email**: you can leave this blank if you don't want to receive SMS notifications. If your carrier has an email to SMS gateway, use that address. For a list of gateways, check [here](https://email2sms.info/).

**intervals**: be mindful and respectful. Choose appropriate intervals and don't hammer your university's servers with requests. They will block this method and you otherwise.

## Usage

Once configured, you can run the script from your terminal.

### Standard run

```
python class-search.py
```

The script will run continuously, checking courses at the intervals defined in `config.json`. Once **any** of the courses is found to have an open seat, the script will send an email (and SMS if configured) and exit. You will have to then adjust your config and restart the script to monitor any other courses. Run it in tmux or screen for best results.

### Debug mode

```
python class-search.py --debug
```

Run in debug mode to get detailed output and to test your email setup.

## Disclaimer

This script is for personal use only. Use it responsibly and be mindful of the frequency of your requests to avoid overloading your university's servers. The author is not responsible for any misuse.

