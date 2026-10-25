# Hardware guide

Tech2 Card Writer is only the Linux-side front-end. The actual writing is done
by the original Windows **Card Writer** program talking to a **Tech 2** over a
serial cable, with a PCMCIA card in the Tech 2. This page covers the parts you
need and the ones you must not use.

## What you need

### Tech 2

A genuine or clone **Tech 2** diagnostic unit with the PCMCIA slot and an
RS-232 port. The Tech 2 must be able to boot to its welcome screen; the card
writer uses the Tech 2's own card programming mode.

### PCMCIA card

A **linear flash** PCMCIA card, either:

- **10 MB** for 10 MB images (Saab v44.000, 900/9000), or
- **32 MB** for 32 MB images (Saab v135.000–v148.000).

Use the card size that matches the image. Card Writer overwrites the whole
card, so a card that already contains software is fine.

### 12 V power supply

A **stable 12 V DC supply** for the Tech 2 — the Tech 2's own mains adapter is
ideal. Do not rely on a bench supply that may be turned off, and do not power
the Tech 2 from the car during a write. A 32 MB write takes roughly **15
minutes**, and an interrupted write can leave the card unusable until it is
rewritten.

### RS-232 connection

The Tech 2 side uses its **RS-232 port** (the DB9 connector on the Tech 2).
On the Linux side you need a serial port:

- **USB-to-serial adapter (recommended)** — FTDI-based adapters are the most
  reliable; CH340/CP210x generally work. Avoid adapters that only expose a
  fake/limited UART.
- **Built-in serial port** — if your machine still has one, it appears as
  `/dev/ttyS*`.

Use the serial cable specified for the Tech 2's RS-232 port — normally the
cable supplied with the Tech 2 kit. Generic straight-through and null-modem
cables are not interchangeable; if you are making your own, verify the pinout
on Tech2Wiki before connecting it. See Tech2Wiki's
[USB-to-serial compatibility list](https://tech2wiki.com/content/tech2/tech2_using/connecting_to_techline/usb-to-serial/usb2serial_working.html)
and
[power supplies and cables](https://tech2wiki.com/content/tech2/tech2_kit/tech2_power_supplies_and_cables.html).

### CANdi (conditionally)

**CANdi is only for 9-5 from model year 2006 onward.** For those cars, CANdi
is needed for CAN-based modules. Use it only when the car and procedure call
for it.

> **Do not use CANdi on 2005 and older Saab 9-5/9-3 cars.** Saab's release
> notes are explicit that CANdi is not for the older vehicles; the older cars
> use the standard OBD connector and protocols.

Never connect or disconnect CANdi while a card write is in progress. Card
writing itself does not use CANdi — it talks to the Tech 2 over RS-232 — but
the same Tech 2 is used for vehicle diagnostics, so keep the two activities
separate.

## How the pieces connect

```
Linux PC                 Tech 2                     Car (diagnostics only)
┌──────────┐  USB   ┌──────────────┐
│ USB port ├────────┤ USB-to-serial│
│          │        │ adapter      │
│          │  DB9   │              │
│          ├────────┤ RS-232 port  │
└──────────┘        │              │
                    │ PCMCIA slot  │◄── card image is written here
                    │ 12 V DC in   │
                    └──────────────┘
```

During a card write the car is **not connected**. Card writing happens on the
bench: PC ↔ serial adapter ↔ Tech 2 ↔ PCMCIA card.

## Serial device names

The app scans for:

- `/dev/ttyUSB*` — most USB-to-serial adapters
- `/dev/ttyACM*` — CDC-ACM adapters
- `/dev/ttyS*` — built-in serial ports

Your user must be able to read and write the device. On most distributions
that means belonging to the `dialout` group:

```bash
sudo usermod -aG dialout "$USER"
# log out and back in, or run: newgrp dialout
```

On Arch/Fedora the group may be `uucp` instead. Check with:

```bash
ls -l /dev/ttyUSB0
```

## Cards, slots and adapters

The Tech 2 PCMCIA slot takes **Type I/II linear flash** cards. Some cheap
"PCMCIA" cards are ATA/CompactFlash adapters and will **not** work — Card
Writer needs true linear flash. The PCMCIA kit and card compatibility are
documented on Tech2Wiki:

- [Tech 2 PCMCIA kit](https://tech2wiki.com/content/tech2/tech2_kit/tech2_pcmcia.html)
- [Linear flash card compatibility](https://tech2wiki.com/content/tech2_pcmcia/linear_flash_compatibility/linear_flash_cards.html)
- [Working PCMCIA hardware configurations](https://tech2wiki.com/content/tech2_pcmcia/pcmcia_slot_compatibility/working_hardware_configurations.html)