import os
import random
import time
import numpy as np
import pygame

from CONFIG import (
    SENTIMENT_INITIAL,
    SENTIMENT_OPTIONS,
    BREAK_INTERVAL,
    BREAK_DURATION_SECONDS,
    PREVIEW_GAP_SECONDS,
    TEST_STIMULI_COUNT,
    TEST_BREAK_INTERVAL,
)

class GameInformation:
    """Holds all experiment state: stimuli list, trial order, ratings so far."""

    def __init__(self, stimuli_dir="stimuli"):
        self.stimuli = [
            os.path.join(stimuli_dir, f)
            for f in sorted(os.listdir(stimuli_dir))
            if not f.startswith(".")
        ]
        self.break_interval = BREAK_INTERVAL
        self.test_mode = False

        # The pair order is built when the experiment starts (see
        # Game.start_preview). Until then the matrix is empty, so closing the
        # window early still saves an all-zero matrix.
        self.songOrder = []
        self.similarityArray = np.zeros((len(self.stimuli), len(self.stimuli)))

        self.testing_completed = False
        self.pair_number = 0
        self.similarityScore = float(SENTIMENT_INITIAL)

        self.rated = False
        self.playing_A = False
        self.playing_B = False

        # "preview" -> play every stimulus once before trials start
        # "trial"   -> normal A/B rating trials
        # "break"   -> optional pause offered every BREAK_INTERVAL pairs
        self.phase = "preview"
        self.preview_started = False
        self.preview_index = 0
        self.break_remaining = 0.0

    def _build_trials(self):
        """(Re)build the shuffled pair order and the ratings matrix."""
        n = len(self.stimuli)
        self.songOrder = [[i, j] for i in range(n) for j in range(i)]
        for pair in self.songOrder:
            random.shuffle(pair)  # randomize which sound is A / B
        random.shuffle(self.songOrder)
        self.similarityArray = np.zeros((n, n))

    def enable_test_mode(self):
        """Use only the first few clips and offer breaks more often."""
        self.test_mode = True
        self.stimuli = self.stimuli[:TEST_STIMULI_COUNT]
        self.break_interval = TEST_BREAK_INTERVAL


class Game:
    """Owns experiment state and audio playback; has no drawing code."""

    def __init__(self, stimuli_dir="stimuli"):
        pygame.mixer.init()
        self.gameInfo = GameInformation(stimuli_dir)
        self._break_started_at = None
        self._preview_wait_until = None
        # Time the loaded track was told to play (None if nothing should be
        # playing). Polled to detect the track ending, rather than relying on
        # pygame's event queue.
        self._track_playing = False

    # ---------------- audio helpers ----------------
    def _stop(self):
        pygame.mixer.music.stop()
        self._track_playing = False

    def _load_and_play(self, path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.7)
        pygame.mixer.music.play()
        self._track_playing = True

    def _track_just_finished(self):
        if not self._track_playing or pygame.mixer.music.get_busy():
            return False
        self._track_playing = False
        return True

    # ---------------- preview phase ----------------
    def start_preview(self, test_mode=False):
        """Begin the experiment. In test mode: 3 clips, a break every 2 pairs."""
        info = self.gameInfo
        if info.phase == "preview" and not info.preview_started:
            if test_mode:
                info.enable_test_mode()
            info.preview_started = True
            info._build_trials()
            if info.stimuli:
                self._play_preview_current()
            else:
                info.phase = "trial"

    def _play_preview_current(self):
        self._load_and_play(self.gameInfo.stimuli[self.gameInfo.preview_index])

    def _advance_preview(self):
        info = self.gameInfo
        info.preview_index += 1
        if info.preview_index >= len(info.stimuli):
            info.phase = "trial"
        else:
            # a beat of silence before the next clip
            self._preview_wait_until = time.time() + PREVIEW_GAP_SECONDS

    # ---------------- break phase ----------------
    def _maybe_start_break(self):
        info = self.gameInfo
        if info.pair_number > 0 and info.pair_number % info.break_interval == 0:
            info.phase = "break"
            self._break_started_at = time.time()
            info.break_remaining = BREAK_DURATION_SECONDS

    def end_break(self):
        if self.gameInfo.phase == "break":
            self.gameInfo.phase = "trial"

    # ---------------- rating ----------------
    def set_similarity(self, score):
        self.gameInfo.similarityScore = max(1.0, min(float(score), float(SENTIMENT_OPTIONS)))
        self.gameInfo.rated = True

    # ---------------- per-frame refresh ----------------
    def refresh(self):
        """Call once per frame."""
        info = self.gameInfo

        if info.phase == "break":
            elapsed = time.time() - self._break_started_at
            info.break_remaining = max(0.0, BREAK_DURATION_SECONDS - elapsed)

        # in the silent gap between two preview clips
        if info.phase == "preview" and self._preview_wait_until is not None:
            if time.time() >= self._preview_wait_until:
                self._preview_wait_until = None
                self._play_preview_current()
            return

        if self._track_just_finished():
            if info.phase == "preview":
                self._advance_preview()
            elif info.phase == "trial":
                info.playing_A = info.playing_B = False

    # ---------------- trials ----------------
    def next_pair(self):
        """Advance to the next pair"""
        info = self.gameInfo
        if info.phase != "trial" or not info.rated:
            return

        info.rated = False
        self._stop()
        info.playing_A = info.playing_B = False

        a, b = info.songOrder[info.pair_number]
        info.similarityArray[a, b] = info.similarityArray[b, a] = info.similarityScore

        info.similarityScore = float(SENTIMENT_INITIAL)
        info.pair_number += 1

        if info.pair_number >= len(info.songOrder):
            info.testing_completed = True
        else:
            self._maybe_start_break()

    def _toggle_play(self, side):
        """Toggle one trial sound, treating the mixer as the source of truth.

        A stopped mixer always wins over the playing_* flags, so a click just
        after a sound ends restarts it instead of being read as "pause".
        """
        info = self.gameInfo
        if info.phase != "trial":
            return

        is_current_side = info.playing_A if side == "A" else info.playing_B

        if is_current_side and pygame.mixer.music.get_busy():
            self._stop()
            info.playing_A = info.playing_B = False
            return

        index = info.songOrder[info.pair_number][0 if side == "A" else 1]
        self._load_and_play(info.stimuli[index])
        info.playing_A = side == "A"
        info.playing_B = side == "B"

    def play_A(self):
        self._toggle_play("A")

    def play_B(self):
        self._toggle_play("B")
