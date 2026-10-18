"""B1 natural-language Modify planner.

Turns a request into a strict A1 ``SemanticPlan`` and stops at ``prepare()``.
The model is not an authority: it can only pick opaque handles and semantic
values from a minimized catalog. It never receives, and this package never calls,
approval, the write client, provider identities or any execution capability.
"""
