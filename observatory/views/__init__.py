from __future__ import annotations

from .dashboard import render_dashboard
from .hub import render_hub
from .option1 import render_option1
from .option2 import render_option2
from .option3 import render_option3

render_option4 = render_dashboard

__all__ = [
    "render_dashboard",
    "render_hub",
    "render_option1",
    "render_option2",
    "render_option3",
    "render_option4",
]
