# python-2d-game

This is a simple 2D action RPG game that lets you control a character and fight against 
different monsters, using potions and abilities to your advantage.

#### In-game footage (YouTube):

[![in-game footage](https://img.youtube.com/vi/4FijOSF_O6o/0.jpg)](https://www.youtube.com/watch?v=4FijOSF_O6o)

#### Screenshots:

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/gameplay.png" height="300" />
<br/>

_Choose your hero:_

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/heroes.png" height="300" />
<br/>


_Master different abilities:_

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/abilities.png" height="300" />
<br/>

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/abilities_2.png" height="300" />
<br/>

_Equip powerful items:_

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/items.png" height="300" />
<br/>

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/items_2.png" height="300" />
<br/>

_Customize your character with talents:_

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/talents.png" height="300" />
<br/>

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/talents_2.png" height="300" />
<br/>

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/talents_3.png" height="300" />
<br/>


_Interact with NPCs:_

<img src="https://github.com/JonathanMurray/python-2d-game/blob/master/screenshots/dialog.png" height="300" />
<br/>


## Installation

This project targets **Python 3.14** and uses
[pygame-ce 2.5.8](https://pypi.org/project/pygame-ce/2.5.8/), which provides
Python 3.14 wheels for Windows, macOS, and Linux. pygame-ce is the community
edition of pygame; the code still uses `import pygame`.

Create a fresh virtual environment with Python 3.14. Existing Python 3.6
environments must be recreated, and `pygame` and `pygame-ce` must not be
installed together because they provide the same module.

Linux / macOS:
```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):
```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Playing the game

Simply run
```
python run.py
```

Use `python run.py --disable-fullscreen` for a window instead of fullscreen.
The older `--disable_fullscreen` spelling also works. If no audio device is
available, the game warns once at startup and continues without sound.

Images, fonts, sounds, and maps are resolved relative to the project (or the
packaged executable's bundled resources), so launching with an absolute script
path from another directory also works. Character saves remain in
`saved_characters/` under the current working directory, using the existing
JSON format. Launch from the same directory to keep using your existing saves.

## Generating an executable file
To generate an executable that can be run without having Python installed,
run these commands from the project root in the activated environment:
```sh
python -m pip install -r requirements-build.txt
python -m PyInstaller run.spec
```
The build requires PyInstaller 6.16 or newer for Python 3.14. Distribute the
entire `dist/run/` directory, which includes the game's resources. Launch
`dist/run/run` on Linux/macOS or `dist\run\run.exe` on Windows. Build on each
target operating system; PyInstaller does not cross-compile.

## Launching the map editor

Simply run
```
python map_editor.py
```
or to edit a specific map
```
python map_editor.py --map test.json
```

## Gameplay basics

* Use arrow keys to move
* Use keys shown in UI to use abilities and consumables
* Use spacebar to interact with NPCs and other entities in the environment
* Press 'Enter' to pause the game
* Press 'S' to save your progress

### Advanced usage
To play a specific map, run
```
python run.py --map test.json
```

or with a specific hero
```
python run.py --hero MAGE
python run.py --hero ROGUE
python run.py --hero WARRIOR
```

To start the game without it being fullscreen, run
```
python run.py --disable-fullscreen
```

There may be more flags to use for debugging purposes.

## Verification

Run the integration tests in the Python 3.14 environment:
```sh
python -m unittest discover -s tests -v
```

Tests use SDL's dummy video/audio drivers, so they work without a display or
speakers. They exercise real asset loading and rendering, hero movement and
abilities, pause/resume, fullscreen switching, save loading (including older
JSON files), map editing, map serialization, and dungeon generation. Each
scenario runs in a temporary directory to isolate saves and check resource
paths. GitHub Actions runs the suite on Linux, Windows, and macOS.

## Profiling the game:
To profile the game code, run:
```
./profile_game.sh
```
You will be running the game through `cProfiler`, and when you're done
stats will be printed and saved to a file.
