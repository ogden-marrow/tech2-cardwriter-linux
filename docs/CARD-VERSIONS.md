# Tech 2 card versions (Saab)

A Tech 2 PCMCIA card is a **linear flash** card that holds the diagnostic
software for one or more car families. Card Writer does not create card
software; it copies an existing **`.bin` image** onto a card.

The table below is the Saab set published by
[Tech2Wiki](https://tech2wiki.com/content/tech2_pcmcia/available_tech2_.bin-files/tech2_saab.html)
(CC0). Sizes are the actual image sizes: 10 MB images are for 10 MB cards,
32 MB images for 32 MB cards. A 10 MB image **cannot** be written to a 32 MB
card and vice versa.

## Version table

| Version | Size | Covers | Languages | Notes |
|---|---:|---|---|---|
| **v148.000** | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010 | 13 languages | **Newest general 32 MB release.** Recommended for a 1999–2010 9-5. |
| v147.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010 | 13 languages | Previous release; keep as a fallback. |
| v146.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010 | 13 languages | |
| v145.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2011, 9-5 (9600) 1998–2010 | 13 languages | |
| v144.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2010, 9-5 (9600) 1998–2010 | 13 languages | |
| v143.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2010, 9-5 (9600) 1998–2010 | English only | English-only build. |
| v136.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2009, 9-5 (9600) 1998–2009 | 13 languages | |
| v135.000 | 32 MB | 9-3 (9400) 1998–2003, 9-3 Sport (9440) 2003–2008, 9-5 (9600) 1998–2008 | 13 languages | |
| **v44.000** | **10 MB** | Saab 900 1990–1998, 9000 1988–1998 | 13 languages | **Different card size (10 MB).** Not for the 9-5. |
| v2.000 | 32 MB | Saab 9-3 diagnostics | many | Special 9-3 DTC build (C0131 08 and C0252 ESP). Not the general 9-5 card. |

The 13 languages are: Chinese (Simplified and Traditional), German, English,
Spanish, Finnish, French, Italian, Japanese, Korean, Dutch, Russian, Swedish
and Thai. v143.000 is English only.

## Which one should I use?

**Saab 9-5, 1999–2010 → v148.000 (32 MB).** It is the newest general release
and covers the whole 9-5 (9600) range. Use a **32 MB** PCMCIA card.

**Saab 900 / 9000 → v44.000 (10 MB).** It will not fit a 32 MB card, so keep a
10 MB card for these cars if you work on them.

If you are chasing a specific 9-3 ESP fault, the v2.000 image is a targeted
9-3 build, not a substitute for v148.000 on a 9-5.

## What the app validates

When you choose a `.bin` file, Tech2 Card Writer checks it before enabling
**Launch Card Writer**:

1. **Header** — the first four bytes must be `T2  ` (the letters `T2` followed
   by two spaces). Files without it are rejected as "not a Tech 2 card image".
2. **Size** — the file must be exactly **10 MiB** or **32 MiB**.
3. **Version hint** — a two- or three-digit number in the filename (for example
   `148` in `saab_148.000.bin`) is matched against the table above.
4. **Consistency** — the app warns if the version looks like a 10 MB image but
   the file is 32 MB, if v44.000 is selected while the car is set to 9-5, if
   v143.000 (English only) is selected, or if a 32 MB-only image is used.

The checks are a safety net, not a signature check: a file can have a valid
header and size and still be damaged. Write only images you trust.

## Where to get images

The repository **ships no `.bin` files** and no Card Writer binaries. Card
images are copyrighted by Saab/GM and must be obtained by the user from their
own Tech 2 media, TIS2000 installation, or the Tech2Wiki archive:

- [Available Tech 2 .bin files — SAAB](https://tech2wiki.com/content/tech2_pcmcia/available_tech2_.bin-files/tech2_saab.html)
- [Writing PCMCIA using Tech 2 Card Writer](https://tech2wiki.com/content/tech2_pcmcia/writing_pcmcia_cards/writing_pcmcia_using_tech2_card_writer.html)

Keep a copy of every image you write. A card can be rewritten, but the image
is your only source.
