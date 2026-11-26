"""Record the headset microphone and turn Persian speech into text.

Capture polls the stream at normal priority. A Python callback on the audio
thread runs at high priority and makes the mouse stutter, so that path is not
used. WASAPI shared mode is the same input Chrome uses. Phrases are sent to
the Persian (fa-IR) speech service while the microphone stays open.

The device list is read again each time listening starts. This process starts
at login, and PortAudio would otherwise keep the USB microphone that existed
before the headset connected.
"""

from __future__ import annotations

import base64
import ctypes
import io
import json
import math
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

# Key shipped in Chromium for short dictation. Not a private credential.
_GOOGLE_SPEECH_URL = "https://www.google.com/speech-api/v2/recognize"
_TARGET_RATE = 16000

# Voice activity. A short pause ends a phrase and types it. It does not end the session.
_SPEECH_RMS = 0.012
_PARTIAL_FIRST_S = 0.7
_PARTIAL_EVERY_S = 1.2
# A breath between words is shorter than this, so a sentence is sent whole.
# Cut into single words, the recognizer has no context and guesses worse.
_COMMIT_SILENCE_S = 0.7
_MIN_SPEECH_S = 0.28
_MAX_UTTERANCE_S = 12.0
_SESSION_MAX_S = 600.0
# The quiet end of a word (the "-neh" of گرونه, a trailing n or vowel) is
# below _SPEECH_RMS, so it counts as silence. Trimming that "silence" cut the
# word itself: گرونه arrived as گرو. Keep the whole pause before a commit.
_TAIL_KEEP_S = 0.7
# After stop, keep reading this long. The last word is often still being
# spoken when the button is pressed, and WASAPI holds audio not yet read.
_STOP_TAIL_S = 0.6
# The last phrase is kept even when shorter than _MIN_SPEECH_S.
_MIN_FINAL_SPEECH_S = 0.1
# Audio kept from before the first loud sound of a phrase. The first phrase of
# a session keeps everything since the mic opened: a Bluetooth headset ramps
# its level up, so a soft first word (این) stays under _SPEECH_RMS and was lost.
_FIRST_PREROLL_S = 3.0
_PREROLL_S = 0.5
# A mic that sends nothing this long is reported instead of waiting forever.
_NO_AUDIO_S = 5.0


class SpeechError(Exception):
    """A problem the UI can show as a status line."""


_KEY_FILE = Path(__file__).resolve().parent / "data" / "speech_key.txt"
# Chromium's public key for its web speech service. It is not tied to any
# user's account, and it is the same default the open-source SpeechRecognition
# library ships for recognize_google(). Built in so the mic works right after
# installing. See README, "Speech key".
_DEFAULT_SPEECH_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"


def _speech_key() -> str:
    """GOOGLE_SPEECH_KEY, else data/speech_key.txt, else the built-in default."""
    key = os.environ.get("GOOGLE_SPEECH_KEY", "").strip()
    if not key and _KEY_FILE.is_file():
        try:
            key = _KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            key = ""
    return key or _DEFAULT_SPEECH_KEY


def probe_microphone() -> str:
    """Open and close the headset input. Used to log the real device at startup."""
    _init_audio_thread()
    try:
        stream, rate, name = _open_capture()
    except SpeechError as ex:
        return f"Microphone probe failed: {ex}"
    try:
        _close_capture(stream)
    except Exception as ex:
        return f"Microphone probe failed on {name}: {type(ex).__name__}: {ex}"
    return f"Microphone ready: {name} @ {rate} Hz"


