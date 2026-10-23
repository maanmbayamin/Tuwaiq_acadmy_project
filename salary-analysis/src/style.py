"""One visual system for the notebook (matplotlib) and the app (Plotly).

Colors come from a validated, colorblind-safe palette. Categorical hues are
always assigned in this fixed order; ordered categories use one blue ramp.
"""

SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

BLUE = "#2a78d6"
ORANGE = "#eb6834"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

# Blue ramp steps for ordered categories (light to dark).
RAMP_4 = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # e.g. Entry, Mid, Senior, Executive
RAMP_3 = ["#86b6ef", "#2a78d6", "#104281"]            # e.g. Small, Medium, Large
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

# Chart tokens for the Streamlit app (Plotly). The app picks light or dark
# to match the viewer's theme; the hues are the same palette stepped per mode.
APP_FONT = "'Instrument Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"
APP_CHART = {
    "light": {
        "ink": "#14213d", "muted": "#52607a", "faint": "#8a96a8", "grid": "#e3e8ef",
        "axis": "#c9d2de", "surface": "#f6f8fb", "hover_bg": "#ffffff",
        "blue": "#2a78d6", "blue_soft": "#9ec5f4", "orange": "#eb6834", "orange_soft": "#f6b79c",
        "aqua": "#1baf7a", "ramp4": ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],
        "sequential": ["#e3eefc", "#9ec5f4", "#5598e7", "#256abf", "#104281"],
    },
    "dark": {
        "ink": "#e6ebf2", "muted": "#a9b4c4", "faint": "#7d8899", "grid": "#232d3c",
        "axis": "#344055", "surface": "#0f1520", "hover_bg": "#18202c",
        "blue": "#3987e5", "blue_soft": "#256abf", "orange": "#d95926", "orange_soft": "#8f3f1f",
        "aqua": "#199e70", "ramp4": ["#184f95", "#256abf", "#3987e5", "#86b6ef"],
        "sequential": ["#14243a", "#184f95", "#2a78d6", "#6da7ec", "#cde2fb"],
    },
}


def apply_matplotlib_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "font.family": "sans-serif",
        "font.size": 10.5,
        "text.parse_math": False,  # so "$100K" is shown as text, not as a formula
        "text.color": INK,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlecolor": INK,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 1,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 1,
        "grid.linestyle": "-",
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "lines.linewidth": 2,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "patch.edgecolor": SURFACE,
        "axes.prop_cycle": mpl.cycler(color=CATEGORICAL),
    })


def money_k(x, _pos=None) -> str:
    """Axis formatter: 150000 -> '150K'."""
    if abs(x) >= 1_000_000:
        return f"{x / 1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{x / 1_000:.0f}K"
    return f"{x:.0f}"
