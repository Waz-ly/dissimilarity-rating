import os
import subprocess
import sys
import traceback

import numpy as np
import pygame

from game import Game
from CONFIG import *

pygame.font.init()


_SAVE_DIALOG_SCRIPT = """
import sys
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.asksaveasfilename(
    title="Choose where to save the dissimilarity matrix",
    initialdir=sys.argv[1],
    initialfile=sys.argv[2],
    defaultextension=".txt",
    filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
)
root.destroy()
sys.stdout.write(path)
"""


def choose_output_path(default_path):
    """Show a native "save as" window and return the chosen path, or None if
    the user cancels.

    The dialog runs in a separate process so tkinter and pygame/SDL never
    share a process (they can conflict, especially on macOS). If the dialog
    can't be shown at all (e.g. tkinter missing), fall back to default_path.
    """
    default_path = os.path.abspath(default_path)
    try:
        result = subprocess.run(
            [sys.executable, "-c", _SAVE_DIALOG_SCRIPT,
             os.path.dirname(default_path), os.path.basename(default_path)],
            capture_output=True, text=True, check=True,
        )
    except Exception as e:
        print(f"Could not show save dialog ({e}); saving to {default_path}")
        return default_path
    return result.stdout.rstrip("\r\n") or None


class SimilarityTest:
    def __init__(self, fullscreen=False):
        # Ask where to save before any experiment window opens.
        self.output_path = choose_output_path(OUTPUT_FILE)
        if self.output_path is None:
            sys.exit(0)

        pygame.init()
        pygame.display.set_caption("Dissimilarity Rating Experiment")

        self.fullscreen = fullscreen
        self.windowed_size = (WIDTH, HEIGHT)
        self._apply_display_mode()

        self.bg_color = pygame.Color(BG_COLOR)
        self.fg_color = pygame.Color(FG_COLOR)

        self.small_font = pygame.font.SysFont(*SMALL_FONT)
        self.large_font = pygame.font.SysFont(*LARGE_FONT)
        self.pair_font  = pygame.font.SysFont(*PAIR_NUMBER_FONT)

        self.game = Game(stimuli_dir=STIMULI_DIR)

        self._raw_images = {
            name: pygame.image.load(os.path.join(ASSETS_DIR, f"{name}.webp")).convert_alpha()
            for name in ("play", "pause")
        }
        self._resized_cache = {}

        self.dragging = False
        self._closed = False
        self._done = False

        self.compute_layout()

    # ---------------- display / fullscreen ----------------
    def _apply_display_mode(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def _set_fullscreen(self, value):
        self.fullscreen = value
        self._apply_display_mode()
        self.compute_layout()

    def toggle_fullscreen(self):
        self._set_fullscreen(not self.fullscreen)

    def exit_fullscreen(self):
        if self.fullscreen:
            self._set_fullscreen(False)

    # ---------------- assets ----------------
    def _get_button_image(self, name, size):
        key = (name, size)
        if key not in self._resized_cache:
            self._resized_cache[key] = pygame.transform.smoothscale(
                self._raw_images[name], (size, size)
            )
        return self._resized_cache[key]

    # ---------------- layout ----------------
    def compute_layout(self):
        w, h = (max(v, 1) for v in self.screen.get_size())

        cb_w = int(w * CENTER_BOX_WIDTH_FRAC)
        cb_h = int(h * CENTER_BOX_HEIGHT_FRAC)

        self.layout = {
            "w": w, "h": h,
            "button_size": max(int(min(w, h) * BUTTON_SIZE_FRAC), 20),
            "button_A": (int(w * BUTTON_A_X_FRAC), int(h * BUTTON_Y_FRAC)),
            "button_B": (int(w * BUTTON_B_X_FRAC), int(h * BUTTON_Y_FRAC)),
            "scale_x": int(w * SCALE_X_FRAC),
            "scale_y": int(h * SCALE_Y_FRAC),
            "scale_width": max(int(w * SCALE_WIDTH_FRAC), 4),
            "scale_height": int(h * SCALE_HEIGHT_FRAC),
            "next_box": (
                int(w * NEXT_X_FRAC), int(h * NEXT_Y_FRAC),
                int(w * NEXT_WIDTH_FRAC), int(h * NEXT_HEIGHT_FRAC),
            ),
            "center_box": (
                int(w / 2 - cb_w / 2), int(h * CENTER_BOX_Y_FRAC - cb_h / 2), cb_w, cb_h,
            ),
        }
        return self.layout

    def on_resize(self, size):
        if not self.fullscreen:
            self.windowed_size = size
            self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.compute_layout()

    # ---------------- input ----------------
    @staticmethod
    def _point_in_box(x, y, bx, by, bw, bh, pad=0):
        return (bx - pad) <= x <= (bx + bw + pad) and (by - pad) <= y <= (by + bh + pad)

    def _hit_test(self, x, y):
        """Return the name of the clickable element under (x, y), or None."""
        L = self.layout
        info = self.game.gameInfo

        if info.phase == "preview":
            if not info.preview_started and self._point_in_box(x, y, *L["center_box"], pad=8):
                return "start"
            return None

        if info.phase == "break":
            return "continue" if self._point_in_box(x, y, *L["center_box"], pad=8) else None

        # trial phase
        bs = L["button_size"]
        for name in ("A", "B"):
            if self._point_in_box(x, y, *L[f"button_{name}"], bs, bs, pad=8):
                return f"play_{name}"

        if info.rated and self._point_in_box(x, y, *L["next_box"], pad=8):
            return "next"

        sx, sw = L["scale_x"], L["scale_width"]
        if self._point_in_box(x, y, sx - sw, L["scale_y"], sw * 3, L["scale_height"]):
            return "scale"

        return None

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.on_close()
            return

        if self._done:
            # Any key press or click on the "done" screen exits.
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.on_close()
            return

        if event.type == pygame.VIDEORESIZE:
            self.on_resize((event.w, event.h))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                self.exit_fullscreen()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_click(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_score_from_y(event.pos[1])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def on_click(self, pos):
        target = self._hit_test(*pos)

        if target == "scale":
            self.dragging = True
            self._update_score_from_y(pos[1])
        elif target is not None:
            try:
                self._activate(target)
            except Exception:
                traceback.print_exc()

    def _activate(self, target):
        game = self.game
        if target == "next":
            game.next_pair()
            if game.gameInfo.testing_completed:
                self.finish()
            return

        {
            "start": game.start_preview,
            "continue": game.end_break,
            "play_A": game.play_A,
            "play_B": game.play_B,
        }[target]()

    def _update_score_from_y(self, y):
        sy, sh = self.layout["scale_y"], self.layout["scale_height"]
        rel = min(max((y - sy) / sh if sh else 0, 0.0), 1.0)
        # top of the bar = "most dissimilar" (9), bottom = "least dissimilar" (1)
        self.game.set_similarity(9 - rel * (SENTIMENT_OPTIONS - 1))

    # ---------------- render helpers ----------------
    def _draw_text(self, text, font, pos, anchor="center"):
        surf = font.render(text, True, self.fg_color)
        rect = surf.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        self.screen.blit(surf, rect)

    def _draw_button_box(self, box, label):
        x, y, w, h = box
        pygame.draw.rect(self.screen, self.fg_color, (x, y, w, h))
        pygame.draw.rect(self.screen, self.bg_color, (x + 5, y + 5, w - 10, h - 10))
        self._draw_text(label, self.large_font, (x + w / 2, y + h / 2))

    # ---------------- render ----------------
    def render(self):
        self.screen.fill(self.bg_color)
        phase = self.game.gameInfo.phase

        if self._done:
            self._render_done()
        elif phase == "preview":
            self._render_preview()
        elif phase == "break":
            self._render_break()
        else:
            self._render_trial()

        pygame.display.flip()

    def _render_preview(self):
        L, info = self.layout, self.game.gameInfo
        w, h = L["w"], L["h"]

        if not info.preview_started:
            self._draw_text("Sound Preview", self.large_font, (w / 2, h * 0.35))
            self._draw_text(
                "First, listen to each sound once to get a sense of the range of sounds.",
                self.small_font, (w / 2, h * 0.45),
            )
            self._draw_button_box(L["center_box"], "Start")
            return

        total = len(info.stimuli)
        current = min(info.preview_index + 1, total)
        self._draw_text("Get a feel for the sounds before we begin", self.large_font, (w / 2, h * 0.35))
        self._draw_text(f"Now playing {current} of {total}", self.small_font, (w / 2, h * 0.45))

    def _render_break(self):
        L, info = self.layout, self.game.gameInfo
        w, h = L["w"], L["h"]
        minutes, seconds = divmod(max(int(info.break_remaining), 0), 60)

        self._draw_text("Take a break!", self.large_font, (w / 2, h * 0.3))
        self._draw_text(f"You've rated {info.pair_number} pairs so far.", self.small_font, (w / 2, h * 0.4))
        self._draw_text(f"{minutes:01d}:{seconds:02d}", self.large_font, (w / 2, h * 0.48))
        self._draw_text(
            "Continue whenever you're ready - the countdown is just a suggestion.",
            self.small_font, (w / 2, h * 0.55),
        )
        self._draw_button_box(L["center_box"], "Continue")

    def _render_trial(self):
        L, info = self.layout, self.game.gameInfo

        for side, playing in (("A", info.playing_A), ("B", info.playing_B)):
            image = self._get_button_image("pause" if playing else "play", L["button_size"])
            self.screen.blit(image, L[f"button_{side}"])

        instructions = (
            "Click the play buttons to listen to the stimuli.",
            "Move the slider on the right based on the stimuli's dissimilarity.",
            "Click next when complete. Try to use the full range of the scale.",
        )
        for i, line in enumerate(instructions):
            self._draw_text(line, self.small_font, (20, 20 + 25 * i), anchor="topleft")

        self._draw_text(str(info.pair_number), self.pair_font, (20, L["h"] - 20), anchor="bottomleft")

        # scale bar
        sx, sy = L["scale_x"], L["scale_y"]
        sw, sh = L["scale_width"], L["scale_height"]
        pygame.draw.rect(self.screen, self.fg_color, (sx, sy, sw, sh))

        for i in range(SENTIMENT_OPTIONS):
            tab_y = sy + sh - i / (SENTIMENT_OPTIONS - 1) * sh
            pygame.draw.rect(self.screen, self.fg_color, (sx - 10, tab_y - 2, sw + 20, 4))
            self._draw_text(str(i + 1), self.small_font, (sx + sw + 20, tab_y), anchor="midleft")

        frac = (info.similarityScore - 1) / (SENTIMENT_OPTIONS - 1)
        indicator_y = sy + sh - frac * sh
        pygame.draw.circle(self.screen, self.fg_color,
                           (int(sx + sw / 2), int(indicator_y)), SIMILARITY_INDICATOR_SIZE)
        self._draw_text(f"{info.similarityScore:.1f}", self.small_font,
                        (sx - 30, indicator_y), anchor="midright")

        self._draw_text("most dissimilar (least similar)", self.small_font, (sx + sw / 2, sy - 20))
        self._draw_text("least dissimilar (most similar)", self.small_font, (sx + sw / 2, sy + sh + 20))

        if info.rated:
            self._draw_button_box(L["next_box"], "next")

    def _render_done(self):
        w, h = self.layout["w"], self.layout["h"]
        self._draw_text("Done", self.large_font, (w / 2, h * 0.45))
        self._draw_text("Thanks! The experiment is complete.", self.small_font, (w / 2, h * 0.55))
        self._draw_text("Press any key or click to exit.", self.small_font, (w / 2, h * 0.62))

    # ---------------- main loop / lifecycle ----------------
    def tick(self):
        """Advance experiment state. Call once per frame from the main loop."""
        if not (self._closed or self._done):
            self.game.refresh()

    def finish(self):
        self._done = True
        self.save()

    def on_close(self):
        if self._closed:
            return
        self._closed = True
        if not self._done:
            self.save()
        pygame.quit()
        sys.exit(0)

    def save(self):
        # stimuli saved in alphabetical order
        matrix = np.round(self.game.gameInfo.similarityArray, 2)
        np.savetxt(self.output_path, matrix, fmt="%.2f", delimiter=" ")
