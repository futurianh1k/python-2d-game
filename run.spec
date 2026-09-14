# -*- mode: python ; coding: utf-8 -*-

a = Analysis(['run.py'],
             pathex=[],
             binaries=[],
             datas=[('resources','resources')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='run',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='run')
