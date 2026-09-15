"""Public API for the agent.tools package.

Tools live in their own modules and are imported directly by callers, e.g.::

    from agent.tools.rename_file import rename_file
    from agent.tools.move_file import move_file

This package intentionally does NOT re-export the tool callables. Doing
``from agent.tools.rename_file import rename_file`` in this file would bind
the *function* ``rename_file`` to the attribute ``agent.tools.rename_file``,
shadowing the submodule of the same name. That breaks
``monkeypatch.setattr("agent.tools.rename_file.<X>", …)`` in the test suite,
because pytest resolves ``agent.tools.rename_file`` to the function rather
than the module.
"""