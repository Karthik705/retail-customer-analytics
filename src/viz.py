"""Shared chart style. Same palette as powerbi/theme.json so every visual matches."""
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

from . import config as C

PALETTE = {
    "navy": "#1B2A49",
    "teal": "#2A9D8F",
    "amber": "#E9C46A",
    "coral": "#E76F51",
    "slate": "#6C7A89",
    "sky": "#8AB6D6",
    "light": "#F4F1EA",
}
SEQ = [PALETTE[k] for k in ["navy", "teal", "amber", "coral", "slate", "sky"]]


def set_style():
    sns.set_theme(style="whitegrid", palette=SEQ, font_scale=1.0)
    plt.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.alpha": 0.4,
    })


def money_axis(ax, axis="y", unit="k"):
    div = {"k": 1e3, "M": 1e6}[unit]
    fmt = mtick.FuncFormatter(lambda x, _: f"{C.CURRENCY}{x / div:,.0f}{unit}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def pct_axis(ax, axis="y"):
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(mtick.PercentFormatter(1.0))


def save(fig, name):
    C.IMAGES_DIR.mkdir(exist_ok=True)
    fig.savefig(C.IMAGES_DIR / f"{name}.png")
