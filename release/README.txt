FIRE EMBLEM: THREE HOUSES - PLAYSTATION BUTTON PROMPTS
=======================================================

Replaces the Nintendo button icons with PlayStation icons: Cross, Circle,
Square, Triangle, L1/R1, L2/R2, Options and Share/Create. Covers:

- the prompt bar and menu icons
- the inventory and status tab badges (ZL/ZR/L/R become L2/R2/L1/R1)
- button names in Guide pages, tutorials and help text, in all 12 game
  languages ("press the A Button" now shows the Circle icon)

Made for game version 1.2.0 (the final update). Tested on yuzu. Other Switch
emulators with mod support (Ryujinx, Eden, Citron, Sudachi and similar)
should work but have not been tested.


WHAT'S IN THE ARCHIVE
---------------------

PS Prompts Installer.bat               installs, switches or removes the mod for you
Circle confirms (emulator default)\    5 styles, for setups where Circle confirms
Cross confirms (remapped)\             the same 5 styles, for setups where Cross confirms

Use ONE style folder. Each one is a complete mod (about 220 MB once installed).

The archive is a .7z because the 10 versions share almost all their data:
packed together they take a fraction of the space. Open it with 7-Zip
(free, 7-zip.org), WinRAR, or Windows 11's built-in extractor.


WHICH BUTTON STYLE?
-------------------

  DualSense          Pale buttons with the symbol cut out, matching the game's
                     own icon style. Options shows three bars, Create shows
                     the Create button's rays.

  DS4 Light, Label   Pale buttons with coloured symbols (green Triangle,
                     red Circle, pink Square, blue Cross). Share and Options
                     are shown as word labels.
  DS4 Light, Pill    The same, with Share and Options shown as the word above
                     a small pill-shaped button.
  DS4 Dark, Label    Dark buttons with a light rim and coloured symbols,
                     like a real DualShock 4. L1/R1/L2/R2 and Share/Options
                     are dark too.
  DS4 Dark, Pill     The same, with pill-style Share and Options.

On every style: L = L1, R = R1, ZL = L2, ZR = R2, + = Options, - = Share/Create.
In the text of the DS4 styles, Options and Share are written as words: their
icons are too small to read at text size.


CROSS OR CIRCLE?
----------------

The mod only changes the icons. Which button confirms is set by your
emulator's controller mapping. Pick the set that matches it:

  Circle confirms    Emulators map a PlayStation pad by position by default,
                     so Circle (right) does what Switch A does.
                     Use "Circle confirms (emulator default)".
  Cross confirms     If you swapped A and B so that Cross does what Switch A
                     does, use "Cross confirms (remapped)".

The two sets differ only in Cross and Circle. Triangle and Square stay the
same in both (Triangle = Switch X, Square = Switch Y).

Not sure? Open a menu and press Cross. If that selects, use the Cross set.
If it backs out, use the Circle set.

To make Cross confirm, swap A and B in the emulator's controller settings
(yuzu: Emulation > Configure > Controls; Ryujinx: Options > Settings > Input):
      A = Cross     B = Circle     (leave X = Triangle, Y = Square)
Save each mapping as a controller profile to switch between them later.


INSTALL WITH THE INSTALLER (EASIEST)
------------------------------------

1. Close the game.
2. Extract the whole archive anywhere.
3. Double-click "PS Prompts Installer.bat" in the extracted folder.
4. Pick your emulator, the button style, and Circle or Cross, then click
   Install.
5. Make sure the mod is ticked in the game's Add-ons / Mods list
   (yuzu: right-click the game > Properties > Add-Ons), then start the game.

The installer finds yuzu, Ryujinx, suyu, Sudachi, Citron and Eden in their
usual places. For a portable emulator, click Browse and pick the folder
the emulator opens with "Open Mod Data Location" for Three Houses.

To switch styles, run it again and install another style: it removes the old
one first, so only one is ever installed. To uninstall, run it and click
Remove. It only creates or deletes folders named "PS Prompts - ..." and
never touches anything else.

If Windows warns about the file, choose "More info" > "Run anyway". The
installer is a plain PowerShell script ("PS Prompts Installer.ps1"), so you
can open it in Notepad and read exactly what it does.


INSTALL BY HAND
---------------

1. Close the game.
2. Extract the archive anywhere.
3. In the emulator, right-click Fire Emblem: Three Houses and choose
   "Open Mod Data Location" (the wording varies by emulator).
4. Copy ONE style folder there, for example
       "PS Prompts - DS4 Dark, Pill [Circle]"
   (copy the folder itself, not the "Circle confirms..." folder above it).
5. Make sure the mod is ticked in the game's Add-ons / Mods list
   (yuzu: right-click the game > Properties > Add-Ons), then start the game.

The folder must end up as <mod data location>\PS Prompts - ...\romfs\...


SWITCHING STYLES
----------------

Only one PS Prompts mod may be on at a time: they replace the same files.
With the installer, just install the new style. By hand: untick the old one
and tick the new one in Add-ons / Mods, then start the game. You can keep several style folders installed and switch with the ticks.
Emulators tick new mods automatically, so check that only one is ticked.


REMOVING
--------

Run the installer and click Remove. By hand: close the game and delete the
mod folder from the mod data location, or just untick it. Nothing else is changed. Saves and controller settings are untouched.


COMPATIBILITY AND LIMITS
------------------------

- Requires game version 1.2.0. Other versions are not supported.
- Conflicts with other mods that replace the game's file list
  (romfs\patch4\INFO0.bin), which includes most mods that change text or
  textures this way. Only one such mod can be active unless they are merged.
- Also replaces the English and other-language text files (msgdata,
  scrdata, tuscrdata) and the icon textures. Text mods and fan
  translations that replace those files will conflict.
- Not replaced: the SL/SR, HOME and Capture icons (a PlayStation pad has no
  equivalent), the stick icons, and anything drawn into tutorial pictures.
- Three Houses has no controller-layout screen, so unlike the Fortune's
  Weave version there is no controller-picture add-on.


CREDITS
-------

- Idea and approach: Fire Emblem XBOX UI Project by YamadaAsaemonGurei.
- L1/R1/L2/R2 and SHARE/OPTIONS lettering: Bahnschrift. Inventory tab
  labels: Palatino Linotype Bold, matching the game's own lettering.

Unofficial fan modification. Not affiliated with Nintendo, Intelligent Systems,
Koei Tecmo or Sony Interactive Entertainment.
