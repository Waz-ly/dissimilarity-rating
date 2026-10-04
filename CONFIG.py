# ---------------------------------------------------------------------------
# Window (used as the default *windowed* size; fullscreen uses the screen's
# own resolution and everything below scales to whatever size the window is)
# ---------------------------------------------------------------------------
WIDTH = 1000
HEIGHT = 700

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG_COLOR = "black"
FG_COLOR = "white"

# ---------------------------------------------------------------------------
# Fonts ("font name", "size", "bold", "italic")
# ---------------------------------------------------------------------------
SMALL_FONT = ("Helvetica", 13)
LARGE_FONT = ("Helvetica", 26, True)
PAIR_NUMBER_FONT = ("Helvetica", 9)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STIMULI_DIR = "./sounds"
ASSETS_DIR = "./assets"
OUTPUT_FILE = "./data/dissimilarity_matrix.txt"

# ---------------------------------------------------------------------------
# Rating scale
# ---------------------------------------------------------------------------
SENTIMENT_OPTIONS = 9
SENTIMENT_INITIAL = 5
SIMILARITY_INDICATOR_SIZE = 10

# ---------------------------------------------------------------------------
# Breaks
# ---------------------------------------------------------------------------
BREAK_INTERVAL = 50            # offer a break every N completed pairs
BREAK_DURATION_SECONDS = 5 * 60  # countdown shown on the break screen

# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
PREVIEW_GAP_SECONDS = 1.0      # silence between each preview clip

# ---------------------------------------------------------------------------
# Layout, expressed as FRACTIONS of the current canvas width/height.
# This is what lets the same code look right whether the window is small,
# maximized, or fullscreen on a completely different resolution.
# ---------------------------------------------------------------------------
BUTTON_SIZE_FRAC = 0.2
BUTTON_A_X_FRAC = 0.10
BUTTON_B_X_FRAC = 0.37
BUTTON_Y_FRAC = 0.35

SCALE_X_FRAC = 0.75
SCALE_Y_FRAC = 0.20
SCALE_WIDTH_FRAC = 0.005
SCALE_HEIGHT_FRAC = 0.55

NEXT_X_FRAC = 0.85
NEXT_Y_FRAC = 0.05
NEXT_WIDTH_FRAC = 0.10
NEXT_HEIGHT_FRAC = 0.08

# Centered button used by the preview ("Start") and break ("Continue")
# screens.
CENTER_BOX_WIDTH_FRAC = 0.22
CENTER_BOX_HEIGHT_FRAC = 0.10
CENTER_BOX_Y_FRAC = 0.62
