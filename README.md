# USB Hub Port Controller

This project provides a Python interface for controlling the state of StarTech Managed USB hubs through the provided CUSBC.exe from StarTech

Supported AFAIK: 
- 5G4AINDRM-USB-A-HUB 
- 5G7AINDRM-USB-A-HUB (never tested but it should work) 

## Features
- Set port states using bit-mapped (`B`) or hexadecimal (`H`) formats
- Convert hex-encoded port states into boolean lists
- Execute commands through the system interface

## Installation
- Ensure Python 3 is installed (I'm on 3.12.4?)
- Clone the repo
- No requirements, pure python

```sh
git clone https://github.com/shanedertrain/cusbc.git
cd cusbc
