# Greengrass (Nucleus Classic) Ubuntu Core Snap Packages

These folders contain the Greengrass v2 Nucleus Classic Snap packages for Ubuntu Core

## Attribution

This project includes work derived from Amazon Web Services. See `LICENSE` and `NOTICE` for full terms and attribution.

- arm64 package tested on Raspberry Pi Zero 2W running Ubuntu Core 22 from Raspberry Pi Imager
- amd64 tested on Intel NUC N150 running generic Ubuntu Core 24 image from Canonical
- armhf and riscv64 builds are included but not yet validated

## Notes on base per architecture

This snap is built and published per-architecture. The current bases are:
- amd64: core24
- arm64: core22
- armhf: core22
- riscv64: core22

If you publish multiple architectures under the same snap name, each arch gets its own build/revision in the Snap Store.

## Building the snap

Install Snapcraft

```bash
sudo snap install snapcraft
```

Install necessary tools

```bash
sudo apt install findutils python3-dev python3-venv wget
```
Create a new folder in your home folder (e.g. `/home/user/mysnaps/iotconnect-gg-nucleus`)

Change to the folder you just created and initialize snapcraft

```bash
mkdir -p ~/mysnaps/iotconnect-gg-nucleus
cd ~/mysnaps/iotconnect-gg-nucleus
snapcraft init
```

Copy all files from the `amd64`, `arm64`, `armhf`, or `riscv64` directory in this repository to your local machine. The `snapcraft init` command from the previous step creates a default `snapcraft.yaml` file - replace that default file with the one in this repository.

```bash
cp -r  ~/git/aws-greengrass-snap/amd64/* ~/mysnaps/iotconnect-gg-nucleus
```

Run the following script to build the new snap

```bash
./build.sh
```

## Installation

If publishing to the Snap Store, install with:

```bash
sudo snap install iotconnect-gg-nucleus
```

For a local build, copy the *.snap package to the device (use SCP) and execute installation:

```bash
sudo snap install --dangerous ./iotconnect-gg-nucleus_<version>_<arch>.snap
```

Once installed successfully, configure Greengrass using the following commands:

```bash
./connect.sh
sudo iotconnect-gg-nucleus.configure
```

The `connect.sh` script connects the installed Greengrass package to the Ubuntu Core slots that are not connected by default. (should not be needed once published to Snap store)

The `sudo iotconnect-gg-nucleus.configure` command prompts for the following information;
- AWS Access Key
- AWS Secret Access Key
- AWS Region
- Device Name (for IoT Core Thing and Greengrass Core Device name)

The Access Key/Secret Access Key corresponds to an IAM user with sufficient privileges to install and connect an IoT Thing to IoT Core, including provisioning certificates, and creating the Greengrass Core device.

## Running and managing the snap

By default, the Greengrass daemon is started automatically after install. You can manage it with:

```bash
sudo snap start iotconnect-gg-nucleus.greengrass-daemon
sudo snap stop iotconnect-gg-nucleus.greengrass-daemon
sudo snap restart iotconnect-gg-nucleus.greengrass-daemon
```

To re-run the interactive setup at any time:

```bash
sudo snap run iotconnect-gg-nucleus.configure
```

View logs:

```bash
snap logs iotconnect-gg-nucleus.greengrass-daemon -f
```

Greengrass files and logs live under:

```
/var/snap/iotconnect-gg-nucleus/common/greengrass/v2
```

If you side-load the snap, you may need to manually connect these interfaces (the `connect.sh` script does this):

```bash
sudo snap connect iotconnect-gg-nucleus:hardware-observe
sudo snap connect iotconnect-gg-nucleus:home
sudo snap connect iotconnect-gg-nucleus:system-observe
sudo snap connect iotconnect-gg-nucleus:mount-observe
sudo snap connect iotconnect-gg-nucleus:process-control
```

To remove the snap and all data:

```bash
sudo snap remove --purge iotconnect-gg-nucleus
```

## NOTES

- The package assumes that the role alias `GreengrassV2TokenExchangeRoleAlias` already exists and this should refer to a suitable IAM role.
- Docker integration is included so the Docker snap must be installed (`snap install docker`) on the build machine to build successfully.
- Some Python libraries are included in the snap such as boto3 and awsiotsdk.  Further validation should be done on what should/should not be included
