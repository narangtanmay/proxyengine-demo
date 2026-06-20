import os
import sys

# Ensure src directory is in path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from sml_engine import ProxyEngineSML

def main():
    print("=========================================================")
    print("       PROXYENGINE ASYNCHRONOUS SML PREFITTING SCRIPT     ")
    print("=========================================================")
    
    # 1. Initialize the full panel SML engine
    print("Initializing SML engine...")
    engine = ProxyEngineSML()
    
    # 2. Run the full fitting pipeline
    print("Running multi-stage panel regressions & K-Means clustering...")
    engine.run_full_pipeline()
    
    # 3. Export parameters to JSON cache
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sml_cache.json")
    print(f"Exporting model coefficients, scaler states, and shadow peer centroids...")
    engine.save_to_cache(cache_path)
    
    print("Prefitting complete. Caching successful!")
    print("=========================================================")

if __name__ == "__main__":
    main()
