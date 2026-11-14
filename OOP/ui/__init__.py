# UI package containing theme styling and polymorphic page view classes

from OOP.ui.ui_theme import UITheme
from OOP.ui.ui_views import (
    AnalyticsView,
    BasePageView,
    CandidatesView,
    DashboardView,
    JobPostingsView,
    OverviewWidgets,
    ResumeAnalyserView,
    SettingsView,
)

__all__ = [
    "UITheme",
    "OverviewWidgets",
    "BasePageView",
    "DashboardView",
    "AnalyticsView",
    "ResumeAnalyserView",
    "CandidatesView",
    "JobPostingsView",
    "SettingsView",
]
