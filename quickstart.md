# /IOTCONNECT AWS IoT Greengrass (Nucleus Classic) Snap QuickStart

This guide walks you through installing the **iotconnect-gg-nucleus** snap on Ubuntu Core and onboarding a Greengrass **Nucleus Classic** device using an /IOTCONNECT connection kit. It also highlights the value each platform adds to the other.

## Why Greengrass + /IOTCONNECT

**Greengrass value for /IOTCONNECT users**
- Run local compute, filtering, and routing so devices keep working even when the cloud is intermittent.
- Deploy components over the air without hand-building fleet automation.
- Support for multi-protocol device data ingestion at the edge.

**/IOTCONNECT value for Greengrass (console-only) users**
- Streamlined device provisioning and certificate management without manual AWS Console steps.
- Device templates, bulk onboarding, and visual dashboards in one place.
- Simplified Greengrass component packaging and deployments from a unified UI.

## Requirements

### Hardware
- An Ubuntu Core device (Raspberry Pi, Intel NUC, etc.) with network access

### Software
- /IOTCONNECT account with AWS backend
- SSH or console access to the device
- `snapd` available on the target device (standard on Ubuntu Core)

## 1. Create the Greengrass Device in /IOTCONNECT

These steps are the same as other /IOTCONNECT Greengrass guides **except you will choose _Nucleus Classic_** (not Nucleus Lite).

<img src="https://github.com/user-attachments/assets/2d0e2dbd-f867-4933-84a5-337cce94c10f" width="900" alt="IOTCONNECT Greengrass device creation overview" />

1. Log in to /IOTCONNECT at `console.iotconnect.io`.
2. Go to **Device -> Greengrass Device -> Template** and import the template you use for Greengrass (for example, the `all-apps-device-template.json` used in other Greengrass demos).
   <img width="1017" alt="click_templates" src="https://github.com/user-attachments/assets/e20ee569-38a1-4da6-bce1-08c66169774a" />
   <img width="326" height="227" alt="click_create_template" src="https://github.com/user-attachments/assets/6c6c3e4d-49fb-4cef-83ef-4a9a46f7adeb" />
3. Go to **Devices** and click **Create Device**.
   <img width="1011" height="73" alt="click_devices" src="https://github.com/user-attachments/assets/fcea8f0c-f412-4ad2-a0c1-c172ca30ef1d" />
   <img width="471" height="211" alt="click_create_device" src="https://github.com/user-attachments/assets/e57d01b4-bb59-43c1-a926-cf862195b071" />
4. Enter a **Unique ID** and **Device Name** (they must match; keep it under 14 chars).
5. Select your **Entity** and **Template**.
6. For **Device Type**, select **Nucleus Classic**.
7. Click **Save & View**.
8. Download the **Connection Kit** from the device page and save it as `connectionKit.zip`.
   <img width="380" height="180" alt="connection_kit" src="https://github.com/user-attachments/assets/ab693911-aebe-4916-b85d-9d734d067a46" />

## 2. Install the Snap on the Device

From the device shell:

```bash
sudo snap install iotconnect-gg-nucleus
```

If you are **side-loading** the snap, install with:

```bash
sudo snap install --dangerous ./iotconnect-gg-nucleus_<version>_<arch>.snap
./connect.sh
```

## 3. Copy the Connection Kit to the Device

From your host machine, copy the connection kit to the device (replace `x.x.x.x`):

```bash
scp connectionKit.zip ubuntu@x.x.x.x:
```

## 4. Onboard Greengrass Using the Connection Kit

The snap uses the bundled setup script to extract the connection kit and generate a resolved Greengrass config. Run this on the device:

```bash
sudo snap run iotconnect-gg-nucleus.configure --connection-kit ~/connectionKit.zip
```

The snap’s configure app runs the same script in `local-scripts/iot-greengrass-setup.py`, so the behavior matches local/test usage.

### What the script does with the connection kit

The connection kit contains these files:
- `config.yaml`
- `device.pem.crt` (device certificate)
- `private.pem.key` (device key)
- `AmazonRootCA1.pem` (root CA)

The setup script:
- Extracts the kit into `/var/snap/iotconnect-gg-nucleus/common/greengrass/v2/connection-kit`.
- Updates the `config.yaml` paths to point at the extracted certificate/key/CA.
- Writes the resolved config to `/var/snap/iotconnect-gg-nucleus/common/greengrass/v2/config.yaml`.
- Installs and starts Greengrass Nucleus Classic using the resolved configuration.

If you ever need to re-run onboarding, re-run the same command.

## 5. Verify Greengrass is Running

```bash
snap logs iotconnect-gg-nucleus.greengrass-daemon -f
```

Greengrass files and logs live in:

```
/var/snap/iotconnect-gg-nucleus/common/greengrass/v2
```

## 6. Next Steps

- Deploy Greengrass components from /IOTCONNECT.
- Use /IOTCONNECT dashboards to visualize and interact with device data.

## Resources

- /IOTCONNECT Greengrass demos (Nucleus Lite reference):
  `https://github.com/avnet-iotconnect/iotc-python-greengrass-demos/tree/main/stm32mp135f-dk`
