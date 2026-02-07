"""Merit configuration and shared resources for tests."""

import merit


@appmerit.resource
def trace_context():
    """Provide trace context for tests."""
    # Mock trace context for now - Merit will provide real one
    class TraceContext:
        def get_all_spans(self):
            return []
        
        def get_sut_spans(self, sut):
            return []
    
    return TraceContext()
