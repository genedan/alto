"""The audio engine's less common paths: far notes, fades, errors and a sequence that is replaced while it waits."""

from __future__ import annotations

import wave
from typing import TYPE_CHECKING, Never

import pytest
from alto.audio import INSTRUMENT_BY_KEY, Sounds
from alto.theory.pitch import Note

if TYPE_CHECKING:
    from pathlib import Path

    from PySide6.QtMultimedia import QSoundEffect
    from PySide6.QtWidgets import QApplication


class Effect:
    """Stands in for QSoundEffect."""

    def __init__(
        self,
        playing: bool = False,
        *,
        loading: bool = False,
    ) -> None:
        """
        Build the effect.

        Parameters
        ----------
        playing : bool
            Whether it is playing at first.
        loading : bool
            Whether it is still loading.
        """
        self.playing, self.loading, self.volume_set, self.stopped = playing, loading, [], 0

    def isPlaying(self) -> bool:
        """
        Say whether the effect is playing.

        Returns
        -------
        bool
            The playing flag.
        """
        return self.playing

    def setVolume(self, v: float) -> None:
        """
        Record a volume that was set.

        Parameters
        ----------
        v : float
            The volume.
        """
        self.volume_set.append(v)

    def volume(self) -> float:
        """
        Return the volume.

        Returns
        -------
        float
            Always 1.0.
        """
        return 1.0

    def play(self) -> None:
        """
        Start playing.
        """
        self.playing = True

    def stop(self) -> None:
        """
        Stop playing, and count the stop.
        """
        self.stopped += 1
        self.playing = False

    def status(self) -> QSoundEffect.Status:
        """
        Return the loading status.

        Returns
        -------
        QSoundEffect.Status
            Loading while the loading flag is set, otherwise Ready.
        """
        from PySide6.QtMultimedia import QSoundEffect

        return QSoundEffect.Status.Loading if self.loading else QSoundEffect.Status.Ready


def test_a_piano_note_far_outside_the_recordings_is_synthesized(tmp_path: Path) -> None:
    """
    Check that a piano note far outside the recordings is synthesized.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    s = Sounds()
    s._dir = tmp_path
    piano = INSTRUMENT_BY_KEY["piano"]
    path = s._note_file(piano, midi=max(s.recordings(piano)) + 6)  # well above the highest recording
    assert path.exists()
    with wave.open(str(path)) as w:
        assert w.getnchannels() == 1 and w.getnframes() > 1000


def test_another_instrument_shifts_the_nearest_recording(tmp_path: Path) -> None:
    """
    Check that another instrument shifts the nearest recording.

    Parameters
    ----------
    tmp_path : Path
        A scratch folder unique to this test.
    """
    s = Sounds()
    s._dir = tmp_path
    inst = INSTRUMENT_BY_KEY["viola_plucked"]
    missing = next(m for m in range(48, 90) if m not in s.recordings(inst))  # a note between the recorded ones
    assert s._note_file(inst, midi=missing).exists()


def test_a_released_note_fades_out_and_stops(app: QApplication) -> None:
    """
    Check that a released note fades out and stops.

    Parameters
    ----------
    app : QApplication
        The shared Qt application.
    """
    from PySide6.QtMultimedia import QSoundEffect
    from PySide6.QtTest import QTest

    s = Sounds()
    fx = QSoundEffect()
    s._release(fx)
    assert id(fx) in s._fades
    QTest.qWait(s.FADE_MS + 150)
    assert fx.volume() == pytest.approx(0.0, abs=0.01)


def test_playing_a_note_again_cancels_its_fade() -> None:
    """
    Check that playing a note again cancels its fade.
    """
    s = Sounds()
    fx = Effect()
    stopped = []

    class Fade:
        """
        A fade-out that records when it is stopped.
        """

        def stop(self) -> None:
            """
            Record that the fade was cancelled.
            """
            stopped.append(1)

    s._effects[("viola_bowed", 60)] = fx
    s._fades[id(fx)] = Fade()
    s.play_midi(60, instrument="viola_bowed")
    assert stopped == [1] and fx.playing and id(fx) not in s._fades


def test_stop_all_silences_what_is_playing_and_cancels_fades() -> None:
    """
    Check that stop all silences what is playing and cancels fades.
    """
    s = Sounds()
    quiet, loud = Effect(), Effect(playing=True)
    s._effects = {("piano", 60): quiet, ("piano", 62): loud}
    cancelled = []

    class Fade:
        """
        A fade-out that records when it is cancelled.
        """

        def stop(self) -> None:
            """
            Record that the fade was cancelled.
            """
            cancelled.append(1)

    s._fades = {1: Fade(), 2: Fade()}
    s._sounding = [loud]
    s.stop_all()
    assert cancelled == [1, 1] and s._fades == {} and s._sounding == []
    assert loud.stopped == 1 and loud.volume_set == [0.0] and quiet.stopped == 0


def test_a_failure_in_the_sound_system_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    Check that a failure in the sound system is reported not raised.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    capsys : pytest.CaptureFixture[str]
        Captures what the test prints.
    """
    s = Sounds()

    def broken(
        inst: str,
        midi: int,
    ) -> Never:
        """
        Fail as a machine with no sound card would.

        Raises
        ------
        RuntimeError
            Always.

        Parameters
        ----------
        inst : str
            The instrument.
        midi : int
            The note.
        """
        raise RuntimeError("no sound card")

    monkeypatch.setattr(s, "_effect", broken)
    s.play_midi(60)
    s.play_notes([[Note(4, letter=0)]])
    s.preview("piano", midis=(60,))
    assert capsys.readouterr().out.count("audio unavailable: no sound card") == 3


def test_an_unknown_instrument_is_reported_not_raised(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Check that an unknown instrument is reported not raised.

    Parameters
    ----------
    capsys : pytest.CaptureFixture[str]
        Captures what the test prints.
    """
    Sounds().preview("no-such-instrument", midis=(60,))
    assert "audio unavailable" in capsys.readouterr().out


def test_a_sequence_waiting_for_its_notes_to_load_gives_way_to_a_newer_one(
    monkeypatch: pytest.MonkeyPatch,
    app: QApplication,
) -> None:
    """
    Check that a sequence waiting for its notes to load gives way to a newer one.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Replaces settings, functions or attributes for the length of the test.
    app : QApplication
        The shared Qt application.
    """
    from PySide6.QtTest import QTest

    s = Sounds()
    slow, ready = Effect(loading=True), Effect()
    played = []
    monkeypatch.setattr(s, "play_midi", lambda midi, *a, **k: played.append(midi))
    monkeypatch.setattr(s, "_effect", lambda inst, midi: slow if midi == 60 else ready)
    s.play_notes([[Note(4, letter=0)]])  # waits, because note 60 is still loading
    s.play_notes([[Note(4, letter=1)]])  # replaces it
    QTest.qWait(150)
    assert played == [62]  # the first one gave up without playing
    slow.loading = False
