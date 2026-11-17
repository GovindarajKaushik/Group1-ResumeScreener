# Theme and CSS styling manager for the Streamlit UI

import streamlit as st


# Encapsulates the Obsidian Black, Dark Red & Cool Silver design system and CSS animations
class UITheme:

    def __init__(self):
        self._palette = {
            "bg_canvas": "#09090B",
            "bg_surface": "#121216",
            "border": "#24242B",
            "text_primary": "#F4F4F5",
            "text_muted": "#A1A1AA",
            "accent_primary": "#991B1B",
            "accent_hover": "#DC2626",
            "accent_rose": "#F87171",
            "accent_gold": "#F59E0B",
        }

    @property
    def palette(self) -> dict[str, str]:
        # return a copy of the colour tokens so callers cannot mutate internal state
        return dict(self._palette)

    def get_global_css(self) -> str:
        # build the global stylesheet for layout, cards, badges, and keyframe animations
        return """
        <style>
        :root {
            --ra-bg-canvas: #09090B;
            --ra-bg-surface: #121216;
            --ra-border: #24242B;
            --ra-text-primary: #F4F4F5;
            --ra-text-muted: #A1A1AA;
            --ra-accent-primary: #991B1B;
            --ra-accent-hover: #DC2626;
            --ra-accent-rose: #F87171;
            --ra-accent-gold: #F59E0B;
            --background-color: #09090B;
            --secondary-background-color: #121216;
            --text-color: #F4F4F5;
            --primary-color: #991B1B;
        }

        /* Clean app chrome */
        header[data-testid="stHeader"],
        #MainMenu,
        footer,
        [data-testid="stFooter"] {
            visibility: hidden !important;
            display: none !important;
        }

        .block-container {
            padding: 1.75rem 2.25rem 2.5rem 2.25rem !important;
            max-width: 1440px !important;
        }

        /* Canvas, sidebar, and typography */
        .stApp,
        [data-testid="stAppViewContainer"] {
            background-color: var(--ra-bg-canvas) !important;
            color: var(--ra-text-primary) !important;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div:first-child {
            background-color: var(--ra-bg-surface) !important;
            border-right: 1px solid var(--ra-border) !important;
            color: var(--ra-text-primary) !important;
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp label {
            color: var(--ra-text-primary);
        }

        .stCaption, [data-testid="stCaptionContainer"], .ra-muted {
            color: var(--ra-text-muted) !important;
        }

        /* Primary & hover button accents */
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"] {
            background-color: var(--ra-accent-primary) !important;
            border: 1px solid var(--ra-accent-hover) !important;
            color: var(--ra-text-primary) !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.18s ease-in-out !important;
        }

        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button[kind="primary"]:hover {
            background-color: var(--ra-accent-hover) !important;
            border-color: var(--ra-accent-rose) !important;
        }

        /* Reusable base card, pill, and divider classes */
        .ra-card,
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: var(--ra-bg-surface) !important;
            border: 1px solid var(--ra-border) !important;
            border-radius: 14px !important;
            padding: 1.35rem 1.5rem !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
            margin-bottom: 1rem !important;
        }

        .ra-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.26rem 0.72rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            background-color: rgba(153, 27, 27, 0.22);
            border: 1px solid var(--ra-accent-hover);
            color: var(--ra-accent-rose);
        }

        .ra-pill-gold {
            background-color: rgba(245, 158, 11, 0.16);
            border: 1px solid var(--ra-accent-gold);
            color: var(--ra-accent-gold);
        }

        .ra-pill-silver {
            background-color: rgba(161, 161, 170, 0.12);
            border: 1px solid var(--ra-border);
            color: var(--ra-text-muted);
        }

        .ra-divider {
            border: none;
            border-top: 1px solid var(--ra-border);
            margin: 1rem 0;
        }

        /* Sidebar brand header, nav buttons, and bottom mode box */
        .ra-brand-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.25rem 0 1.15rem 0;
            margin-bottom: 0.85rem;
            border-bottom: 1px solid var(--ra-border);
        }

        .ra-brand-badge {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background-color: var(--ra-accent-primary);
            border: 1px solid var(--ra-accent-hover);
            color: var(--ra-text-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
            flex-shrink: 0;
        }

        .ra-brand-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--ra-text-primary);
            line-height: 1.2;
        }

        .ra-brand-subtitle {
            font-size: 0.76rem;
            color: var(--ra-text-muted);
            margin-top: 0.12rem;
        }

        [data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start !important;
            text-align: left !important;
            padding: 0.55rem 0.9rem !important;
            border-radius: 10px !important;
            font-size: 0.9rem !important;
            margin-bottom: 0.15rem !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #991B1B 0%, #DC2626 100%) !important;
            border: 1px solid #DC2626 !important;
            color: #FFFFFF !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.25) !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background-color: transparent !important;
            border: 1px solid transparent !important;
            color: var(--ra-text-muted) !important;
            font-weight: 500 !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
            background-color: #1C1C22 !important;
            border-color: var(--ra-border) !important;
            color: var(--ra-text-primary) !important;
        }

        .ra-mode-box {
            margin-top: 1.75rem;
            padding: 0.8rem 0.95rem;
            border-radius: 12px;
            background-color: rgba(153, 27, 27, 0.15);
            border: 1px solid var(--ra-accent-primary);
        }

        .ra-mode-title {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.84rem;
            font-weight: 600;
            color: var(--ra-text-primary);
        }

        .ra-mode-sub {
            font-size: 0.75rem;
            color: var(--ra-text-muted);
            margin-top: 0.2rem;
        }

        /* Top split header bar */
        .ra-top-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1.25rem;
            flex-wrap: wrap;
            padding-bottom: 1.15rem;
            margin-bottom: 1.25rem;
            border-bottom: 1px solid var(--ra-border);
        }

        .ra-header-title {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--ra-text-primary);
            letter-spacing: -0.02em;
            line-height: 1.2;
            margin: 0;
        }

        .ra-header-title-accent {
            color: var(--ra-accent-rose);
        }

        .ra-header-subtitle {
            font-size: 0.9rem;
            color: var(--ra-text-muted);
            margin-top: 0.28rem;
        }

        .ra-header-controls {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            flex-wrap: wrap;
        }

        .ra-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.32rem 0.4rem 0.32rem 0.75rem;
            background-color: var(--ra-bg-surface);
            border: 1px solid var(--ra-border);
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--ra-text-primary);
        }

        .ra-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--ra-accent-rose);
            box-shadow: 0 0 8px var(--ra-accent-rose);
        }

        .ra-inline-connect-btn {
            background-color: var(--ra-accent-primary);
            border: 1px solid var(--ra-accent-hover);
            color: var(--ra-text-primary);
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
        }

        .ra-inline-connect-btn:hover {
            background-color: var(--ra-accent-hover);
        }

        .ra-refresh-btn {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background-color: var(--ra-bg-surface);
            border: 1px solid var(--ra-border);
            color: var(--ra-text-muted);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
            cursor: pointer;
        }

        .ra-refresh-btn:hover {
            border-color: var(--ra-accent-hover);
            color: var(--ra-text-primary);
        }

        .ra-updated-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.36rem 0.78rem;
            border-radius: 999px;
            background-color: var(--ra-bg-surface);
            border: 1px solid var(--ra-border);
            font-size: 0.78rem;
            color: var(--ra-text-muted);
        }

        /* Full-width status / onboarding banner card */
        .ra-status-banner {
            background:
                radial-gradient(circle at top left, rgba(153, 27, 27, 0.22), transparent 52%),
                var(--ra-bg-surface);
            border: 1px solid var(--ra-border);
            border-top: 1px solid rgba(220, 38, 38, 0.55);
            border-left: 3px solid var(--ra-accent-hover);
            border-radius: 14px;
            padding: 1.35rem 1.5rem;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.5);
            margin-bottom: 1.5rem;
        }

        .ra-banner-top {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
        }

        .ra-banner-icon {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            background-color: rgba(153, 27, 27, 0.22);
            border: 1px solid var(--ra-accent-primary);
            color: var(--ra-accent-rose);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }

        .ra-banner-heading {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--ra-text-primary);
            margin: 0;
        }

        .ra-banner-desc {
            font-size: 0.86rem;
            color: var(--ra-text-muted);
            margin-top: 0.25rem;
            line-height: 1.45;
        }

        .ra-capability-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin-top: 0.95rem;
        }

        .ra-capability-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.42rem;
            padding: 0.3rem 0.75rem;
            border-radius: 999px;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--ra-border);
            font-size: 0.79rem;
            color: var(--ra-text-primary);
        }

        .ra-capability-check {
            color: var(--ra-accent-rose);
            font-weight: 700;
        }

        .ra-banner-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .ra-setup-link {
            font-size: 0.82rem;
            color: var(--ra-accent-rose);
            text-decoration: none;
            font-weight: 500;
        }

        .ra-setup-link:hover {
            text-decoration: underline;
        }

        .ra-banner-actions {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .ra-btn-crimson {
            background-color: var(--ra-accent-hover);
            border: 1px solid var(--ra-accent-rose);
            color: #FFFFFF;
            padding: 0.42rem 0.95rem;
            border-radius: 9px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
        }

        .ra-btn-crimson:hover {
            background-color: var(--ra-accent-primary);
        }

        .ra-btn-outline {
            background-color: transparent;
            border: 1px solid var(--ra-border);
            color: var(--ra-text-primary);
            padding: 0.42rem 0.95rem;
            border-radius: 9px;
            font-size: 0.82rem;
            font-weight: 500;
            cursor: pointer;
        }

        .ra-btn-outline:hover {
            background-color: #1C1C22;
            border-color: var(--ra-text-muted);
        }

        /* 4-Column KPI Summary Row */
        .ra-kpi-card {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 142px;
            transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
        }

        .ra-kpi-card:hover {
            border-color: #991B1B !important;
            box-shadow: 0 10px 26px rgba(153, 27, 27, 0.22);
            transform: translateY(-2px);
        }

        .ra-kpi-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.05rem;
        }

        .ra-kpi-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            background-color: rgba(220, 38, 38, 0.15);
            border: 1px solid rgba(153, 27, 27, 0.65);
            color: var(--ra-text-primary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            flex-shrink: 0;
        }

        .ra-kpi-icon-solid {
            background-color: #991B1B;
            border: 1px solid #DC2626;
            color: #FFFFFF;
        }

        .ra-kpi-trend {
            display: inline-flex;
            align-items: center;
            gap: 0.28rem;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 0.22rem 0.58rem;
            border-radius: 999px;
            background-color: rgba(248, 113, 113, 0.12);
            border: 1px solid rgba(248, 113, 113, 0.32);
            color: var(--ra-accent-rose);
        }

        .ra-kpi-trend-gold {
            background-color: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.35);
            color: var(--ra-accent-gold);
        }

        .ra-kpi-value {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--ra-text-primary);
            line-height: 1.15;
            letter-spacing: -0.02em;
        }

        .ra-kpi-label {
            font-size: 0.83rem;
            color: var(--ra-text-muted);
            margin-top: 0.28rem;
            font-weight: 500;
        }

        /* Middle 2-Column Data Visualisation Row */
        .ra-chart-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.65rem;
        }

        .ra-chart-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--ra-text-primary);
            margin: 0;
        }

        .ra-chart-options {
            color: var(--ra-text-muted);
            font-size: 1.15rem;
            font-weight: 700;
            line-height: 1;
            cursor: pointer;
            padding: 0.15rem 0.35rem;
            border-radius: 6px;
        }

        .ra-chart-options:hover {
            background-color: #1C1C22;
            color: var(--ra-text-primary);
        }

        .ra-skill-legend {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.55rem 1.15rem;
            margin-top: 0.55rem;
            padding-top: 0.65rem;
            border-top: 1px solid var(--ra-border);
        }

        .ra-skill-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 0.42rem;
            font-size: 0.8rem;
            font-weight: 500;
            color: #E4E4E7;
        }

        .ra-skill-swatch {
            width: 10px;
            height: 10px;
            border-radius: 3px;
            flex-shrink: 0;
        }

        /* Bottom 2-Column Operational Row (Processing Queue & Recent Resumes) */
        .ra-op-card {
            min-height: 295px;
            display: flex;
            flex-direction: column;
        }

        .ra-op-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.9rem;
        }

        .ra-op-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: var(--ra-text-primary);
            margin: 0;
        }

        .ra-active-counter {
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            background-color: rgba(161, 161, 170, 0.1);
            border: 1px solid var(--ra-border);
            font-size: 0.76rem;
            font-weight: 600;
            color: var(--ra-text-muted);
        }

        .ra-view-all-link {
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--ra-accent-rose);
            text-decoration: none;
        }

        .ra-view-all-link:hover {
            text-decoration: underline;
        }

        .ra-queue-empty {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 2.2rem 1rem;
        }

        .ra-queue-clock {
            width: 52px;
            height: 52px;
            border-radius: 50%;
            background-color: rgba(153, 27, 27, 0.16);
            border: 1px solid rgba(153, 27, 27, 0.55);
            color: var(--ra-accent-rose);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            margin-bottom: 0.8rem;
        }

        .ra-queue-empty-title {
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--ra-text-primary);
            margin-bottom: 0.25rem;
        }

        .ra-queue-empty-sub {
            font-size: 0.8rem;
            color: var(--ra-text-muted);
            max-width: 280px;
        }

        .ra-candidate-list {
            display: flex;
            flex-direction: column;
        }

        .ra-candidate-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.85rem;
            padding: 0.72rem 0;
            border-bottom: 1px solid var(--ra-border);
        }

        .ra-candidate-row:last-child {
            border-bottom: none;
            padding-bottom: 0.2rem;
        }

        .ra-candidate-left {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 0;
        }

        .ra-avatar {
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background-color: #991B1B;
            border: 1px solid #DC2626;
            color: #F4F4F5;
            font-size: 0.82rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .ra-candidate-meta {
            min-width: 0;
        }

        .ra-candidate-file {
            font-size: 0.88rem;
            font-weight: 700;
            color: #F4F4F5;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 210px;
        }

        .ra-candidate-date {
            font-size: 0.75rem;
            color: #A1A1AA;
            margin-top: 0.12rem;
        }

        .ra-candidate-right {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            flex-shrink: 0;
        }

        .ra-score-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            font-size: 0.8rem;
            font-weight: 700;
            color: #F59E0B;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            background-color: rgba(245, 158, 11, 0.14);
            border: 1px solid rgba(245, 158, 11, 0.4);
        }

        .ra-completed-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.62rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 600;
            background-color: rgba(16, 185, 129, 0.14);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #34D399;
        }

        .ra-eye-btn {
            width: 28px;
            height: 28px;
            border-radius: 7px;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--ra-border);
            color: var(--ra-text-muted);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.82rem;
            cursor: pointer;
        }

        .ra-eye-btn:hover {
            border-color: #991B1B;
            color: #F4F4F5;
        }

        /* Page Load & View Transition Animations */
        [data-stale="true"] {
            opacity: 1 !important;
            transition: none !important;
        }

        @keyframes raHeaderSlideDown {
            0% {
                opacity: 0;
                transform: translate3d(0, -10px, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raViewEnterA {
            0% {
                opacity: 0;
                transform: translate3d(0, 14px, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raViewEnterB {
            0% {
                opacity: 0;
                transform: translate3d(0, 14px, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raRowSlideInA {
            0% {
                opacity: 0;
                transform: translate3d(-12px, 0, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raRowSlideInB {
            0% {
                opacity: 0;
                transform: translate3d(-12px, 0, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raPulseDot {
            0%, 100% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.25);
                opacity: 0.72;
            }
        }

        @keyframes raDrawSplineA {
            0% {
                stroke-dashoffset: 1000;
            }
            100% {
                stroke-dashoffset: 0;
            }
        }

        @keyframes raDrawSplineB {
            0% {
                stroke-dashoffset: 1000;
            }
            100% {
                stroke-dashoffset: 0;
            }
        }

        @keyframes raAreaFadeInA {
            0% {
                opacity: 0;
                transform: translateY(10px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes raAreaFadeInB {
            0% {
                opacity: 0;
                transform: translateY(10px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes raDotPopA {
            0% {
                opacity: 0;
                transform: scale(0.3);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes raDotPopB {
            0% {
                opacity: 0;
                transform: scale(0.3);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes raDonutSweepA {
            0% {
                opacity: 0;
                transform: rotate(-230deg) scale(0.9);
            }
            100% {
                opacity: 1;
                transform: rotate(-90deg) scale(1);
            }
        }

        @keyframes raDonutSweepB {
            0% {
                opacity: 0;
                transform: rotate(-230deg) scale(0.9);
            }
            100% {
                opacity: 1;
                transform: rotate(-90deg) scale(1);
            }
        }

        @keyframes raIconPopA {
            0% {
                opacity: 0;
                transform: scale(0.75);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes raIconPopB {
            0% {
                opacity: 0;
                transform: scale(0.75);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes raValueRiseA {
            0% {
                opacity: 0;
                transform: translate3d(0, 14px, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        @keyframes raValueRiseB {
            0% {
                opacity: 0;
                transform: translate3d(0, 14px, 0);
            }
            100% {
                opacity: 1;
                transform: translate3d(0, 0, 0);
            }
        }

        .ra-top-header {
            will-change: opacity, transform;
            backface-visibility: hidden;
            animation: raHeaderSlideDown 1.4s cubic-bezier(0.16, 1, 0.3, 1) both;
        }

        .ra-status-dot {
            animation: raPulseDot 2.8s ease-in-out infinite;
        }

        .ra-kpi-stagger-0 { animation-delay: 0.16s !important; }
        .ra-kpi-stagger-1 { animation-delay: 0.34s !important; }
        .ra-kpi-stagger-2 { animation-delay: 0.52s !important; }
        .ra-kpi-stagger-3 { animation-delay: 0.70s !important; }

        .ra-chart-stagger-0 { animation-delay: 0.58s !important; }
        .ra-chart-stagger-1 { animation-delay: 0.78s !important; }

        .ra-spline-line {
            stroke-dasharray: 1000;
            stroke-dashoffset: 1000;
        }

        .ra-spline-dot {
            transform-box: fill-box;
            transform-origin: center;
        }

        .ra-donut-ring {
            transform-origin: 110px 102px;
        }

        .ra-donut-segment {
            transition: stroke-width 0.3s ease, opacity 0.3s ease;
            cursor: pointer;
        }

        .ra-donut-segment:hover {
            stroke-width: 34;
            opacity: 0.92;
        }

        .ra-op-stagger-0 { animation-delay: 0.92s !important; }
        .ra-op-stagger-1 { animation-delay: 1.12s !important; }

        .ra-candidate-row {
            will-change: opacity, transform;
            backface-visibility: hidden;
            transition: background-color 0.25s ease, padding-left 0.25s ease;
        }

        .ra-candidate-row:nth-child(1) { animation-delay: 1.15s !important; }
        .ra-candidate-row:nth-child(2) { animation-delay: 1.35s !important; }
        .ra-candidate-row:nth-child(3) { animation-delay: 1.55s !important; }
        .ra-candidate-row:nth-child(4) { animation-delay: 1.75s !important; }

        .ra-candidate-row:hover {
            background-color: rgba(255, 255, 255, 0.02);
            padding-left: 0.35rem;
            border-radius: 8px;
        }
        </style>
        """

    def get_view_transition_css(self, nav_tick: int) -> str:
        # toggle keyframe suffix (A/B) on every navigation tick so cards, charts, and rows always replay
        suffix = "A" if int(nav_tick) % 2 == 0 else "B"
        anim_name = f"raViewEnter{suffix}"
        return f"""
        <style>
        .ra-card,
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stForm"],
        div[data-testid="stExpander"],
        section.main h2,
        section.main h3 {{
            will-change: opacity, transform;
            backface-visibility: hidden;
            animation: {anim_name} 1.75s cubic-bezier(0.16, 1, 0.3, 1) both;
        }}

        .ra-kpi-icon {{
            animation: raIconPop{suffix} 1.35s cubic-bezier(0.16, 1, 0.3, 1) 0.35s both;
        }}

        .ra-kpi-value,
        .ra-kpi-trend {{
            animation: raValueRise{suffix} 1.45s cubic-bezier(0.16, 1, 0.3, 1) 0.45s both;
        }}

        .ra-spline-line {{
            animation: raDrawSpline{suffix} 3.6s cubic-bezier(0.25, 1, 0.5, 1) 0.75s forwards;
        }}

        .ra-spline-area {{
            animation: raAreaFadeIn{suffix} 2.8s cubic-bezier(0.16, 1, 0.3, 1) 1.1s both;
        }}

        .ra-spline-dot {{
            animation: raDotPop{suffix} 1.1s cubic-bezier(0.16, 1, 0.3, 1) both;
        }}

        .ra-donut-ring {{
            animation: raDonutSweep{suffix} 3.2s cubic-bezier(0.16, 1, 0.3, 1) 0.85s both;
        }}

        .ra-skill-legend-item {{
            animation: raValueRise{suffix} 1.35s cubic-bezier(0.16, 1, 0.3, 1) 1.35s both;
        }}

        .ra-candidate-row {{
            animation: raRowSlideIn{suffix} 1.45s cubic-bezier(0.16, 1, 0.3, 1) both;
        }}
        </style>
        """

    def apply_global_styles(self):
        st.markdown(self.get_global_css(), unsafe_allow_html=True)

    def apply_view_transition(self, nav_tick: int):
        st.markdown(self.get_view_transition_css(nav_tick), unsafe_allow_html=True)
