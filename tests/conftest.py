import os
import sys
import pytest

# Ensure local src directory is in path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from sml_engine import ProxyEngineSML
from llm_wrapper import ProxyEngineDualLens

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "allow_fallback_mock: Allow test to hit Wizard of Oz offline fallback templates"
    )

@pytest.fixture(autouse=True)
def enforce_no_mock_fallback(request, monkeypatch):
    """Fails the test if it hits any Wizard of Oz fallback without being explicitly marked."""
    allow_fallback = request.node.get_closest_marker("allow_fallback_mock") is not None
    
    if not allow_fallback:
        def fail_on_fallback(*args, **kwargs):
            pytest.fail(
                "CRITICAL GUARDRAIL TRIGGERED: Test executed a Wizard of Oz mock fallback path "
                "but was not explicitly marked with @pytest.mark.allow_fallback_mock! "
                "This indicates that an integration-critical LLM wrapper path silently degraded to local templates."
            )
        
        monkeypatch.setattr(ProxyEngineDualLens, "_fallback_insight", fail_on_fallback)
        monkeypatch.setattr(ProxyEngineDualLens, "_generate_fallback_chat_response", fail_on_fallback)
        monkeypatch.setattr(ProxyEngineDualLens, "_fallback_auditor_report", fail_on_fallback)
        monkeypatch.setattr(ProxyEngineDualLens, "_fallback_compliance_report", fail_on_fallback)

@pytest.fixture(scope="session")
def shared_sml_engine():
    """Session-scoped fixture to fit and cache the SML engine once for the entire test run."""
    os.environ.setdefault("USE_MOCK_PANEL", "1")
    print("\n--- Fitting shared SML pipeline for test run ---")
    engine = ProxyEngineSML()
    engine.run_full_pipeline()
    return engine

@pytest.fixture(scope="session")
def shared_dual_lens():
    """Session-scoped fixture providing the Dual-Lens LLM wrapper."""
    return ProxyEngineDualLens()
