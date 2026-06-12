import os
import struct
import wave
import math
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

import database


SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")


def _ensure_sounds_dir():
    os.makedirs(SOUNDS_DIR, exist_ok=True)


def _generate_wav(filepath, frequency, duration_ms, volume=0.5):
    sample_rate = 44100
    num_samples = int(sample_rate * duration_ms / 1000)
    data = []
    for i in range(num_samples):
        t = i / sample_rate
        env = min(1.0, min(i, num_samples - i) / (sample_rate * 0.01))
        val = volume * env * math.sin(2 * math.pi * frequency * t)
        data.append(int(val * 32767))
    with wave.open(filepath, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(data)}h", *data))


def generate_default_sounds():
    _ensure_sounds_dir()
    sounds = {
        "default.wav": (880, 300),
        "chime.wav": (523, 800),
        "ding.wav": (1047, 200),
        "alert.wav": (660, 500),
        "gentle.wav": (440, 600),
    }
    for name, (freq, dur) in sounds.items():
        path = os.path.join(SOUNDS_DIR, name)
        if not os.path.exists(path):
            _generate_wav(path, freq, dur)
    return SOUNDS_DIR


class AudioManager(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = None
        self._tts_available = False
        self._init_tts()
        generate_default_sounds()

    def _init_tts(self):
        try:
            from PyQt6.QtTextToSpeech import QTextToSpeech
            self._tts_available = True
        except ImportError:
            self._tts_available = False

    def play_sound(self, sound_type="default", sound_file=None, volume=80):
        try:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
        except ImportError:
            return
        if self._player is None:
            self._player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(volume / 100.0)
        url = None
        if sound_file and os.path.isfile(sound_file):
            url = QUrl.fromLocalFile(os.path.abspath(sound_file))
        else:
            sound_map = {
                "default": "default.wav",
                "chime": "chime.wav",
                "ding": "ding.wav",
                "alert": "alert.wav",
                "gentle": "gentle.wav",
            }
            fname = sound_map.get(sound_type, "default.wav")
            fpath = os.path.join(SOUNDS_DIR, fname)
            if os.path.exists(fpath):
                url = QUrl.fromLocalFile(fpath)
        if url:
            self._player.setSource(url)
            self._player.play()

    def speak(self, text):
        if not self._tts_available:
            return
        try:
            from PyQt6.QtTextToSpeech import QTextToSpeech
            tts = QTextToSpeech(self)
            tts.say(text)
        except Exception:
            pass

    def get_available_sounds(self):
        sounds = ["default", "chime", "ding", "alert", "gentle"]
        result = []
        for s in sounds:
            path = os.path.join(SOUNDS_DIR, f"{s}.wav")
            if os.path.exists(path):
                result.append(s)
        return result


class FocusModeManager(QObject):
    focus_mode_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._enabled = False
        self._start_time = ""
        self._end_time = ""
        self._whitelist_fullscreen = True
        self._load_settings()

    def _load_settings(self):
        self._enabled = database.get_setting("focus_mode_enabled", "0") == "1"
        self._start_time = database.get_setting("focus_mode_start", "")
        self._end_time = database.get_setting("focus_mode_end", "")
        self._whitelist_fullscreen = database.get_setting("whitelist_fullscreen", "1") == "1"

    def is_active(self):
        if not self._enabled:
            return False
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        if self._start_time and self._end_time:
            if self._start_time <= current_time < self._end_time:
                return True
            return False
        return self._enabled

    def set_enabled(self, enabled):
        self._enabled = enabled
        database.set_setting("focus_mode_enabled", "1" if enabled else "0")
        self.focus_mode_changed.emit(enabled)

    def set_time_range(self, start_time, end_time):
        self._start_time = start_time
        self._end_time = end_time
        database.set_setting("focus_mode_start", start_time)
        database.set_setting("focus_mode_end", end_time)

    def set_whitelist_fullscreen(self, enabled):
        self._whitelist_fullscreen = enabled
        database.set_setting("whitelist_fullscreen", "1" if enabled else "0")

    @property
    def enabled(self):
        return self._enabled

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def whitelist_fullscreen(self):
        return self._whitelist_fullscreen


class ReminderEngine(QObject):
    reminder_triggered = pyqtSignal(dict)
    countdown_triggered = pyqtSignal(dict)
    interval_triggered = pyqtSignal(dict)
    hourly_chime_triggered = pyqtSignal()
    countdown_tick = pyqtSignal()

    def __init__(self, audio_manager: AudioManager, focus_mode: FocusModeManager, parent=None):
        super().__init__(parent)
        self.audio = audio_manager
        self.focus_mode = focus_mode
        self._paused = False
        self._countdown_timers = {}
        self._interval_timers = {}
        self._last_chime_hour = -1

        self._check_timer = QTimer(self)
        self._check_timer.timeout.connect(self._check_reminders)
        self._check_timer.start(1000)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdowns)
        self._countdown_timer.start(1000)

        self._interval_check_timer = QTimer(self)
        self._interval_check_timer.timeout.connect(self._check_intervals)
        self._interval_check_timer.start(1000)

        self._chime_timer = QTimer(self)
        self._chime_timer.timeout.connect(self._check_hourly_chime)
        self._chime_timer.start(1000)

        self._restore_countdowns()
        self._restore_intervals()

    def set_paused(self, paused):
        self._paused = paused

    def is_paused(self):
        return self._paused

    def _check_reminders(self):
        if self._paused:
            return
        now = datetime.now()
        reminders = database.get_reminders(enabled_only=True)
        for r in reminders:
            if self._should_trigger(r, now):
                if self.focus_mode.is_active():
                    continue
                self._trigger_reminder(r)
                database.update_reminder_last_triggered(r["id"], now.isoformat())

    def _should_trigger(self, r, now):
        rtype = r["reminder_type"]
        trigger_time = r["trigger_time"]
        last_triggered = r.get("last_triggered")
        advance = r.get("advance_minutes", 0)
        try:
            tt = datetime.fromisoformat(trigger_time)
        except (ValueError, TypeError):
            return False
        if rtype == "single":
            target = tt - timedelta(minutes=advance)
            if now >= target and now < target + timedelta(seconds=2):
                if last_triggered:
                    return False
                return True
            return False
        elif rtype == "daily":
            target_time = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target_time -= timedelta(minutes=advance)
            if now >= target_time and now < target_time + timedelta(seconds=2):
                today_str = now.strftime("%Y-%m-%d")
                if last_triggered and last_triggered.startswith(today_str):
                    return False
                return True
            return False
        elif rtype == "weekly":
            week_day = r.get("week_day")
            if week_day is None or now.weekday() != week_day:
                return False
            target_time = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target_time -= timedelta(minutes=advance)
            if now >= target_time and now < target_time + timedelta(seconds=2):
                today_str = now.strftime("%Y-%m-%d")
                if last_triggered and last_triggered.startswith(today_str):
                    return False
                return True
            return False
        elif rtype == "monthly":
            month_day = r.get("month_day")
            if month_day is None or now.day != month_day:
                return False
            target_time = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target_time -= timedelta(minutes=advance)
            if now >= target_time and now < target_time + timedelta(seconds=2):
                month_str = now.strftime("%Y-%m")
                if last_triggered and last_triggered.startswith(month_str):
                    return False
                return True
            return False
        elif rtype == "yearly":
            if now.month != tt.month or now.day != tt.day:
                return False
            target_time = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target_time -= timedelta(minutes=advance)
            if now >= target_time and now < target_time + timedelta(seconds=2):
                year_str = str(now.year)
                if last_triggered and last_triggered.startswith(year_str):
                    return False
                return True
            return False
        return False

    def _trigger_reminder(self, r):
        data = {
            "id": r["id"],
            "title": r["title"],
            "content": r.get("content", ""),
            "reminder_type": r["reminder_type"],
            "sound_type": r.get("sound_type", "default"),
            "sound_file": r.get("sound_file"),
            "volume": r.get("volume", 80),
        }
        self.audio.play_sound(
            data["sound_type"], data.get("sound_file"), data["volume"]
        )
        database.add_history({
            "title": r["title"],
            "content": r.get("content", ""),
            "reminder_type": "timed",
        })
        self.reminder_triggered.emit(data)

    def _restore_countdowns(self):
        countdowns = database.get_countdowns(active_only=True)
        for cd in countdowns:
            self._start_countdown_timer(cd["id"], cd["remaining_seconds"], cd["is_running"])

    def start_countdown(self, cid, duration_seconds):
        database.update_countdown(cid, {
            "remaining_seconds": duration_seconds,
            "is_running": 1,
            "triggered": 0,
        })
        self._start_countdown_timer(cid, duration_seconds, True)

    def _start_countdown_timer(self, cid, remaining, is_running):
        self._countdown_timers[cid] = {
            "remaining": remaining,
            "running": is_running == 1,
        }

    def _tick_countdowns(self):
        if self._paused:
            return
        changed = False
        to_remove = []
        for cid, info in self._countdown_timers.items():
            if not info["running"]:
                continue
            info["remaining"] -= 1
            if info["remaining"] <= 0:
                cd = database.get_countdowns()
                cd_data = None
                for c in cd:
                    if c["id"] == cid:
                        cd_data = c
                        break
                if cd_data:
                    database.update_countdown(cid, {"remaining_seconds": 0, "triggered": 1})
                    if not self.focus_mode.is_active():
                        self.audio.play_sound("alert", volume=80)
                        database.add_history({
                            "title": cd_data["title"],
                            "content": f"倒计时结束",
                            "reminder_type": "countdown",
                        })
                        self.countdown_triggered.emit(cd_data)
                to_remove.append(cid)
            else:
                database.update_countdown(cid, {"remaining_seconds": info["remaining"]})
                changed = True
        for cid in to_remove:
            del self._countdown_timers[cid]
            changed = True
        if changed:
            self.countdown_tick.emit()

    def pause_countdown(self, cid):
        if cid in self._countdown_timers:
            self._countdown_timers[cid]["running"] = False
            database.update_countdown(cid, {"is_running": 0})

    def resume_countdown(self, cid):
        if cid in self._countdown_timers:
            self._countdown_timers[cid]["running"] = True
            database.update_countdown(cid, {"is_running": 1})

    def remove_countdown(self, cid):
        if cid in self._countdown_timers:
            del self._countdown_timers[cid]
        database.delete_countdown(cid)
        self.countdown_tick.emit()

    def get_countdown_remaining(self, cid):
        if cid in self._countdown_timers:
            return self._countdown_timers[cid]["remaining"]
        return 0

    def _restore_intervals(self):
        intervals = database.get_intervals(enabled_only=True)
        for iv in intervals:
            self._init_interval_timer(iv)

    def _init_interval_timer(self, iv):
        iid = iv["id"]
        self._interval_timers[iid] = {
            "interval_minutes": iv["interval_minutes"],
            "is_paused": iv.get("is_paused", 0) == 1,
            "last_triggered": iv.get("last_triggered"),
            "start_time": iv.get("start_time"),
            "end_time": iv.get("end_time"),
        }

    def _check_intervals(self):
        if self._paused:
            return
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        for iid, info in list(self._interval_timers.items()):
            if info["is_paused"]:
                continue
            if info["start_time"] and info["end_time"]:
                if not (info["start_time"] <= current_time_str < info["end_time"]):
                    continue
            last = info.get("last_triggered")
            interval_sec = info["interval_minutes"] * 60
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    elapsed = (now - last_dt).total_seconds()
                except (ValueError, TypeError):
                    elapsed = interval_sec + 1
            else:
                elapsed = interval_sec + 1
            if elapsed >= interval_sec:
                iv_data = None
                intervals = database.get_intervals()
                for iv in intervals:
                    if iv["id"] == iid:
                        iv_data = iv
                        break
                if iv_data and iv_data.get("enabled", 1):
                    info["last_triggered"] = now.isoformat()
                    database.update_interval(iid, {"last_triggered": now.isoformat()})
                    if not self.focus_mode.is_active():
                        self.audio.play_sound(
                            iv_data.get("sound_type", "default"),
                            volume=iv_data.get("volume", 80),
                        )
                        database.add_history({
                            "title": iv_data["title"],
                            "content": iv_data.get("content", ""),
                            "reminder_type": "interval",
                        })
                        self.interval_triggered.emit(iv_data)

    def add_interval_to_engine(self, iv_data):
        self._init_interval_timer(iv_data)

    def remove_interval_from_engine(self, iid):
        if iid in self._interval_timers:
            del self._interval_timers[iid]

    def pause_interval(self, iid):
        if iid in self._interval_timers:
            self._interval_timers[iid]["is_paused"] = True
            database.update_interval(iid, {"is_paused": True})

    def resume_interval(self, iid):
        if iid in self._interval_timers:
            self._interval_timers[iid]["is_paused"] = False
            database.update_interval(iid, {"is_paused": False})

    def _check_hourly_chime(self):
        if self._paused:
            return
        enabled = database.get_setting("hourly_chime_enabled", "0") == "1"
        if not enabled:
            return
        now = datetime.now()
        if now.minute != 0 or now.second > 1:
            return
        start_h = int(database.get_setting("hourly_chime_start", "9"))
        end_h = int(database.get_setting("hourly_chime_end", "21"))
        if not (start_h <= now.hour < end_h):
            return
        if self._last_chime_hour == now.hour:
            return
        self._last_chime_hour = now.hour
        if self.focus_mode.is_active():
            return
        sound_type = database.get_setting("hourly_chime_sound", "chime")
        volume = int(database.get_setting("default_volume", "80"))
        self.audio.play_sound(sound_type, volume=volume)
        tts_enabled = database.get_setting("tts_enabled", "0") == "1"
        if tts_enabled:
            self.audio.speak(f"现在是{now.hour}点整")
        self.hourly_chime_triggered.emit()

    def get_next_reminder(self):
        now = datetime.now()
        reminders = database.get_reminders(enabled_only=True)
        next_time = None
        next_reminder = None
        for r in reminders:
            tt = self._calc_next_trigger(r, now)
            if tt and (next_time is None or tt < next_time):
                next_time = tt
                next_reminder = r
        if next_reminder and next_time:
            return next_reminder, next_time
        return None, None

    def _calc_next_trigger(self, r, now):
        rtype = r["reminder_type"]
        try:
            tt = datetime.fromisoformat(r["trigger_time"])
        except (ValueError, TypeError):
            return None
        advance = r.get("advance_minutes", 0)
        if rtype == "single":
            target = tt - timedelta(minutes=advance)
            if target > now:
                return target
            return None
        elif rtype == "daily":
            target = now.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target -= timedelta(minutes=advance)
            if target <= now:
                target += timedelta(days=1)
            return target
        elif rtype == "weekly":
            week_day = r.get("week_day", 0)
            days_ahead = (week_day - now.weekday()) % 7
            target = now + timedelta(days=days_ahead)
            target = target.replace(hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target -= timedelta(minutes=advance)
            if target <= now:
                target += timedelta(weeks=1)
            return target
        elif rtype == "monthly":
            month_day = r.get("month_day", 1)
            target = now.replace(day=month_day, hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target -= timedelta(minutes=advance)
            if target <= now:
                if now.month == 12:
                    target = target.replace(year=now.year + 1, month=1)
                else:
                    target = target.replace(month=now.month + 1)
            return target
        elif rtype == "yearly":
            target = now.replace(month=tt.month, day=tt.day, hour=tt.hour, minute=tt.minute, second=0, microsecond=0)
            target -= timedelta(minutes=advance)
            if target <= now:
                target = target.replace(year=now.year + 1)
            return target
        return None
