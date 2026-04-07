from matplotlib.figure import Figure

def create_figure(palette, figsize=(5.8, 3.8), dpi=100):
    fig = Figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(palette["chart_bg"])
    fig.set_constrained_layout(True)
    return fig

def style_axes(fig, ax, palette):
    fig.patch.set_facecolor(palette["chart_bg"])
    ax.set_facecolor(palette["chart_bg"])
    ax.grid(True, color=palette["chart_grid"], alpha=0.35, linestyle="--", linewidth=0.7)

    for spine in ax.spines.values():
        spine.set_color(palette["chart_axis"])

    ax.tick_params(axis="x", colors=palette["chart_text"], labelsize=9)
    ax.tick_params(axis="y", colors=palette["chart_text"], labelsize=9)

    ax.title.set_color(palette["chart_text"])
    ax.xaxis.label.set_color(palette["chart_text"])
    ax.yaxis.label.set_color(palette["chart_text"])