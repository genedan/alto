import os
from pathlib import Path
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    if "ALTO_TRIAL_LOG" in os.environ:
        from PySide6.QtCore import QCoreApplication, QTimer
        from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
        from alto.audio import Sounds, INSTRUMENT_BY_KEY
        import ctypes, time

        log = Path(os.environ["ALTO_TRIAL_LOG"])
        def record(value):
            with log.open("a") as f:
                print(value, file=f)
        app = QCoreApplication([])
        devices = QMediaDevices.audioOutputs()
        record([d.description() for d in devices])
        if not devices:
            raise SystemExit(4)
        sounds = Sounds()
        effect = sounds._effect(INSTRUMENT_BY_KEY["piano"], midi=60)
        effect.setMuted(True)
        started = []
        def status():
            record(effect.status().name)
            if effect.status() == QSoundEffect.Status.Ready:
                effect.play()
            elif effect.status() == QSoundEffect.Status.Error:
                app.exit(3)
        def playing():
            if effect.isPlaying():
                started.append(time.monotonic())
            elif started:
                elapsed = time.monotonic()-started[0]
                record(f"Playback completed in {elapsed:.2f}s")
                dlls = ["ffmpegmediaplugin.dll","avcodec-63.dll","avformat-63.dll","avutil-61.dll"]
                loaded = [name for name in dlls if ctypes.windll.kernel32.GetModuleHandleW(name)]
                record(f"Loaded FFmpeg libraries: {loaded}")
                app.exit(0 if elapsed > .2 and not loaded else 5)
        effect.statusChanged.connect(status)
        effect.playingChanged.connect(playing)
        QTimer.singleShot(0, status)
        QTimer.singleShot(12000,lambda:app.exit(2))
        raise SystemExit(app.exec())
    from alto.__main__ import main
    raise SystemExit(main())
