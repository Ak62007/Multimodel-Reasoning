import matplotlib.pyplot as plt
import numpy as np

def plot_beautiful(x, y, title=None, xlabel='X', ylabel='Y', color='blue', linewidth=2, marker=None):
    """
    Simple utility to create a beautiful line plot.
    
    Args:
        x, y: arrays or lists of data
        title: optional plot title
        xlabel, ylabel: optional axis labels
        color: line color (default: blue)
        linewidth: line thickness (default: 2)
        marker: optional marker style (e.g., 'o', '^')
    
    Returns:
        fig, ax: matplotlib figure and axis for further customization
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot the line
    ax.plot(x, y, color=color, linewidth=linewidth, marker=marker, markersize=4)
    
    # Styling for beauty
    ax.set_title(title or 'Beautiful Plot', fontsize=16, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Auto-format for better readability
    plt.tight_layout()
    plt.show()
    
    return fig, ax

def plot_dual_beautiful(x, y1, y2, title=None, xlabel='X', ylabel1='Y1', ylabel2='Y2', color1='blue', color2='red'):
    """
    Utility for twin-axis plots (e.g., two metrics over time).
    
    Args:
        x: shared x-axis data
        y1, y2: two y-series
        title: optional title
        xlabel, ylabel1, ylabel2: labels
        color1, color2: colors for each line
    """
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # First line
    ax1.plot(x, y1, color=color1, linewidth=2, label=f'{ylabel1}')
    ax1.set_xlabel(xlabel, fontsize=12)
    ax1.set_ylabel(ylabel1, color=color1, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Second axis and line
    ax2 = ax1.twinx()
    ax2.plot(x, y2, color=color2, linewidth=2, label=f'{ylabel2}')
    ax2.set_ylabel(ylabel2, color=color2, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Styling
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    fig.suptitle(title or 'Dual Metric Plot', fontsize=16, fontweight='bold')
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.show()
    
    return fig, (ax1, ax2)