def listen_persian(stop_event: threading.Event, on_partial, on_phrase, on_started=None) -> str:
    """Keep listening until stop_event. Type phrases while the mic stays open.

    on_partial(text) is the current phrase as it grows.
    on_phrase(text) is a finished phrase (a short pause, or the mic stopping).
    on_started(name) runs once the headset really sends sound, so the user
    knows when to talk. Opening a Bluetooth headset takes about a second.
    Returns a note when the session hits its time limit, otherwise "".
    """
    _lower_thread_priority()
    # Unbounded: recognition requests block this loop for a second or more, and
    # a full queue used to stall the capture thread (dropping audio) and make it
    # discard a block at stop to fit the end marker.
    audio_q: queue.Queue = queue.Queue()
    ready = threading.Event()
    start_error: list[BaseException] = []
    meta: dict[str, int | str] = {"rate": _TARGET_RATE}

    def capture() -> None:
        _lower_thread_priority()
        _init_audio_thread()
        stream = None
        try:
            stream, rate, name = _open_capture()
            meta["rate"] = rate
            meta["name"] = name
            ready.set()
            frames = max(800, int(rate) // 10)
            announced = False
            while not stop_event.is_set():
                block = _poll_read(stream, frames, stop_event, _NO_AUDIO_S)
                if block is None:
                    if stop_event.is_set():
                        break
                    raise SpeechError(
                        f"{name} sends no sound. Take the headset out of its case or "
                        "reconnect it, then press the mic again."
                    )
                audio_q.put(block)
                # A Bluetooth link first delivers exact zeros while it connects.
                if not announced and np.any(block):
                    announced = True
                    if on_started is not None:
                        try:
                            on_started(name)
                        except Exception:
                            pass
            _read_stop_tail(stream, frames, audio_q)
        except Exception as ex:
            start_error.append(ex)
            ready.set()
        finally:
            if stream is not None:
                try:
                    _close_capture(stream)
                except Exception:
                    pass
            audio_q.put(None)

    threading.Thread(target=capture, name="finglish-mic", daemon=True).start()
    if not ready.wait(8):
        stop_event.set()
        raise SpeechError("Microphone could not start.")
    if start_error and audio_q.empty():
        raise _as_speech_error(start_error[0])

    rate = int(meta["rate"])
    gate = _UtteranceGate(rate)
    session_peak = 0.0
    delivered = False
    last_error: SpeechError | None = None
    started = time.monotonic()
    timed_out = False

    def recognize(pcm: np.ndarray, kind: str) -> None:
        nonlocal delivered, last_error
        if pcm.size < int(rate * 0.2):
            if kind == "commit":
                on_phrase("")
            return
        try:
            text = transcribe_persian(_wav_bytes(_to_16k_mono(pcm, rate), _TARGET_RATE))
        except SpeechError as ex:
            last_error = ex
            text = ""
        if kind == "partial":
            if text:
                on_partial(text)
            return
        if text:
            delivered = True
        on_phrase(text)

    want_partial = False
    while True:
        if not timed_out and time.monotonic() - started >= _SESSION_MAX_S:
            timed_out = True
            stop_event.set()
        block = audio_q.get()
        if block is None:
            break
        session_peak = max(session_peak, float(np.max(np.abs(block))) if block.size else 0.0)
        if stop_event.is_set():
            gate.closing = True
        for kind, pcm in gate.push(block):
            if kind == "partial":
                want_partial = True
                continue
            # A commit replaces the phrase's partial, so an older partial is moot.
            want_partial = False
            recognize(pcm, kind)
        # Send a partial only once caught up, on the newest audio of the open
        # phrase. Audio that piled up during a request is not re-sent stale.
        # After stop only the final phrases matter.
        if want_partial and (stop_event.is_set() or audio_q.empty()):
            want_partial = False
            if not stop_event.is_set():
                pcm = gate.snapshot()
                if pcm.size:
                    recognize(pcm, "partial")

    for _kind, pcm in gate.flush():
        recognize(pcm, "commit")

    if start_error and not delivered:
        raise _as_speech_error(start_error[0])
    if start_error and delivered:
        return f"Microphone stopped ({start_error[0]}). The Persian already heard is kept."
    if not delivered and session_peak < 0.008:
        raise SpeechError(
            "The microphone stayed silent. Unmute the headset mic, speak closer, and press the button again."
        )
    if not delivered and last_error is not None:
        raise last_error
    if timed_out:
        return "The microphone turned off after 10 minutes. Press it again to keep going."
    return ""


def transcribe_persian(wav_bytes: bytes) -> str:
    """Return the Persian transcript, or an empty string when nothing was heard."""
    pcm, rate = _wav_pcm(wav_bytes)
    if rate <= 0 or len(pcm) < int(rate * 2 * 0.25):
        raise SpeechError("The recording was too short. Speak, then keep going.")

    cloud_key = _cloud_key()
    if cloud_key:
        return _recognize_cloud(pcm, rate, cloud_key)

    url = f"{_GOOGLE_SPEECH_URL}?client=chromium&lang=fa-IR&key={_speech_key()}"
    request = urllib.request.Request(
        url,
        data=pcm,
        headers={"Content-Type": f"audio/l16; rate={rate}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        raise SpeechError(
            f"Google's free speech service refused the request (HTTP {ex.code}). "
            "If this keeps happening, add your own Google Cloud key (see README)."
        ) from ex
    except urllib.error.URLError as ex:
        raise SpeechError("Persian speech recognition needs an internet connection.") from ex
    return _transcripts(body)


# Your own Google Cloud key, for when the free endpoint is restricted or off.
# When set, it is used instead of the free endpoint. See README, "Using your own
# Google Cloud key".
_CLOUD_URL = "https://speech.googleapis.com/v1/speech:recognize"
_CLOUD_KEY_FILE = Path(__file__).resolve().parent / "data" / "google_cloud_key.txt"


def _cloud_key() -> str:
    """GOOGLE_CLOUD_SPEECH_KEY, else data/google_cloud_key.txt, else ""."""
    key = os.environ.get("GOOGLE_CLOUD_SPEECH_KEY", "").strip()
    if not key and _CLOUD_KEY_FILE.is_file():
        try:
            key = _CLOUD_KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            key = ""
    return key


def _recognize_cloud(pcm: bytes, rate: int, key: str) -> str:
    """Google Cloud Speech-to-Text v1, synchronous recognize, fa-IR."""
    payload = json.dumps(
        {
            "config": {
                "encoding": "LINEAR16",
                "sampleRateHertz": int(rate),
                "languageCode": "fa-IR",
                "enableAutomaticPunctuation": False,
            },
            "audio": {"content": base64.b64encode(pcm).decode("ascii")},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{_CLOUD_URL}?key={urllib.parse.quote(key, safe='')}",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as ex:
        try:
            detail = json.loads(ex.read().decode("utf-8", "replace"))["error"]["message"]
        except Exception:
            detail = f"HTTP {ex.code}"
        raise SpeechError(f"Your Google Cloud key was refused: {detail[:160]}") from ex
    except urllib.error.URLError as ex:
        raise SpeechError("Persian speech recognition needs an internet connection.") from ex
    except ValueError as ex:
        raise SpeechError("Google Cloud sent an answer that could not be read.") from ex
    parts = []
    for result in body.get("results") or []:
        alternatives = result.get("alternatives") or []
        text = (alternatives[0].get("transcript") or "").strip() if alternatives else ""
        if text:
            parts.append(text)
    return " ".join(parts).strip()


class _UtteranceGate:
    """Split a stream into a growing phrase and a committed phrase.

    A pause commits the phrase. It does not mean the microphone should close.
    """

    def __init__(self, rate: int):
        self.rate = max(1, int(rate))
        self._preroll: list[np.ndarray] = []
        self._preroll_n = 0
        self._preroll_limit = int(_FIRST_PREROLL_S * self.rate)
        self._parts: list[np.ndarray] = []
        self._speech_s = 0.0
        self._silence_s = 0.0
        self._since_partial_s = 0.0
        self._heard = False
        self._partial_sent = False
        # Set once stop is pressed: a short last word is kept, not dropped as noise.
        self.closing = False

    def push(self, block: np.ndarray) -> list[tuple[str, np.ndarray]]:
        if block.size == 0:
            return []
        dur = block.size / self.rate
        rms = _rms(block)
        voiced = rms >= _SPEECH_RMS
        if not self._heard:
            self._remember_preroll(block)
            if not voiced:
                return []
            self._heard = True
            self._parts = list(self._preroll)
            self._preroll = []
            self._preroll_n = 0
            self._preroll_limit = int(_PREROLL_S * self.rate)
            self._speech_s = dur
            self._silence_s = 0.0
            self._since_partial_s = dur
            self._partial_sent = False
            return self._events_for_speech()

        self._parts.append(block)
        if not voiced:
            self._silence_s += dur
            if self._silence_s < _COMMIT_SILENCE_S:
                return []
            return self._commit_or_drop()

        self._speech_s += dur
        self._silence_s = 0.0
        self._since_partial_s += dur
        return self._events_for_speech()

    def flush(self) -> list[tuple[str, np.ndarray]]:
        if not self._heard or not self._parts:
            self._reset_open()
            return []
        return self._commit_or_drop(_MIN_FINAL_SPEECH_S)

    def snapshot(self) -> np.ndarray:
        """The open phrase so far, without closing it."""
        if not self._heard:
            return np.zeros(0, dtype=np.float32)
        return self._audio_view()

    def _events_for_speech(self) -> list[tuple[str, np.ndarray]]:
        if self._speech_s >= _MAX_UTTERANCE_S:
            audio = self._take_audio()
            self._reset_open()
            return [("commit", audio)] if audio.size else []
        first = (not self._partial_sent) and self._speech_s >= _PARTIAL_FIRST_S
        again = self._partial_sent and self._since_partial_s >= _PARTIAL_EVERY_S
        if not (first or again):
            return []
        self._partial_sent = True
        self._since_partial_s = 0.0
        audio = self._audio_view()
        return [("partial", audio)] if audio.size else []

    def _commit_or_drop(self, min_speech_s: float = _MIN_SPEECH_S) -> list[tuple[str, np.ndarray]]:
        if self.closing:
            min_speech_s = min(min_speech_s, _MIN_FINAL_SPEECH_S)
        if self._speech_s < min_speech_s:
            self._reset_open()
            self._parts = []
            return []
        audio = self._take_audio()
        self._reset_open()
        return [("commit", audio)] if audio.size else []

    def _remember_preroll(self, block: np.ndarray) -> None:
        self._preroll.append(block)
        self._preroll_n += int(block.size)
        while self._preroll and self._preroll_n - int(self._preroll[0].size) >= self._preroll_limit:
            self._preroll_n -= int(self._preroll[0].size)
            self._preroll.pop(0)

    def _audio_view(self) -> np.ndarray:
        if not self._parts:
            return np.zeros(0, dtype=np.float32)
        audio = self._parts[0] if len(self._parts) == 1 else np.concatenate(self._parts)
        if self._silence_s > _TAIL_KEEP_S and audio.size:
            drop = int((self._silence_s - _TAIL_KEEP_S) * self.rate)
            if 0 < drop < audio.size:
                audio = audio[:-drop]
        return audio

    def _take_audio(self) -> np.ndarray:
        audio = self._audio_view()
        self._parts = []
        return audio

    def _reset_open(self) -> None:
        self._heard = False
        self._speech_s = 0.0
        self._silence_s = 0.0
        self._since_partial_s = 0.0
        self._partial_sent = False
        self._parts = []


def _poll_read(stream, frames: int, stop_event: threading.Event, timeout_s: float):
    """One block of audio, or None on stop or when the mic sends nothing.

    A blocking read waits forever when a Bluetooth headset is connected but
    silent (in its case, or still switching modes), and then stop never ends.
    """
    # WASAPI reports one packet (about 20 ms) as available, not all buffered
    # audio, so a block is gathered packet by packet. Reading at most what is
    # available never blocks.
    deadline = time.monotonic() + timeout_s
    chunks: list[np.ndarray] = []
    got = 0
    while got < frames:
        avail = int(stream.read_available)
        if avail > 0:
            data, _overflowed = stream.read(min(avail, frames - got))
            chunk = np.array(data[:, 0], dtype=np.float32, copy=True)
            chunks.append(chunk)
            got += chunk.size
            deadline = time.monotonic() + timeout_s
            continue
        if stop_event.is_set() or time.monotonic() >= deadline:
            break
        time.sleep(0.005)
    if not chunks:
        return None
    return chunks[0] if len(chunks) == 1 else np.concatenate(chunks)


def _read_stop_tail(stream, frames: int, audio_q: queue.Queue) -> None:
    """Keep the audio around the stop press instead of closing it away."""
    try:
        tail_end = time.monotonic() + _STOP_TAIL_S
        never = threading.Event()
        while time.monotonic() < tail_end:
            block = _poll_read(stream, frames, never, max(0.0, tail_end - time.monotonic()))
            if block is None:
                break
            audio_q.put(block)
        pending = int(stream.read_available)
        if pending > 0:
            data, _overflowed = stream.read(pending)
            audio_q.put(np.array(data[:, 0], dtype=np.float32, copy=True))
    except Exception:
        # The phrases already captured are still recognized.
        pass


def _as_speech_error(ex: BaseException) -> SpeechError:
    if isinstance(ex, SpeechError):
        return ex
    return SpeechError(f"Microphone could not start: {ex}")


def _lower_thread_priority() -> None:
    """Keep capture off the priority the mouse and cursor need."""
    try:
        kernel = ctypes.windll.kernel32
        kernel.SetThreadPriority(kernel.GetCurrentThread(), -1)  # THREAD_PRIORITY_BELOW_NORMAL
    except Exception:
        pass


def _init_audio_thread() -> None:
    """WASAPI capture needs COM initialized on the recording thread."""
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 0)  # COINIT_MULTITHREADED
    except Exception:
        pass


# A headset wins over the Windows default. After a restart that default is
# often a silent USB endpoint that enumerated before the headset connected.
_HEADSET_MARKERS = (
    "kopfhörer",
    "kopfhorer",
    "headset",
    "headphone",
    "hands-free",
    "earfun",
    "airpod",
)
# Guards PortAudio set-up and tear-down. Restarting PortAudio (to see a newly
# connected headset) while another stream is still open or closing corrupted
# the heap: pressing the mic during the start-up probe crashed the app, and
# the window was left on "Working...". So streams open and close under this
# lock, and PortAudio is only restarted when no stream is open.
_PA_LOCK = threading.Lock()
_open_streams = 0


def _is_headset(name: str) -> bool:
    folded = name.casefold()
    plain = folded.replace("ö", "o").replace("ä", "a").replace("ü", "u")
    return any(marker in folded or marker in plain for marker in _HEADSET_MARKERS)


def _rank_inputs(found: list[tuple[int, int, str, bool]]) -> list[tuple[int, int, str]]:
    """Headset first. Within a group, the Windows default comes first."""
    ordered = sorted(
        found,
        key=lambda item: (
            0 if _is_headset(item[2]) else 1,
            0 if item[3] else 1,
            item[2].casefold(),
        ),
    )
    return [(idx, rate, name) for idx, rate, name, _default in ordered]


def _refresh_portaudio() -> None:
    """PortAudio keeps the device list from the first import until restarted."""
    if getattr(sd, "_initialized", 0):
        try:
            sd._terminate()
        except Exception:
            pass
    try:
        sd._initialize()
    except Exception:
        pass


def _capture_candidates(refresh: bool = True) -> list[tuple[int, int, str]]:
    if refresh:
        _refresh_portaudio()
    hostapis = list(sd.query_hostapis())
    devices = list(sd.query_devices())
    wasapi_index = None
    default_index = -1
    for index, api in enumerate(hostapis):
        if "WASAPI" not in str(api["name"]).upper():
            continue
        wasapi_index = index
        default_index = int(api["default_input_device"])
        break
    if wasapi_index is None:
        info = sd.query_devices(kind="input")
        return [(int(info["index"]), int(info["default_samplerate"]), str(info["name"]))]
    found: list[tuple[int, int, str, bool]] = []
    for idx, info in enumerate(devices):
        if int(info["hostapi"]) != wasapi_index or int(info["max_input_channels"]) < 1:
            continue
        found.append(
            (idx, int(info["default_samplerate"]), str(info["name"]), idx == default_index)
        )
    ranked = _rank_inputs(found)
    if not ranked:
        raise SpeechError("No microphone was found.")
    return ranked


def _open_capture():
    """Shared-mode WASAPI input. Prefer the headset, then 16 kHz."""
    global _open_streams
    with _PA_LOCK:
        candidates = _capture_candidates(refresh=_open_streams == 0)
        errors: list[str] = []
        for device, native_rate, name in candidates:
            try:
                opened = _open_one(device, native_rate, name)
            except SpeechError as ex:
                errors.append(str(ex))
                continue
            _open_streams += 1
            return opened
        detail = errors[-1] if errors else "no input device"
        raise SpeechError(detail)


def _close_capture(stream) -> None:
    """Stop and close a stream from _open_capture, never during a restart."""
    global _open_streams
    with _PA_LOCK:
        try:
            stream.stop()
        except Exception:
            pass
        try:
            stream.close()
        finally:
            _open_streams = max(0, _open_streams - 1)


def _open_one(device: int, native_rate: int, name: str):
    try:
        wasapi = sd.WasapiSettings(exclusive=False, auto_convert=True)
    except Exception:
        wasapi = None
    rates: list[int] = []
    for rate in (16000, int(native_rate)):
        if rate > 0 and rate not in rates:
            rates.append(rate)
    errors: list[str] = []
    attempts: list[tuple[int, object]] = [(rate, wasapi) for rate in rates]
    attempts.append((int(native_rate), None))
    for rate, extra in attempts:
        kwargs = {
            "device": device,
            "samplerate": rate,
            "channels": 1,
            "dtype": "float32",
            "latency": "high",
        }
        if extra is not None:
            kwargs["extra_settings"] = extra
        stream = None
        try:
            stream = sd.InputStream(**kwargs)
            stream.start()
            return stream, rate, name
        except Exception as ex:
            errors.append(f"{rate} Hz: {ex}")
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass
    detail = errors[-1] if errors else "no input device"
    raise SpeechError(f"Microphone could not start ({name}): {detail}")


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    energy = float(np.dot(samples, samples))
    if energy <= 0.0:
        return 0.0
    return math.sqrt(energy / samples.size)


def _to_16k_mono(samples: np.ndarray, source_rate: int) -> np.ndarray:
    if source_rate <= 0:
        source_rate = _TARGET_RATE
    if source_rate != _TARGET_RATE and samples.size:
        count = max(1, int(round(samples.size * _TARGET_RATE / source_rate)))
        index = (np.arange(count) * (source_rate / _TARGET_RATE)).astype(np.int64)
        index = np.clip(index, 0, samples.size - 1)
        samples = samples[index]
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16)


def _wav_bytes(pcm: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return buf.getvalue()


def _wav_pcm(wav_bytes: bytes) -> tuple[bytes, int]:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as src:
            rate = src.getframerate()
            channels = src.getnchannels()
            width = src.getsampwidth()
            frames = src.readframes(src.getnframes())
    except wave.Error as ex:
        raise SpeechError("The recording could not be read.") from ex
    if channels != 1 or width != 2:
        raise SpeechError("The recording format was not accepted.")
    return frames, rate


def _transcripts(body: str) -> str:
    parts: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        for result in payload.get("result") or []:
            alternatives = result.get("alternative") or []
            if not alternatives:
                continue
            text = (alternatives[0].get("transcript") or "").strip()
            if text:
                parts.append(text)
    return " ".join(parts).strip()
