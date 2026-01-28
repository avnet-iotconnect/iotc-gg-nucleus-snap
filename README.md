# Greengrass (Nucleus Classic) Ubuntu Core Snap Packages

This repository contains the Greengrass v2 Nucleus Classic Snap packages for Ubuntu Core.
The primary Snapcraft project is at the repository root (`snapcraft.yaml`). The per-architecture
folders (`amd64/`, `arm64/`, `armhf/`, `riscv64/`) are kept for reference and legacy local builds.

For end-to-end onboarding instructions, see `quickstart.md`.

## Upstream AWS snap and differences

This snap is derived from the original AWS Greengrass snap project in the AWS Greengrass GitHub organization and includes their work with modifications. See `LICENSE` and `NOTICE` for full attribution and terms.

Key differences in the /IOTCONNECT version:
- Adds an interactive `/IOTCONNECT` onboarding flow to provision Greengrass using an /IOTCONNECT connection kit.
- Bundles the `/IOTCONNECT` setup script used by `iotconnect-gg-nucleus.configure`.
- Focuses on /IOTCONNECT-backed workflows and documentation (see `quickstart.md`).

If you are looking for the original AWS snap, refer to the upstream repository: `https://github.com/aws-greengrass/aws-greengrass-snap`.

## Attribution

This project includes work derived from Amazon Web Services. See `LICENSE` and `NOTICE` for full terms and attribution.

- arm64 package tested on Raspberry Pi Zero 2W running Ubuntu Core 22 from Raspberry Pi Imager
- amd64 tested on Intel NUC N150 running generic Ubuntu Core 24 image from Canonical
- armhf and riscv64 builds are included but not yet validated

## Notes on base and architectures

The root `snapcraft.yaml` uses `core22` for multi-architecture remote builds. If you publish multiple architectures
under the same snap name, each arch gets its own build/revision in the Snap Store.

## Building the snap

Install Snapcraft

```bash
sudo snap install snapcraft
```

Install necessary tools

```bash
sudo apt install findutils python3-dev python3-venv wget
```
For a local build, run Snapcraft from the repository root (where `snapcraft.yaml` lives):

```bash
cd /home/mlamp/dev/edge/greengrass/aws-greengrass-snap
snapcraft
```

For remote builds (Launchpad), run from the repository root:

```bash
snapcraft remote-build --launchpad-accept-public-upload
```

To build a single architecture (for example amd64), add `--build-for=amd64`.

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
