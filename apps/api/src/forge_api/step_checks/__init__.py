"""Deterministic, evidence-only step requirements.

Pure functions over the existing ``CadInspector`` read model. Nothing here calls
Onshape, an AI provider, or the lesson runtime; status is computed, never chosen
by a model. Wiring into Learn is a later, separately gated integration.
"""
