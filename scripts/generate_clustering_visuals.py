import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure src directory is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from sml_engine import ProxyEngineSML

def main():
    print("=========================================================================")
    print("      RE-GENERATING HIGH-CONTRAST 4-PANEL CORPORATE PEER DASHBOARD      ")
    print("=========================================================================")
    
    # 1. Initialize SML Engine on the new precomputed baseline
    engine = ProxyEngineSML()
    df = engine.data.copy()  # Uses the real precomputed 1,156-row dataset loaded by default
    
    # Map features for clustering profiles
    features = ['toas', 'opre', 'empl', 'oppl', 'roa', 'gear']
    feature_labels = ['Total Assets (TOAS)', 'Operating Revenue (OPRE)', 'Employees (EMPL)', 'Operating Profit (OPPL)', 'ROA (%)', 'Gearing (%)']
    
    # 2. Global Rank-Percentile Mapping (0-100) across all company-years to restore high contrast!
    print("Executing Global Rank-Percentile transformation...")
    percentile_df = df.copy()
    for col in features:
        percentile_df[col] = df[col].rank(pct=True) * 100.0
        
    df['peer_label'] = df['shadow_peer_cluster'].map(lambda c: f"Peer_C{c}")
    percentile_df['peer_label'] = percentile_df['shadow_peer_cluster'].map(lambda c: f"Peer_C{c}")
    
    # Define a high-contrast corporate palette for 7 clusters
    colors = ['#1f4287', '#ff7600', '#2e7d32', '#d32f2f', '#9c27b0', '#795548', '#00bcd4']
    cluster_palette = {f"Peer_C{i}": colors[i] for i in range(7)}
    
    # Set up matplotlib figure (4-panel layout: 2x2 grid)
    sns.set_theme(style="whitegrid")
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 16))
    fig.suptitle("Outlier-Robust Peer Clustering & Global Rank-Percentile Mapping (K=7)", 
                 fontsize=18, fontweight='bold', y=0.98, color='#0f172a')
    
    # ----------------------------------------------------
    # Panel 1: Peer Clusters Scatter (OPRE vs ROA)
    # ----------------------------------------------------
    print("Generating Panel 1: Scale vs Capital Efficiency...")
    sns.scatterplot(
        data=df,
        x=np.log(df['opre']),
        y=df['roa'] * 100, # Convert to percentage
        hue='peer_label',
        palette=cluster_palette,
        s=90,
        alpha=0.8,
        edgecolors='black',
        linewidth=0.5,
        ax=ax1
    )
    ax1.set_title("Panel 1: Corporate Scale vs Capital Efficiency (OPRE vs ROA)", fontsize=13, fontweight='bold', pad=10, color='#1f4287')
    ax1.set_xlabel("Log(Operating Revenue - €)", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Return on Assets (%)", fontsize=11, fontweight='bold')
    ax1.legend(title="Peer Clusters", ncol=2, fontsize=10, title_fontsize=11, loc="upper right")
    
    # ----------------------------------------------------
    # Panel 2: Cluster Size Balance Bar Chart
    # ----------------------------------------------------
    print("Generating Panel 2: Cluster Size Distributions...")
    cluster_counts = df['peer_label'].value_counts().sort_index()
    percentages = (cluster_counts / len(df)) * 100
    
    bars = ax2.bar(
        cluster_counts.index,
        cluster_counts.values,
        color=colors[:len(cluster_counts)],
        edgecolor='black',
        linewidth=0.5
    )
    ax2.set_title("Panel 2: Cluster Size Balance & Member Counts", fontsize=13, fontweight='bold', pad=10, color='#1f4287')
    ax2.set_ylabel("Number of Companies in Cluster", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Shadow Peer Group Label", fontsize=11, fontweight='bold')
    
    # Overlay percentages on top of bars
    for bar, pct in zip(bars, percentages):
        height = bar.get_height()
        ax2.annotate(f"{pct:.1f}%",
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3),
                     textcoords="offset points",
                     ha='center', va='bottom', fontsize=10, fontweight='bold')
                     
    # ----------------------------------------------------
    # Panel 3: Risk vs Profitability Scatter (Gearing vs Operating Profit)
    # ----------------------------------------------------
    print("Generating Panel 3: Capital Risk vs Operating Profits...")
    sns.scatterplot(
        data=df,
        x=np.arcsinh(df['oppl'] / 1e6), # Pre-scaled to Millions, arcsinh transform applied
        y=df['gear'] * 100, # Percentage gearing
        hue='peer_label',
        palette=cluster_palette,
        s=90,
        alpha=0.8,
        edgecolors='black',
        linewidth=0.5,
        ax=ax3
    )
    ax3.set_title("Panel 3: Capital Risk vs Operating Profits (Gearing vs IHS Profit)", fontsize=13, fontweight='bold', pad=10, color='#1f4287')
    ax3.set_xlabel("IHS(Operating Profit - € Millions)", fontsize=11, fontweight='bold')
    ax3.set_ylabel("Gearing (%)", fontsize=11, fontweight='bold')
    ax3.legend(title="Peer Clusters", ncol=2, fontsize=10, title_fontsize=11, loc="upper left")
    
    # ----------------------------------------------------
    # Panel 4: Bounded Rank-Percentile Profiles Heatmap (Capital-IQ / Bloomberg style)
    # ----------------------------------------------------
    print("Generating Panel 4: Localized Rank-Percentile Profiles Heatmap...")
    profile = percentile_df.groupby('peer_label')[features].median()
    profile = profile.reindex(sorted(profile.index))
    
    # Render Heatmap with high-contrast color scheme
    sns.heatmap(
        profile,
        annot=True,
        fmt=".1f",
        cmap="YlGnBu",
        cbar=True,
        ax=ax4,
        linewidths=0.5,
        xticklabels=feature_labels,
        cbar_kws={'label': 'Global Rank Percentile (0 to 100)'}
    )
    ax4.set_title("Panel 4: High-Contrast Cluster Profile Heatmap (Percentiles 0-100)", fontsize=13, fontweight='bold', pad=10, color='#1f4287')
    ax4.set_ylabel("Shadow Peer Groups", fontsize=11, fontweight='bold')
    plt.setp(ax4.get_xticklabels(), rotation=35, ha="right", rotation_mode="anchor", fontsize=9)
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # Save the output image
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "step2_peer_clustering.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    
    print(f"\nSUCCESS: High-contrast 4-panel corporate peer dashboard successfully re-generated at: {output_path}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
