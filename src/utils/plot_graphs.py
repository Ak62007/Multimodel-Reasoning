import matplotlib.pyplot as plt
import numpy as np

def plot_beautiful(x=None, y=None, plot_type='line', title=None, xlabel='X', ylabel='Y', 
                   color='blue', linewidth=2, marker=None, alpha=0.8, bins=30, 
                   figsize=(10, 6), grid_alpha=0.3, legend_loc='best'):
    """
    Flexible utility to create beautiful plots of various types.
    
    Args:
        x, y: arrays or lists of data (x can be None for 'hist')
        plot_type: Type of plot ('line', 'bar', 'scatter', 'hist') - default: 'line'
        title: optional plot title
        xlabel, ylabel: optional axis labels
        color: line/bar/scatter color (default: 'blue')
        linewidth: line thickness (default: 2); for bar/scatter: edge width
        marker: optional marker style for line/scatter (e.g., 'o', '^') - default: None
        alpha: transparency for bar/scatter/hist (default: 0.8)
        bins: number of bins for histogram (default: 30)
        figsize: figure size (default: (10, 6))
        grid_alpha: grid transparency (default: 0.3)
        legend_loc: legend location (default: 'best')
    
    Returns:
        fig, ax: matplotlib figure and axis for further customization
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Handle different plot types
    if plot_type == 'line':
        if x is None or y is None:
            raise ValueError("x and y required for 'line' plot")
        ax.plot(x, y, color=color, linewidth=linewidth, marker=marker, markersize=4)
    
    elif plot_type == 'bar':
        if x is None or y is None:
            raise ValueError("x and y required for 'bar' plot")
        ax.bar(x, y, color=color, alpha=alpha, linewidth=linewidth, edgecolor='black')
    
    elif plot_type == 'scatter':
        if x is None or y is None:
            raise ValueError("x and y required for 'scatter' plot")
        ax.scatter(x, y, color=color, alpha=alpha, s=40, linewidth=linewidth, 
                   edgecolors='black', marker=marker or 'o')
    
    elif plot_type == 'hist':
        if y is None:
            raise ValueError("y required for 'hist' plot")
        ax.hist(y, bins=bins, color=color, alpha=alpha, edgecolor='black', linewidth=1)
        if xlabel:
            ax.set_xlabel('Bins')
        if ylabel:
            ax.set_ylabel('Frequency')
    
    else:
        raise ValueError(f"Unsupported plot_type: '{plot_type}'. Choose 'line', 'bar', 'scatter', or 'hist'.")
    
    # Common styling for beauty
    ax.set_title(title or f'Beautiful {plot_type.capitalize()} Plot', fontsize=16, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=grid_alpha, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Auto-format for better readability
    plt.tight_layout()
    plt.show()
    
    return fig, ax


def plot_dual_beautiful(x, y1, y2, plot_type='line', title=None, xlabel='X', 
                        ylabel1='Y1', ylabel2='Y2', color1='blue', color2='red',
                        linewidth=2, alpha=0.8, figsize=(12, 6), grid_alpha=0.3):
    """
    Flexible utility for dual-axis plots (supports line, bar, scatter; hist not supported for dual).
    
    Args:
        x, y1, y2: shared x-axis and two y-series
        plot_type: Type of plot ('line', 'bar', 'scatter') - default: 'line' (hist not supported)
        title: optional title
        xlabel, ylabel1, ylabel2: labels
        color1, color2: colors for each series
        linewidth: line/bar edge thickness (default: 2)
        alpha: transparency for bar/scatter (default: 0.8)
        figsize: figure size (default: (12, 6))
        grid_alpha: grid transparency (default: 0.3)
    
    Returns:
        fig, (ax1, ax2): matplotlib figure and axes for further customization
    """
    if plot_type == 'hist':
        raise ValueError("Histogram not supported for dual-axis plots. Use plot_beautiful instead.")
    
    fig, ax1 = plt.subplots(figsize=figsize)
    
    # First series on ax1
    if plot_type == 'line':
        ax1.plot(x, y1, color=color1, linewidth=linewidth, label=f'{ylabel1}')
    elif plot_type == 'bar':
        ax1.bar(np.arange(len(x)), y1, color=color1, alpha=alpha, linewidth=linewidth, 
                edgecolor='black', label=f'{ylabel1}')
        ax1.set_xticks(np.arange(len(x)))
        ax1.set_xticklabels(x)
    elif plot_type == 'scatter':
        ax1.scatter(x, y1, color=color1, alpha=alpha, s=40, linewidth=linewidth, 
                    edgecolors='black', label=f'{ylabel1}')
    else:
        raise ValueError(f"Unsupported plot_type: '{plot_type}'. Choose 'line', 'bar', or 'scatter'.")
    
    ax1.set_xlabel(xlabel, fontsize=12)
    ax1.set_ylabel(ylabel1, color=color1, fontsize=12)
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=grid_alpha, linestyle='--')
    
    # Second axis and series on ax2
    ax2 = ax1.twinx()
    if plot_type == 'line':
        ax2.plot(x, y2, color=color2, linewidth=linewidth, label=f'{ylabel2}')
    elif plot_type == 'bar':
        # Offset bars slightly for dual bars
        ax2.bar(np.arange(len(x)) + 0.35, y2, width=0.35, color=color2, alpha=alpha, linewidth=linewidth, 
                edgecolor='black', label=f'{ylabel2}')
    elif plot_type == 'scatter':
        ax2.scatter(x, y2, color=color2, alpha=alpha, s=40, linewidth=linewidth, 
                    edgecolors='black', label=f'{ylabel2}')
    
    ax2.set_ylabel(ylabel2, color=color2, fontsize=12)
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Styling
    ax1.spines['top'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    fig.suptitle(title or f'Dual {plot_type.capitalize()} Plot', fontsize=16, fontweight='bold')
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.show()
    
    return fig, (ax1, ax2)