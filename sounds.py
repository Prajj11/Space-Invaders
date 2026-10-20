"""
Procedural sound engine -- every effect is synthesized in code.

No .wav/.ogg files: we generate int16 PCM sample arrays (mono, 22.05 kHz)
with pure Python math, wrap them in pygame.mixer.Sound objects, and play
them. If no audio device is available the game simply runs silently.
"""

import array
import math
import random

import pygame

RATE = 22050
MASTER = 0.55


def _pack(samples, volume=1.0):
    """Turn a list of floats in [-1, 1] into a pygame Sound."""
    buf = array.array("h")
    for s in samples:
        v = max(-1.0, min(1.0, s * volume))
        buf.append(int(v * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _sweep(f0, f1, duration, env_pow=1.0, square=True):
    """Frequency sweep (square or sine) with a (1-t)^env_pow envelope."""
    n = int(RATE * duration)
    phase = 0.0
    out = []
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        phase += f / RATE
        if square:
            s = 1.0 if (phase % 1.0) < 0.5 else -1.0
        else:
            s = math.sin(phase * 2.0 * math.pi)
        out.append(s * (1.0 - t) ** env_pow)
    return out


def _thump(freq, duration, decay=18.0):
    """Low square thump with exponential decay (the invader march)."""
    n = int(RATE * duration)
    out = []
    for i in range(n):
        t = i / RATE
        s = 1.0 if (t * freq) % 1.0 < 0.5 else -1.0
        out.append(s * math.exp(-decay * t))
    return out


def _noise(duration, decay=6.0, rumble=None):
    """Decaying white noise, optionally over a low sine rumble."""
    n = int(RATE * duration)
    out = []
    for i in range(n):
        t = i / RATE
        s = random.uniform(-1.0, 1.0) * (1.0 - t) ** decay
        if rumble is not None:
            s += rumble * math.sin(2.0 * math.pi * 55.0 * t) * (1.0 - t)
        out.append(s)
    return out


def _warble(duration):
    """The UFO's signature siren: a sine with vibrato."""
    n = int(RATE * duration)
    out = []
    for i in range(n):
        t = i / RATE
        f = 380.0 + 90.0 * math.sin(2.0 * math.pi * 7.0 * t)
        out.append(0.8 * math.sin(2.0 * math.pi * f * t))
    return out


def _arp(freqs, step=0.09):
    """Little rising arpeggio of sine blips."""
    out = []
    for f in freqs:
        n = int(RATE * step)
        for i in range(n):
            t = i / n
            out.append(math.sin(2.0 * math.pi * f * t) * (1.0 - t))
    return out


class SoundBank:
    """Owns the mixer and every Sound. Degrades gracefully to silence."""

    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self._ufo_channel = None
        try:
            pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
            self.ok = True
        except pygame.error:
            return

        mk = _pack
        self.sounds = {
            # Player laser: fast descending zap
            "shoot": mk(_sweep(1500, 350, 0.12, env_pow=0.5), 0.45),
            # Invader destroyed: harsher, longer fall
            "alien_die": mk(_sweep(480, 60, 0.18, env_pow=2.0), 0.55),
            # The iconic four-note march, cycled da-da-da-da
            "march0": mk(_thump(110, 0.10), 0.8),
            "march1": mk(_thump(98, 0.10), 0.8),
            "march2": mk(_thump(88, 0.10), 0.8),
            "march3": mk(_thump(78, 0.10), 0.8),
            # UFO siren (looped) and its explosion
            "ufo": mk(_warble(0.9), 0.30),
            "ufo_die": mk(_sweep(1000, 80, 0.30, env_pow=1.5), 0.5),
            # Player cannon exploding
            "player_die": mk(_noise(0.6, rumble=0.9), 0.65),
            # Bombs chewing through bunkers, bullets popping bombs
            "shield_hit": mk(_noise(0.07, decay=3.0), 0.30),
            "pop": mk(_sweep(300, 200, 0.05, env_pow=1.0), 0.35),
            # Bonus cannon + wave fanfare
            "extra_life": mk(_arp([700, 1050, 1400]), 0.40),
            "wave_clear": mk(_arp([523, 659, 784, 1047], step=0.11), 0.40),
        }

    # -- plain one-shots ------------------------------------------------------
    def play(self, name):
        if self.ok and not self.muted:
            self.sounds[name].play()

    def play_march(self, step_index):
        self.play("march%d" % (step_index % 4))

    # -- looping UFO siren ----------------------------------------------------
    def ufo_start(self):
        if self.ok and not self.muted and self._ufo_channel is None:
            self._ufo_channel = self.sounds["ufo"].play(loops=-1)

    def ufo_stop(self):
        if self._ufo_channel is not None:
            self._ufo_channel.stop()
            self._ufo_channel = None

    def set_muted(self, muted):
        self.muted = muted
        if muted:
            self.ufo_stop()
