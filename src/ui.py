from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from html import escape
from urllib.parse import urlencode
from uuid import uuid4

from src.hero_book import hero_book_scene_svg
from src.models import BookAssessment, BookCandidate, BookSearchEvaluation, ReadingPath
from src.profile_navigation import learning_profile_url, new_learning_profile_url


def atlas_theme_css() -> str:
    """Return the app's code-native visual system.

    The palette and spacing deliberately stay quiet so evidence, learning steps,
    and decisions—not chrome—remain the focus.
    """

    return """
    <style>
      :root {
        --atlas-ink: #0f172a;
        --atlas-ink-soft: #475569;
        --atlas-canvas: #f5f8fc;
        --atlas-surface: #ffffff;
        --atlas-surface-soft: #edf4ff;
        --atlas-line: #dce5f2;
        --atlas-accent: #1769e0;
        --atlas-accent-deep: #0b4fb3;
        --atlas-accent-bright: #69adff;
        --atlas-warning: #8a5710;
        --atlas-focus: #2563eb;
        --atlas-radius-lg: 22px;
        --atlas-radius-md: 14px;
        --atlas-shadow: 0 18px 45px rgba(30, 64, 120, .075);
        --atlas-motion-fast: 160ms;
        --atlas-motion-standard: 220ms;
      }

      *, *::before, *::after { box-sizing: border-box; }
      html { scroll-behavior: smooth; scroll-padding-top: 1rem; }
      [data-testid="stAppViewContainer"] { scroll-behavior: smooth; }
      html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
          "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      }
      html, body,
      [data-testid="stAppViewContainer"],
      [data-testid="stMain"],
      .stApp { overflow-x: hidden !important; }
      body { font-size: 16px; }

      .stApp {
        color: var(--atlas-ink);
        background:
          radial-gradient(circle at 92% 0%, rgba(88, 166, 255, .12), transparent 25rem),
          var(--atlas-canvas);
      }

      header[data-testid="stHeader"] { min-height: 0; height: 0; background: transparent; }
      [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
      [data-testid="stMainBlockContainer"] {
        max-width: 1200px;
        padding: 2.1rem 2.5rem 5rem;
      }

      .atlas-skip {
        position: fixed;
        z-index: 999999;
        top: .75rem;
        left: .75rem;
        padding: .7rem 1rem;
        border-radius: 10px;
        color: #ffffff !important;
        background: var(--atlas-ink);
        font-size: .82rem;
        font-weight: 700;
        text-decoration: none !important;
        transform: translateY(-160%);
        transition: transform var(--atlas-motion-fast) ease;
      }
      .atlas-skip:focus { transform: translateY(0); }
      .atlas-sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        clip: rect(0 0 0 0) !important;
        clip-path: inset(50%) !important;
        white-space: nowrap !important;
      }

      [data-testid="stSidebar"] {
        width: 292px !important;
        min-width: 292px !important;
        background: #0b1730;
        border-right: 1px solid rgba(255,255,255,.07);
      }
      [data-testid="stSidebarContent"] { padding: 1.3rem 1.05rem 2rem; }
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] label p,
      [data-testid="stSidebar"] .stCaption p { color: #f4f8ff !important; }
      [data-testid="stSidebar"] .stCaption p { color: #9db2cf !important; }
      [data-testid="stSidebar"] [data-baseweb="select"] > div,
      [data-testid="stSidebar"] [data-testid="stTextInput"] input {
        background: #12223d;
        border-color: #29456d;
        color: #f7faff;
      }
      [data-testid="stSidebar"] [data-testid="stButton"] button {
        width: 100%;
        min-height: 44px;
        background: #edf4ff;
        border: 0;
        color: #0f172a;
      }
      [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background: #ffffff;
        color: #0f172a;
      }

      h1, h2, h3 { color: var(--atlas-ink); letter-spacing: -.035em; }
      p { line-height: 1.65; }
      a { color: var(--atlas-accent); }
      button, summary, a, [role="button"], [role="tab"] { cursor: pointer; }
      .stCaption p { color: #64748b; }

      .atlas-brand {
        display: flex;
        align-items: center;
        gap: .7rem;
        padding: .25rem .15rem 1.35rem;
      }
      .atlas-brand-mark {
        display: block;
        position: relative;
        flex: 0 0 auto;
        overflow: hidden;
        width: 34px;
        height: 34px;
      }
      .atlas-brand-mark img,
      .atlas-brand-wordmark img { position: absolute; display: block; max-width: none !important; mix-blend-mode: multiply; }
      .atlas-brand-wordmark { position: relative; display: block; flex: 0 0 auto; overflow: hidden; width: 148px; height: 42px; }
      .atlas-brand-mark img { width: 112.6px; left: -37.2px; top: -23px; }
      .atlas-brand-wordmark img { width: 240px; left: -46.8px; top: -138.2px; }

      .atlas-side-label {
        margin: 1.25rem .1rem .55rem;
        color: #7890b0;
        font-size: .66rem;
        font-weight: 700;
        letter-spacing: .13em;
        text-transform: uppercase;
      }
      .atlas-provider {
        padding: .9rem;
        border: 1px solid #29456d;
        border-radius: 14px;
        background: rgba(255,255,255,.035);
        margin: .35rem 0 1rem;
      }
      .atlas-provider-top { display: flex; align-items: center; gap: .5rem; color: #edf5ff; font-weight: 610; font-size: .84rem; }
      .atlas-live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--atlas-accent-bright); box-shadow: 0 0 0 4px rgba(105,173,255,.12); }
      .atlas-provider-model { margin-top: .42rem; color: #93a9c7; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .69rem; overflow-wrap: anywhere; }
      .atlas-provider.offline .atlas-live-dot {
        background: #c98a2f;
        box-shadow: 0 0 0 4px rgba(201, 138, 47, .12);
      }

      .atlas-hero {
        position: relative;
        overflow: hidden;
        min-height: 400px;
        padding: 0;
        margin-bottom: 1.5rem;
        border: 1px solid #d1e2fa;
        border-radius: 24px;
        color: var(--atlas-ink);
        background:
          radial-gradient(ellipse at 85% 62%, #e4efff 0%, transparent 48%),
          linear-gradient(115deg, #ffffff 6%, #f9fbff 49%, #f0f6ff 100%);
        box-shadow: 0 16px 44px rgba(32, 72, 128, .065), inset 0 1px 0 #ffffff;
        isolation: isolate;
        container: atlas-intro / inline-size;
      }
      .atlas-hero::before {
        content: "";
        position: absolute;
        z-index: 0;
        inset: 0;
        background: radial-gradient(#7da9e0 .7px, transparent .7px);
        background-size: 22px 22px;
        opacity: .16;
        mask-image: radial-gradient(ellipse at 87% 60%, #000, transparent 46%);
        pointer-events: none;
      }
      .atlas-hero::after {
        content: "";
        position: absolute;
        z-index: 1;
        inset: 0;
        background: linear-gradient(125deg, transparent 52%, rgba(255,255,255,.6) 52.1%, transparent 71%);
        pointer-events: none;
      }
      .atlas-hero-stage {
        position: relative;
        z-index: 3;
        min-height: 400px;
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1.05fr);
        gap: 1.2rem;
        align-items: center;
        padding: 2.6rem 2.4rem 2.6rem 2.75rem;
      }
      .atlas-hero-copy-column {
        position: relative;
        z-index: 3;
        min-width: 0;
        animation: atlas-console-enter .72s cubic-bezier(.16, 1, .3, 1) both;
      }
      .atlas-eyebrow {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        gap: .55rem;
        margin-bottom: 1.6rem;
        color: var(--atlas-accent-deep);
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: .68rem;
        font-weight: 700;
        letter-spacing: .13em;
        text-transform: uppercase;
      }
      .atlas-eyebrow::before { content: ""; flex: 0 0 6px; width: 6px; height: 6px; border-radius: 50%; background: var(--atlas-accent); box-shadow: 0 0 0 4px #e8f1ff; margin-right: .25rem; }
      .atlas-hero .atlas-hero-title {
        margin: 0;
        padding: 0;
        max-width: none;
        color: #162b49;
        font-size: clamp(1.85rem, 4cqi, 3rem);
        font-weight: 650;
        line-height: 1.24;
        letter-spacing: -.045em;
      }
      .atlas-hero-title-line {
        display: block;
        white-space: nowrap;
      }
      .atlas-hero-title-line + .atlas-hero-title-line { color: #1a61c5; }
      .atlas-hero-zh {
        font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
          "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
      }
      .atlas-hero-zh .atlas-eyebrow {
        font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
        font-size: .72rem;
        font-weight: 600;
        letter-spacing: .07em;
      }
      .atlas-hero-zh .atlas-hero-title {
        font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
          "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
        font-size: clamp(1.85rem, 3.75cqi, 2.8rem);
        font-weight: 600;
        line-height: 1.42;
        letter-spacing: -.018em;
      }
      .atlas-hero .atlas-hero-copy {
        max-width: 490px;
        margin: 1.3rem 0 0;
        padding: 0;
        color: #526783;
        font-size: .94rem;
        line-height: 1.85;
        text-wrap: pretty;
      }
      .atlas-hero-zh .atlas-hero-copy { line-height: 1.95; }
      .atlas-hero-actions {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: .7rem;
        margin-top: 1.7rem;
      }
      .atlas-hero-action {
        min-height: 44px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: .45rem;
        padding: .72rem 1.05rem;
        border: 1px solid #bfd3ee;
        border-radius: 10px;
        color: #234361 !important;
        background: rgba(255,255,255,.88);
        font-size: .82rem;
        font-weight: 600;
        text-decoration: none !important;
        transition: background-color var(--atlas-motion-fast) ease, border-color var(--atlas-motion-fast) ease, box-shadow var(--atlas-motion-fast) ease;
      }
      .atlas-hero-action.primary {
        border-color: #378bff;
        color: #ffffff !important;
        background: linear-gradient(135deg, #1d75ee, #0b4fb3);
        box-shadow: 0 6px 16px rgba(23,105,224,.19), inset 0 1px 0 rgba(255,255,255,.2);
      }
      .atlas-hero-action:hover { border-color: #8fb5e8; background: #ffffff; box-shadow: 0 6px 18px rgba(45,95,158,.1); }
      .atlas-hero-action.primary:hover { border-color: #7db8ff; background: linear-gradient(135deg, #2d83f6, #0f5bc9); }
      .atlas-hero-action:focus-visible { outline: 3px solid #8bc0ff; outline-offset: 3px; }
      .atlas-hero-action svg { width: 16px; height: 16px; }

      .atlas-motion-toggle {
        position: absolute;
        width: 1px;
        height: 1px;
        overflow: hidden;
        opacity: 0;
      }
      .atlas-motion-control {
        position: absolute;
        z-index: 8;
        top: 0;
        right: 0;
        min-height: 44px;
        display: inline-flex;
        align-items: center;
        gap: .42rem;
        padding: .45rem .64rem;
        border: 1px solid #d7e5f7;
        border-radius: 10px;
        color: #466683;
        background: rgba(255,255,255,.78);
        font-family: inherit;
        font-size: .69rem;
        cursor: pointer;
        backdrop-filter: blur(10px);
        transition: color var(--atlas-motion-fast) ease, border-color var(--atlas-motion-fast) ease, background-color var(--atlas-motion-fast) ease;
      }
      .atlas-motion-control:hover { color: #155bbf; border-color: #82b7fb; background: #ffffff; }
      .atlas-motion-control svg { width: 14px; height: 14px; }
      .atlas-motion-pause,
      .atlas-motion-play { align-items: center; gap: .38rem; }
      .atlas-motion-pause { display: inline-flex; }
      .atlas-motion-play { display: none; }
      .atlas-motion-toggle:focus-visible + .atlas-motion-control { outline: 3px solid #8bc0ff; outline-offset: 3px; }
      .atlas-motion-toggle:checked + .atlas-motion-control .atlas-motion-pause { display: none; }
      .atlas-motion-toggle:checked + .atlas-motion-control .atlas-motion-play { display: inline-flex; }
      .atlas-motion-toggle:checked ~ .atlas-book-scene .atlas-book-pages,
      .atlas-motion-toggle:checked ~ .atlas-book-scene .atlas-book-leaf,
      .atlas-motion-toggle:checked ~ .atlas-book-scene * {
        animation-play-state: paused !important;
      }
      .atlas-hero-visual {
        position: relative;
        min-width: 0;
        width: 100%;
        max-width: 680px;
        display: grid;
        place-items: center;
        justify-self: center;
        padding: 1.2rem 0 0;
        animation: atlas-console-enter .82s .12s cubic-bezier(.16, 1, .3, 1) both;
      }
      .atlas-book-scene { position: relative; z-index: 3; display: block; width: 100%; height: auto; aspect-ratio: 720 / 500; overflow: visible; pointer-events: none; }
      [role="dialog"] button[aria-label="Close"] {
        min-width: 44px; min-height: 44px; border-radius: 50%;
        color: #334e72; background: rgba(230,240,255,.7);
      }
      [role="dialog"] button[aria-label="Close"]:hover { background: #dbeafe; }
      [role="dialog"] button[aria-label="Close"]:focus-visible { outline: 2px solid #1769e0; outline-offset: 2px; }
      /* Surface fills live in the SVG: do not flatten its modeled paper lighting. */
      .atlas-book-pages { transform-origin: 360px 350px; animation: atlas-book-float 9s ease-in-out infinite; }
      .atlas-book-leaf { transform-origin: 365px 350px; animation: atlas-leaf-breathe 12s ease-in-out infinite; }
      .atlas-book-link { fill: none; stroke: url(#atlasLinkGradient); stroke-width: 1; opacity: .65; }
      .atlas-book-flow { fill: none; stroke: #599af0; stroke-width: 1.3; stroke-linecap: round; stroke-dasharray: 1 18; opacity: .6; animation: atlas-data-flow 9s linear infinite; }
      .atlas-book-flow.is-slow { animation-direction: reverse; animation-duration: 12s; opacity: .35; }
      .atlas-book-orbit { transform-origin: 414px 165px; animation: atlas-orbit-drift 18s ease-in-out infinite; }
      .atlas-book-signal { animation: atlas-signal-breathe 6s ease-in-out infinite; }
      @keyframes atlas-orbit-drift { 0%, 100% { transform: rotate(-2deg); } 50% { transform: rotate(3deg); } }
      @keyframes atlas-signal-breathe { 0%, 100% { opacity: .5; } 50% { opacity: .85; } }
      @keyframes atlas-console-enter { from { opacity: 0; transform: translate3d(0, 14px, 0); } to { opacity: 1; transform: translate3d(0, 0, 0); } }
      @keyframes atlas-book-float { 0%, 100% { transform: translateY(2px); } 50% { transform: translateY(-4px); } }
      @keyframes atlas-leaf-breathe { 0%, 100% { transform: rotate(0deg) scaleY(1); } 50% { transform: rotate(-1.5deg) scaleY(1.025); } }
      @keyframes atlas-data-flow { to { stroke-dashoffset: -48; } }

      .atlas-activity-shell {
        overflow: hidden;
        margin: .2rem 0 1rem;
        border: 1px solid var(--atlas-line);
        border-radius: 18px;
        background: rgba(255,255,255,.86);
        box-shadow: var(--atlas-shadow);
      }
      .atlas-activity-summary {
        display: grid;
        grid-template-columns: minmax(0, 1.4fr) repeat(2, minmax(145px, .55fr));
        gap: .75rem;
        align-items: stretch;
        padding: 1.15rem;
        border-bottom: 1px solid var(--atlas-line);
        background: linear-gradient(135deg, #f6faf7 0%, #ffffff 72%);
      }
      .atlas-activity-intro { display: flex; gap: .8rem; align-items: flex-start; min-width: 0; }
      .atlas-activity-intro-icon {
        flex: 0 0 38px;
        width: 38px;
        height: 38px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: var(--atlas-accent);
        background: #e2f0e8;
      }
      .atlas-activity-intro-icon svg { width: 19px; height: 19px; }
      .atlas-activity-intro strong { display: block; color: var(--atlas-ink); font-size: .88rem; }
      .atlas-activity-intro span { display: block; max-width: 620px; margin-top: .3rem; color: #66756f; font-size: .73rem; line-height: 1.55; }
      .atlas-activity-stat { padding: .75rem .85rem; border: 1px solid #dde7e1; border-radius: 12px; background: #ffffff; }
      .atlas-activity-stat small { display: block; color: #77847e; font-size: .64rem; }
      .atlas-activity-stat strong { display: block; margin-top: .24rem; color: #17362c; font-size: .94rem; }
      .atlas-activity-events { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-bottom: 1px solid var(--atlas-line); }
      .atlas-activity-event { display: grid; grid-template-columns: 27px 1fr; gap: .6rem; padding: .95rem 1rem; border-right: 1px solid var(--atlas-line); }
      .atlas-activity-event:last-child { border-right: 0; }
      .atlas-activity-event-index { width: 27px; height: 27px; display: grid; place-items: center; border-radius: 50%; color: #ffffff; background: var(--atlas-accent); font-size: .61rem; font-weight: 760; }
      .atlas-activity-event strong { display: block; color: #213b32; font-size: .74rem; }
      .atlas-activity-event span { display: block; margin-top: .2rem; color: #6b7872; font-size: .67rem; line-height: 1.45; }
      .atlas-version-list { display: grid; gap: .65rem; padding: 1rem 1.15rem 1.15rem; }
      .atlas-version-heading { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
      .atlas-version-heading strong { color: var(--atlas-ink); font-size: .8rem; }
      .atlas-version-heading span { color: #78857f; font-size: .65rem; }
      .atlas-version-card { overflow: hidden; border: 1px solid #dfe7e3; border-radius: 12px; background: #fbfcfb; }
      .atlas-version-card.current { border-color: #9ebfea; background: #f3f7ff; }
      .atlas-version-card summary {
        min-height: 54px;
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto auto;
        gap: .7rem;
        align-items: center;
        padding: .7rem .85rem;
        cursor: pointer;
        list-style: none;
      }
      .atlas-version-card summary::-webkit-details-marker { display: none; }
      .atlas-version-dot { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 50%; color: var(--atlas-accent); background: #e3f0e9; }
      .atlas-version-dot svg { width: 15px; height: 15px; }
      .atlas-version-title strong { display: block; color: #17342a; font-size: .78rem; }
      .atlas-version-title small { display: block; margin-top: .12rem; color: #738079; font-size: .63rem; }
      .atlas-version-meta { color: #5e6e67; font-size: .66rem; white-space: nowrap; }
      .atlas-version-card summary > svg { width: 15px; height: 15px; transition: transform var(--atlas-motion-fast) ease; }
      .atlas-version-card[open] summary > svg { transform: rotate(90deg); }
      .atlas-version-stages { display: grid; gap: .48rem; padding: .1rem .85rem .85rem 3.75rem; }
      .atlas-version-stage { display: grid; grid-template-columns: 25px minmax(0, 1fr) auto; gap: .6rem; align-items: start; padding-top: .55rem; border-top: 1px solid #e4ebe7; }
      .atlas-version-stage > span { color: #8a9791; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .62rem; }
      .atlas-version-stage strong { display: block; color: #344b42; font-size: .7rem; line-height: 1.45; overflow-wrap: anywhere; }
      .atlas-version-stage small { color: #6f7c76; font-size: .64rem; white-space: nowrap; }

      .atlas-section-head {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 1rem;
        margin: 2.3rem 0 1rem;
      }
      .atlas-section-index { color: var(--atlas-accent); font-size: .7rem; font-weight: 760; letter-spacing: .14em; text-transform: uppercase; }
      .atlas-section-head h2 { margin: .28rem 0 0; font-size: 1.55rem; font-weight: 630; }
      .atlas-section-head h2 { max-inline-size: 28ch; text-wrap: balance; }
      .atlas-section-copy { max-width: 430px; margin: 0; color: #5d6d66; font-size: .82rem; text-align: right; text-wrap: pretty; }
      .atlas-section-head.compact { align-items: center; margin: 2.05rem 0 .85rem; }
      .atlas-section-head.compact .atlas-section-index {
        color: var(--atlas-accent-deep);
        font-size: clamp(.94rem, .9rem + .15vw, 1.02rem);
        font-weight: 780;
        line-height: 1.35;
        letter-spacing: .075em;
      }

      [data-testid="stForm"] {
        padding: 1.35rem 1.35rem .7rem;
        border: 1px solid var(--atlas-line);
        border-radius: var(--atlas-radius-lg);
        background: rgba(255,255,255,.88);
        box-shadow: var(--atlas-shadow);
      }
      [data-testid="stForm"] label p { color: #33453e; font-size: .82rem; font-weight: 600; }
      .atlas-form-kicker {
        margin: .05rem 0 .75rem;
        color: #6e7f78;
        font-size: .68rem;
        font-weight: 760;
        letter-spacing: .11em;
        text-transform: uppercase;
      }
      [data-testid="stTextInput"] input,
      [data-testid="stTextArea"] textarea,
      [data-testid="stNumberInput"] input,
      [data-baseweb="select"] > div {
        min-height: 44px;
        border-color: #dce4df !important;
        border-radius: 11px !important;
        background: #fafcfb !important;
      }
      [data-testid="stTextInput"] input:focus,
      [data-testid="stTextArea"] textarea:focus,
      [data-testid="stNumberInput"] input:focus {
        border-color: var(--atlas-accent) !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important;
      }
      [data-testid="stSidebar"] [data-testid="stTextInput"] input {
        background: #f7faf8 !important;
        border-color: #dbe6df !important;
        color: #10221c !important;
        -webkit-text-fill-color: #10221c !important;
      }
      [data-baseweb="tag"] { border-radius: 8px !important; background: #e4efff !important; color: #164f9e !important; }
      [data-testid="stFormSubmitButton"] button[kind="primary"],
      [data-testid="stButton"] button[kind="primary"],
      button[data-testid="stBaseButton-primary"] {
        min-height: 46px;
        padding: 0 1.15rem;
        border: 0;
        border-radius: 11px;
        background: var(--atlas-ink);
        color: white;
        font-weight: 650;
        box-shadow: 0 8px 18px rgba(16,34,28,.12);
      }
      [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
      [data-testid="stButton"] button[kind="primary"]:hover,
      button[data-testid="stBaseButton-primary"]:hover { background: #194f96; color: white; }
      a:focus-visible,
      button:focus-visible,
      summary:focus-visible,
      input:focus-visible,
      textarea:focus-visible,
      [role="button"]:focus-visible,
      [role="tab"]:focus-visible {
        outline: 2px solid var(--atlas-focus) !important;
        outline-offset: 3px;
      }
      [data-baseweb="select"]:focus-within > div {
        border-color: var(--atlas-focus) !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, .14) !important;
      }

      .atlas-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: .85rem 1rem;
        margin: .75rem 0;
        border: 1px solid #dce8e1;
        border-radius: 13px;
        background: #f1f8f4;
      }
      .atlas-status-name { color: #194f96; font-size: .75rem; font-weight: 760; letter-spacing: .09em; }
      .atlas-status-meta { color: #6b7b74; font-size: .76rem; }
      .atlas-status.warning { border-color: #eadfc9; background: #fbf7ed; }
      .atlas-status.warning .atlas-status-name { color: var(--atlas-warning); }

      .atlas-trace {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .55rem;
        padding: .25rem 0 .4rem;
      }
      .atlas-trace-row {
        display: grid;
        grid-template-columns: 32px 1fr;
        gap: .7rem;
        align-items: start;
        padding: .72rem;
        border-radius: 11px;
        background: #f7f9f7;
        color: #40524b;
        font-size: .78rem;
        line-height: 1.5;
      }
      .atlas-trace-step { color: var(--atlas-accent); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .7rem; font-weight: 700; }

      [data-testid="stExpander"] {
        overflow: hidden;
        border: 1px solid var(--atlas-line) !important;
        border-radius: 16px !important;
        background: rgba(255,255,255,.9);
        box-shadow: 0 8px 24px rgba(16,34,28,.035);
      }
      [data-testid="stExpander"] summary { min-height: 56px; font-weight: 640; color: var(--atlas-ink); }

      .atlas-concept-card {
        min-height: 132px;
        padding: 1rem 1.15rem 1.05rem;
        border: 1px solid var(--atlas-line);
        border-radius: 16px;
        background: var(--atlas-surface);
        box-shadow: 0 9px 28px rgba(16,34,28,.04);
      }
      .atlas-card-role { margin-top: 0; color: var(--atlas-accent); font-size: .68rem; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; }
      .atlas-card-title { margin-top: .42rem; color: var(--atlas-ink); font-size: 1rem; font-weight: 640; line-height: 1.35; }
      .atlas-card-foot { margin-top: .75rem; color: #73847d; font-size: .72rem; }

      .atlas-score-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .65rem; margin: .65rem 0 1rem; }
      .atlas-score { padding: .8rem; border: 1px solid #e2e8e4; border-radius: 12px; background: #fafcfb; }
      .atlas-score-top { display: flex; justify-content: space-between; gap: .5rem; margin-bottom: .5rem; color: #576760; font-size: .71rem; }
      .atlas-score-top strong { color: var(--atlas-ink); }
      .atlas-score-track { height: 4px; overflow: hidden; border-radius: 99px; background: #e5ebe7; }
      .atlas-score-fill { height: 100%; border-radius: inherit; background: var(--atlas-accent); }

      .atlas-buy {
        margin: 1rem 0 1.15rem;
        padding: 1rem;
        border: 1px solid #dfe8e2;
        border-radius: 14px;
        background: #f7faf8;
      }
      .atlas-buy-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .75rem; }
      .atlas-buy-title { color: var(--atlas-ink); font-size: .8rem; font-weight: 680; }
      .atlas-buy-edition { color: #708078; font-size: .69rem; }
      .atlas-buy-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .55rem; }
      .atlas-buy-link {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 44px;
        padding: .65rem .72rem;
        border: 1px solid #dbe5df;
        border-radius: 10px;
        color: #204f8f !important;
        background: white;
        font-size: .76rem;
        font-weight: 650;
        text-decoration: none !important;
        transition: border-color var(--atlas-motion-fast) ease, box-shadow var(--atlas-motion-fast) ease, background-color var(--atlas-motion-fast) ease;
      }
      .atlas-buy-link:hover {
        border-color: #8ebced;
        background: #fbfdfc;
        box-shadow: 0 6px 16px rgba(16,34,28,.06);
      }
      .atlas-external-icon { width: 15px; height: 15px; flex: 0 0 auto; }
      .atlas-buy-note { margin: .68rem 0 0; color: #73827b; font-size: .67rem; line-height: 1.55; }

      [data-testid="stMetric"] {
        padding: .7rem .78rem;
        border: 1px solid #e3e9e5;
        border-radius: 12px;
        background: #f9fbfa;
      }
      [data-testid="stMetricLabel"] p { color: #6d7c76; font-size: .72rem; }
      [data-testid="stMetricValue"] { color: var(--atlas-ink); font-size: 1.18rem; }

      [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid var(--atlas-line); }
      [data-testid="stTabs"] [data-baseweb="tab"] {
        min-height: 48px;
        padding: 0 .9rem;
        color: #64746d;
        font-size: .875rem;
        caret-color: transparent;
      }
      [data-testid="stTabs"] [aria-selected="true"] { color: var(--atlas-ink); font-weight: 650; }
      [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        top: auto !important;
        right: auto !important;
        bottom: 0 !important;
        height: 2px !important;
        background-color: var(--atlas-accent);
      }
      [data-testid="stAlert"] { border-radius: 13px; }
      hr { border-color: var(--atlas-line) !important; }

      @media (prefers-reduced-motion: reduce) {
        html { scroll-behavior: auto; }
        *, *::before, *::after {
          animation-duration: .01ms !important;
          animation-iteration-count: 1 !important;
          scroll-behavior: auto !important;
          transition-duration: .01ms !important;
        }
        .atlas-motion-control { display: none; }
        .atlas-hero *, .atlas-hero *::before, .atlas-hero *::after { animation: none !important; }
        .atlas-motion-toggle { display: none; }
      }

      .atlas-mentor-hero {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 1.25rem;
        align-items: center;
        padding: 1.3rem 1.4rem;
        margin-bottom: .85rem;
        border: 1px solid #d8e5de;
        border-radius: 15px;
        background: radial-gradient(circle at 92% 12%, rgba(207,225,247,.75), transparent 31%), linear-gradient(135deg, #fbfdff 0%, #f2f7ff 100%);
        box-shadow: 0 12px 30px rgba(20,56,44,.06);
      }
      .atlas-mentor-kicker { display: inline-flex; align-items: center; gap: .42rem; color: var(--atlas-accent); font-size: .7rem; font-weight: 760; letter-spacing: .09em; text-transform: uppercase; }
      .atlas-mentor-kicker svg { width: 16px; height: 16px; }
      .atlas-mentor-hero h3 { margin: .55rem 0 .35rem; color: #13251f; font-size: 1.25rem; }
      .atlas-mentor-hero p { max-width: 720px; margin: 0; color: #5d6d66; font-size: .87rem; line-height: 1.65; }
      .atlas-mentor-context { min-width: 180px; padding: .85rem 1rem; border: 1px solid rgba(23,105,224,.12); border-radius: 12px; background: rgba(255,255,255,.78); }
      .atlas-mentor-context span { display: block; color: #75817c; font-size: .65rem; }
      .atlas-mentor-context strong { display: block; margin: .2rem 0 .45rem; color: #19362d; font-size: .82rem; }
      .atlas-mentor-context .journey-track { height: 5px; }
      .atlas-mentor-thread { display: flex; flex-direction: column; gap: .72rem; min-height: 190px; max-height: 520px; overflow-y: auto; padding: .95rem; margin: .35rem 0 .8rem; border: 1px solid var(--journey-line); border-radius: 14px; background: #fbfcfb; }
      .atlas-mentor-empty { display: grid; place-items: center; min-height: 160px; padding: 1.2rem; color: #67756f; text-align: center; }
      .atlas-mentor-empty strong { display: block; margin-bottom: .3rem; color: #173128; }
      .atlas-mentor-message { display: flex; gap: .65rem; align-items: flex-start; max-width: 88%; }
      .atlas-mentor-message.user { align-self: flex-end; flex-direction: row-reverse; }
      .atlas-mentor-avatar { flex: 0 0 30px; width: 30px; height: 30px; display: grid; place-items: center; border-radius: 50%; color: #fff; background: var(--atlas-accent); font-size: .68rem; font-weight: 760; }
      .atlas-mentor-message.user .atlas-mentor-avatar { color: #315046; background: #e2ece7; }
      .atlas-mentor-bubble { padding: .72rem .85rem; border: 1px solid #dce6e1; border-radius: 4px 13px 13px 13px; color: #263b34; background: #fff; font-size: .82rem; line-height: 1.62; box-shadow: 0 4px 12px rgba(28,52,43,.035); }
      .atlas-mentor-message.user .atlas-mentor-bubble { border-color: #cfe1d8; border-radius: 13px 4px 13px 13px; background: #eaf4ee; }
      .atlas-mentor-action { display: grid; grid-template-columns: 18px 1fr; gap: .45rem; margin-top: .58rem; padding-top: .55rem; border-top: 1px solid #e2eaf5; color: var(--atlas-accent); font-size: .74rem; font-weight: 620; }
      .atlas-mentor-action svg { width: 16px; height: 16px; }
      .atlas-accountability-card { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: .9rem; align-items: center; padding: 1rem 1.1rem; margin: .6rem 0 1rem; border: 1px solid #dce6e1; border-radius: 14px; background: #fff; }
      .atlas-accountability-card.is-off { background: #f8fafc; }
      .atlas-accountability-icon { width: 48px; height: 48px; display: grid; place-items: center; border-radius: 16px; color: #ffffff; background: linear-gradient(145deg, #2f80ed, #155bc7); box-shadow: 0 8px 18px rgba(23,105,224,.2); }
      .atlas-accountability-card.is-off .atlas-accountability-icon { color: #64748b; background: #e8eef6; box-shadow: none; }
      .atlas-accountability-icon svg { width: 32px; height: 32px; }
      .atlas-accountability-head { display: flex; align-items: center; gap: .55rem; flex-wrap: wrap; }
      .atlas-accountability-head strong { color: #19342b; font-size: 1rem; line-height: 1.35; }
      .atlas-accountability-status { display: inline-flex; align-items: center; min-height: 24px; padding: .18rem .5rem; border-radius: 999px; color: #155bc7; background: #e8f1ff; font-size: .72rem; font-weight: 700; }
      .atlas-accountability-card.is-due .atlas-accountability-status { color: #9a4d08; background: #fff1db; }
      .atlas-accountability-card.is-off .atlas-accountability-status { color: #64748b; background: #e8eef6; }
      .atlas-accountability-detail { margin: .28rem 0 0; color: #61728a; font-size: .875rem; line-height: 1.55; }
      .atlas-accountability-next { margin: .34rem 0 0; color: #263a55; font-size: .875rem; font-weight: 650; line-height: 1.5; }
      .atlas-session-complete {
        position: relative;
        overflow: hidden;
        display: grid;
        grid-template-columns: 76px minmax(0, 1fr);
        gap: 1rem;
        align-items: center;
        padding: 1rem 1.05rem;
        margin: 0 0 .9rem;
        border: 1px solid #bfd7fa;
        border-radius: 18px;
        background: radial-gradient(circle at 92% 5%, rgba(101,169,255,.2), transparent 34%), linear-gradient(135deg, #f8fbff 0%, #eaf3ff 100%);
      }
      .atlas-session-complete::before,
      .atlas-session-complete::after { content: ""; position: absolute; border-radius: 999px; background: #65a9ff; opacity: .45; }
      .atlas-session-complete::before { width: 8px; height: 8px; top: 18px; right: 42px; }
      .atlas-session-complete::after { width: 5px; height: 5px; top: 42px; right: 78px; }
      .atlas-session-complete-mark {
        width: 68px;
        height: 68px;
        display: grid;
        place-items: center;
        border-radius: 22px;
        color: #fff;
        background: linear-gradient(145deg, #2f80ed, #155bc7);
        box-shadow: 0 12px 26px rgba(23,105,224,.24);
        animation: atlas-complete-arrive .38s cubic-bezier(.2,.8,.2,1) both;
      }
      .atlas-session-complete-mark svg { width: 48px; height: 48px; }
      .atlas-session-complete-kicker { display: block; margin-bottom: .2rem; color: #1769e0; font-size: .72rem; font-weight: 760; letter-spacing: .08em; text-transform: uppercase; }
      .atlas-session-complete h3 { margin: 0 0 .28rem; color: #14233a; font-size: 1.3rem; line-height: 1.3; letter-spacing: -.015em; }
      .atlas-session-complete p { margin: 0; color: #526986; font-size: .9rem; line-height: 1.58; }
      .atlas-session-complete-meta { display: flex; gap: .45rem; flex-wrap: wrap; margin-top: .65rem; }
      .atlas-session-complete-meta span { display: inline-flex; align-items: center; min-height: 26px; padding: .18rem .58rem; border: 1px solid #cfe0fa; border-radius: 999px; color: #315779; background: rgba(255,255,255,.76); font-size: .72rem; font-weight: 680; }
      @keyframes atlas-complete-arrive { from { opacity: 0; transform: translateY(8px) scale(.94); } to { opacity: 1; transform: translateY(0) scale(1); } }
      .atlas-companion-preview { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: .9rem; align-items: center; margin: .75rem 0 1rem; padding: .9rem 1rem; border: 1px solid #cfe0fa; border-radius: 14px; background: linear-gradient(135deg, #f8fbff 0%, #edf5ff 100%); }
      .atlas-companion-preview-mark { width: 56px; height: 56px; display: grid; place-items: center; border-radius: 18px; color: #ffffff; background: linear-gradient(145deg, #2f80ed, #155bc7); box-shadow: 0 8px 18px rgba(23,105,224,.2); }
      .atlas-companion-preview-mark svg { width: 42px; height: 42px; }
      .atlas-companion-preview strong { display: block; margin-bottom: .2rem; color: #17243a; font-size: 1rem; }
      .atlas-companion-preview p { margin: 0; color: #566b88; font-size: .875rem; line-height: 1.55; }
      .atlas-companion-preview small { display: block; margin-top: .3rem; color: #1769e0; font-size: .75rem; font-weight: 680; }
      .atlas-session-heading { margin: .85rem 0 .3rem; color: #17243a; font-size: 1rem; line-height: 1.4; }
      .st-key-atlas_mentor_workspace iframe { display: block; width: 100%; border: 0; border-radius: 14px; }
      .atlas-loop-picker { margin: 0 0 .5rem; color: #50647e; font-size: .875rem; font-weight: 690; }
      .atlas-loop-context { display: flex; flex-wrap: wrap; align-items: center; gap: .6rem 1rem; padding: .85rem 1.1rem; margin-bottom: .8rem; border: 1px solid #dbe6f7; border-radius: 14px; background: #fff; }
      .atlas-loop-context span { color: #526580; font-size: .875rem; }
      .atlas-loop-context strong { color: #17243a; font-size: 1rem; font-weight: 650; flex: 1; min-width: 150px; }
      [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .5rem; padding: .45rem; background: #eaf1fb; border: 1px solid #dbe6f7; border-radius: 14px; }
      [data-testid="stTabs"] [data-baseweb="tab"] { flex: 1 0 auto; min-height: 48px; padding: .65rem 1rem; color: #475569; border-radius: 10px; font-size: 1rem; }
      [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] { background: #fff; color: #0b4fb3; box-shadow: 0 2px 8px #163d7514; }
      [data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
      [data-testid="stTabs"] [data-baseweb="tab-panel"] { padding: 1rem 0; }
      [data-testid="stTabs"] [data-testid="stCaptionContainer"] p { font-size: .9rem !important; line-height: 1.65; color: #526580 !important; }
      [data-testid="stTabs"] [data-testid="stWidgetLabel"] p { font-size: 1rem; color: #24344d; }
      [data-testid="stTabs"] button:focus-visible { outline: 3px solid #0b4fb3; outline-offset: 3px; }
      [role="tablist"] { display: flex; gap: .5rem; padding: .45rem; background: #eaf1fb; border: 1px solid #dbe6f7; border-radius: 14px; overflow-x: auto; }
      [role="tablist"] [role="tab"] { flex: 1 0 auto; min-height: 48px; padding: .65rem 1rem; border-radius: 10px; color: #475569; text-align: center; justify-content: center; cursor: pointer; }
      [role="tablist"] [role="tab"] p { font-size: 1rem !important; margin: 0; }
      [role="tablist"] [role="tab"][aria-selected="true"] { background: #fff; color: #0b4fb3; box-shadow: 0 2px 8px #163d7514; }
      [role="tablist"] .react-aria-SelectionIndicator { display: none; }
      [role="tablist"] [role="tab"]:focus-visible { outline: 3px solid #0b4fb3; outline-offset: -3px; }
      [role="tabpanel"] [data-testid="stCaptionContainer"] p { font-size: .9rem !important; line-height: 1.65; color: #526580 !important; }
      [role="tabpanel"] [data-testid="stCaptionContainer"] { opacity: 1 !important; }
      [role="tabpanel"] [data-testid="stFormSubmitButton"] button { min-height: 44px; }
      .atlas-result-arrived { animation: atlas-result-flash 1.5s ease-out; }
      .atlas-submit-status { display: inline-block; padding: .4rem .75rem; color: #0b4fb3; font-size: .875rem; }
      @keyframes atlas-result-flash { from { background-color: #dceaff; } to { background-color: transparent; } }
      @media (prefers-reduced-motion: reduce) { .atlas-result-arrived { animation: none; } }
      [data-testid="stMarkdownContainer"] h3.atlas-tool-title { margin: .5rem 0 .35rem; padding: 0; color: #17243a; font-size: 1.375rem !important; font-weight: 650; line-height: 1.5; letter-spacing: 0; }
      .atlas-question-meta { display: flex; flex-wrap: wrap; align-items: center; gap: .7rem; margin: .1rem 0 .7rem; color: #60738c; font-size: .8rem; line-height: 1.6; }
      .atlas-question-meta strong { color: #195cb6; padding: .18rem .6rem; border-radius: 6px; background: #edf4ff; font-weight: 600; }
      .st-key-atlas_mentor_workspace [data-testid="stRadio"] label { min-height: 36px; padding: .2rem 0; }
      .st-key-atlas_mentor_workspace [data-testid="stForm"], [class*="st-key-book_mentor_"] [data-testid="stForm"] { padding: 1rem; border-color: #d9e5df; border-radius: 13px; background: #ffffff; }
      [data-testid="stForm"]:has([data-atlas-form-target="check-questions"]) { padding: .25rem 0 .5rem !important; border: 0 !important; background: transparent !important; box-shadow: none !important; }
      [data-testid="stForm"]:has([data-atlas-form-target="check-questions"]) [data-testid="stElementContainer"]:has(.atlas-sr-only) { display: none; }
      [data-testid="stForm"]:has([data-atlas-knowledge-check-form]) [role="radiogroup"] label { min-height: 44px; padding: .3rem .25rem; cursor: pointer; }
      [data-testid="stForm"]:has([data-atlas-knowledge-check-form]) [role="radiogroup"] label p { color: #334155; font-size: .94rem; font-weight: 400; line-height: 1.6; }
      [data-testid="stForm"]:has([data-atlas-knowledge-check-form]) [data-testid="stWidgetLabel"] p { font-size: .96rem; font-weight: 600; line-height: 1.75; color: #21344e; }
      [data-testid="stForm"]:has([data-atlas-knowledge-check-form]) [data-testid="stElementContainer"]:has(.atlas-sr-only) { display: none; }
      @container atlas-intro (max-width: 820px) {
        .atlas-hero-stage { padding: 2rem; gap: .8rem; }
        .atlas-hero .atlas-hero-title { font-size: clamp(1.7rem, 4cqi, 2.5rem); }
        .atlas-hero-zh .atlas-hero-title { font-size: clamp(1.65rem, 3.7cqi, 2.25rem); }
        .atlas-eyebrow { font-size: .61rem; letter-spacing: .06em; }
        .atlas-hero .atlas-hero-copy { font-size: .875rem; }
      }
      @container atlas-intro (max-width: 660px) {
        .atlas-hero-stage { grid-template-columns: minmax(0, 1fr); gap: 1rem; min-height: 0; padding: 1.75rem; }
        .atlas-hero-copy-column { max-width: 100%; }
        .atlas-hero .atlas-hero-title { font-size: clamp(1.75rem, 6.1cqi, 2.65rem); }
        .atlas-hero-zh .atlas-hero-title { font-size: clamp(1.65rem, 5.8cqi, 2.5rem); line-height: 1.5; }
        .atlas-hero-title-line { white-space: normal; }
        .atlas-hero-visual { max-width: 500px; padding-top: .8rem; }
        .atlas-motion-control { top: .3rem; right: 0; }
      }
      @media (max-width: 900px) {
        [data-testid="stSidebar"] { position: fixed !important; inset: 0 auto 0 0; z-index: 1000; }
        [data-testid="stSidebarCollapseButton"] {
          position: fixed !important;
          top: 14px !important;
          left: 198px !important;
          z-index: 1100 !important;
          display: block !important;
        }
        [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"] {
          left: 14px !important;
          transform: translateX(300px) !important;
        }
        [data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarContent"] {
          overflow: visible !important;
        }
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] {
          left: 258px !important;
          transform: none !important;
        }
        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebarCollapsedControl"] button {
          min-height: 36px !important;
          border: 1px solid var(--journey-line) !important;
          border-radius: 9px !important;
          color: var(--journey-green-deep) !important;
          background: #ffffff !important;
          box-shadow: 0 4px 12px rgba(24,45,37,.08) !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
          position: fixed !important;
          top: 15px !important;
          left: 14px !important;
          z-index: 1100 !important;
        }
        [data-testid="stMain"] { left: 0 !important; width: 100% !important; }
        [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem 4rem; }
        .atlas-hero { min-height: 0; border-radius: 22px; }
        .atlas-section-head { align-items: flex-start; flex-direction: column; }
        .atlas-section-copy { text-align: left; }
        .atlas-trace, .atlas-score-grid { grid-template-columns: 1fr 1fr; }
        .atlas-buy-grid { grid-template-columns: 1fr 1fr; }
      }
      @media (max-width: 560px) {
        [data-testid="stMainBlockContainer"] { padding: .85rem .75rem 3rem; }
        .atlas-hero { min-height: 0; border-radius: 18px; }
        .atlas-hero-stage { padding: 1.25rem; }
        .atlas-eyebrow { margin-bottom: 1rem; font-size: .59rem; letter-spacing: .12em; }
        .atlas-hero .atlas-hero-copy { font-size: .9rem; }
        .atlas-hero-visual { margin-top: .35rem; }
        .atlas-session-complete { grid-template-columns: 58px minmax(0, 1fr); padding: .9rem; }
        .atlas-session-complete-mark { width: 54px; height: 54px; border-radius: 17px; }
        .atlas-session-complete-mark svg { width: 38px; height: 38px; }
        .atlas-hero-actions { display: grid; }
        .atlas-hero-action { width: 100%; }
        .atlas-section-head { margin-top: 1.8rem; }
        .atlas-section-head h2 { font-size: 1.35rem; }
        .atlas-status, .atlas-buy-head { align-items: flex-start; flex-direction: column; }
        .atlas-trace, .atlas-score-grid, .atlas-buy-grid { grid-template-columns: 1fr; }
        [data-testid="stForm"] { padding: 1rem .85rem .45rem; }
      }

      /* Reading Journey workspace — page-specific override. */
      :root {
        --journey-bg: #f5f8fc;
        --journey-panel: #ffffff;
        --journey-sidebar: #fbfdff;
        --journey-line: #dce5f1;
        --journey-line-strong: #cbd7e7;
        --journey-text: #0f172a;
        --journey-muted: #64748b;
        --journey-green: #1769e0;
        --journey-green-deep: #0b4fb3;
        --journey-green-soft: #e8f2ff;
        --journey-warm: #eef4fc;
        --journey-shadow: 0 5px 16px rgba(30, 64, 120, .06);
      }

      .stApp { background: var(--journey-bg); }
      [data-testid="stMainBlockContainer"] {
        max-width: 1400px;
        padding: 0 1.2rem 4.5rem 1.8rem;
      }
      [data-testid="stSidebar"] {
        width: 246px !important;
        min-width: 246px !important;
        background: var(--journey-sidebar);
        border-right: 1px solid var(--journey-line);
      }
      [data-testid="stSidebarContent"] { padding: 1.25rem .9rem 1.5rem; }
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3,
      [data-testid="stSidebar"] label p { color: var(--journey-text) !important; }
      [data-testid="stSidebar"] .stCaption p { color: var(--journey-muted) !important; }
      [data-testid="stSidebar"] [data-baseweb="select"] > div,
      [data-testid="stSidebar"] [data-testid="stTextInput"] input {
        background: #ffffff !important;
        border-color: var(--journey-line) !important;
        color: var(--journey-text) !important;
        -webkit-text-fill-color: var(--journey-text) !important;
      }
      [data-testid="stSidebar"] [data-testid="stButton"] button {
        border: 1px solid var(--journey-line);
        background: #ffffff;
        color: var(--journey-text);
        box-shadow: none;
      }
      [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        border-color: #b9c8c0;
        background: #f5f8f6;
        color: var(--journey-green-deep);
      }
      .atlas-brand { margin-left: -.75rem; padding: .15rem .45rem 2.45rem; gap: .55rem; }
      .atlas-brand-mark { width: 42px; height: 42px; }
      .atlas-side-label { color: #6b726f; margin: 1.1rem .25rem .5rem; }
      .atlas-provider {
        border-color: var(--journey-line);
        background: #ffffff;
        box-shadow: none;
      }
      .atlas-provider-top { color: var(--journey-text); }
      .atlas-provider-model { color: #68716d; }
      .atlas-live-dot { background: var(--journey-green); box-shadow: 0 0 0 4px rgba(23,105,224,.09); }

      .atlas-new-profile {
        display: flex; align-items: center; justify-content: center; gap: .55rem;
        min-height: 46px; padding: .65rem .75rem; margin: .25rem -.6rem .9rem;
        border: 1px solid #aecbf3; border-radius: 10px;
        background: #edf4ff; color: var(--atlas-accent-deep) !important;
        font-size: .88rem; font-weight: 600; text-decoration: none !important;
        cursor: pointer; transition: background-color var(--atlas-motion-fast) ease;
      }
      .atlas-new-profile:hover { background: #deebff; border-color: var(--atlas-accent); }
      .atlas-new-profile:focus-visible, .atlas-profile-return:focus-visible {
        outline: 3px solid var(--atlas-focus); outline-offset: 3px;
      }
      .atlas-new-profile svg { width: 18px; height: 18px; flex: 0 0 auto; }
      .atlas-mobile-profile-action { grid-column: 1 / -1; padding: .25rem .75rem; }
      .atlas-mobile-profile-action .atlas-new-profile { margin: .25rem 0; }
      .atlas-profile-return {
        display: inline-flex; align-items: center; min-height: 44px;
        gap: .6rem; margin-bottom: 1rem; padding: .5rem .85rem;
        border: 1px solid var(--atlas-line); border-radius: 9px;
        background: var(--atlas-surface); color: var(--atlas-accent-deep) !important;
        font-size: .9rem; text-decoration: none !important; overflow-wrap: anywhere;
      }
      .atlas-profile-return svg { width: 18px; height: 18px; flex: 0 0 auto; }
      .atlas-profile-return:hover { background: var(--atlas-surface-soft); }
      .atlas-side-nav { display: grid; gap: .22rem; margin: .15rem -.6rem 1.2rem; }
      .atlas-side-nav a {
        min-height: 50px;
        display: flex;
        align-items: center;
        gap: 1.25rem;
        padding: .55rem .7rem;
        border-radius: 9px;
        color: #252d30 !important;
        font-size: .88rem;
        font-weight: 520;
        text-decoration: none !important;
        transition: background-color var(--atlas-motion-fast) ease, color var(--atlas-motion-fast) ease;
      }
      .atlas-side-nav a:hover { background: #eef2ef; color: var(--journey-green-deep) !important; }
      .atlas-side-nav a[aria-current="page"],
      .atlas-side-nav a[aria-current="location"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #0d4da8, #123d7c);
        box-shadow: 0 5px 12px rgba(11,79,179,.12);
      }
      .atlas-side-nav svg { width: 20px; height: 20px; flex: 0 0 auto; }
      .atlas-side-divider { height: 1px; margin: .45rem .5rem; background: var(--journey-line); }
      .atlas-side-profile {
        display: block;
        min-height: 0;
        margin: 5.85rem -.55rem 1rem;
        padding: .7rem;
        border: 1px solid var(--journey-line);
        border-radius: 10px;
        background: #ffffff;
      }
      .atlas-side-profile-main { display: flex; align-items: center; gap: .65rem; }
      .atlas-side-profile .atlas-avatar { width: 34px; height: 34px; }
      .atlas-side-profile strong { display: block; max-width: 135px; overflow: hidden; color: var(--journey-text); font-size: .74rem; text-overflow: ellipsis; white-space: nowrap; }
      .atlas-side-profile small { display: block; margin-top: .15rem; color: #737a77; font-size: .61rem; }
      .atlas-side-reading { margin-top: .72rem; padding-top: .68rem; border-top: 1px solid var(--journey-line); }
      .atlas-side-reading-row { display: flex; align-items: center; justify-content: space-between; gap: .5rem; color: #616865; font-size: .61rem; }
      .atlas-side-reading-row strong { color: #2b3332; font-size: .66rem; }
      .atlas-side-reading .journey-track { height: 4px; margin-top: .48rem; }

      .atlas-mobile-nav { display: none; }

      .atlas-topbar {
        min-height: 78px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: -2rem -1.8rem .78rem -1.8rem;
        padding: .9rem 1.8rem;
        border-bottom: 1px solid var(--journey-line);
        background: rgba(255,254,252,.91);
      }
      [data-testid="stMainBlockContainer"] { position: relative; }
      .atlas-native-search-slot { width: min(395px, 48vw); min-height: 44px; margin-left: .7rem; }
      .st-key-atlas_global_search {
        position: absolute;
        z-index: 1200;
        top: .9rem;
        left: .7rem;
        width: min(395px, 48vw);
        margin: 0 !important;
      }
      .st-key-atlas_global_search [data-testid="stForm"] {
        position: relative;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
      }
      .st-key-atlas_global_search [data-testid="stTextInput"] { margin: 0 !important; }
      .st-key-atlas_global_search [data-baseweb="input"],
      .st-key-atlas_global_search [data-testid="stTextInputRootElement"] {
        min-height: 44px;
        border: 1px solid #d6d8d3 !important;
        border-radius: 9px !important;
        background: #ffffff !important;
        box-shadow: none !important;
      }
      .st-key-atlas_global_search [data-baseweb="input"]:focus-within,
      .st-key-atlas_global_search [data-testid="stTextInputRootElement"]:focus-within {
        border-color: var(--journey-green) !important;
        box-shadow: 0 0 0 3px rgba(23,105,224,.11) !important;
      }
      .st-key-atlas_global_search input {
        min-height: 42px !important;
        color: #111b1f !important;
        -webkit-text-fill-color: #111b1f !important;
        caret-color: var(--journey-green);
        background: #ffffff !important;
        font-size: .84rem !important;
      }
      .st-key-atlas_global_search input:focus {
        border: 0 !important;
        outline: 0 !important;
        box-shadow: none !important;
      }
      .st-key-atlas_global_search input::placeholder { color: #777d7c !important; opacity: 1 !important; }
      .st-key-atlas_global_search [data-testid="stFormSubmitButton"] {
        width: 100%;
        margin: 0;
        white-space: nowrap !important;
      }
      .st-key-atlas_global_search [data-testid="stFormSubmitButton"] button { min-height: 44px; padding: .45rem .55rem; }
      .st-key-atlas_global_search [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem; }
      .st-key-atlas_global_search [data-testid="stColumn"] { min-width: 0 !important; }
      .atlas-search-wrap {
        position: relative;
        width: min(395px, 48vw);
        margin-left: .7rem;
      }
      .atlas-search-shell {
        width: 100%;
        min-height: 44px;
        display: flex;
        align-items: center;
        gap: .65rem;
        padding: 0 .9rem;
        border: 1px solid #d6d8d3;
        border-radius: 9px;
        background: #ffffff;
        color: #747a79;
      }
      .atlas-search-shell input {
        width: 100%;
        border: 0;
        outline: 0;
        color: #111b1f !important;
        -webkit-text-fill-color: #111b1f !important;
        caret-color: var(--atlas-accent);
        opacity: 1 !important;
        background: transparent;
        font: inherit;
        appearance: none;
        -webkit-appearance: none;
      }
      .atlas-search-shell input::placeholder { color: #777d7c; opacity: 1; }
      .atlas-search-shell:focus-within { border-color: var(--journey-green); box-shadow: 0 0 0 3px rgba(23,105,224,.11); }
      .atlas-search-shell svg { width: 19px; height: 19px; flex: 0 0 auto; color: #333b3c; }
      .atlas-search-results {
        position: absolute;
        z-index: 1200;
        top: calc(100% + .5rem);
        right: 0;
        left: 0;
        max-height: 340px;
        overflow-y: auto;
        padding: .38rem;
        border: 1px solid #d9ded9;
        border-radius: 11px;
        background: #ffffff;
        box-shadow: 0 18px 42px rgba(20, 35, 29, .14);
      }
      .atlas-search-results[hidden] { display: none; }
      .atlas-search-option {
        width: 100%;
        min-height: 50px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .9rem;
        padding: .68rem .72rem;
        border: 0;
        border-radius: 8px;
        color: var(--journey-text);
        background: transparent;
        font: inherit;
        text-align: left;
        cursor: pointer;
      }
      .atlas-search-option:hover,
      .atlas-search-option.active,
      .atlas-search-option:focus-visible {
        background: #edf5f0;
      }
      .atlas-search-option:focus-visible {
        outline: 2px solid var(--atlas-focus);
        outline-offset: -2px;
      }
      .atlas-search-result-label {
        min-width: 0;
        overflow: hidden;
        font-size: .79rem;
        font-weight: 650;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .atlas-search-result-type {
        flex: 0 0 auto;
        color: #69736f;
        font-size: .68rem;
      }
      .atlas-search-empty {
        padding: .82rem .78rem;
        color: #59645f;
        font-size: .75rem;
        line-height: 1.45;
      }
      .atlas-search-agent-option { background: #f2f7f4; }
      .atlas-search-agent-option .atlas-search-result-label { color: var(--journey-green-deep); }
      .atlas-search-agent-option .atlas-search-result-type {
        padding: .18rem .42rem;
        border-radius: 99px;
        color: var(--journey-green-deep);
        background: #dcece3;
        font-weight: 700;
        letter-spacing: .04em;
      }

      .atlas-book-fit {
        margin: .8rem 0 1.35rem;
        overflow: hidden;
        border: 1px solid var(--journey-line);
        border-radius: 16px;
        background: var(--journey-panel);
        box-shadow: var(--journey-shadow);
      }
      .atlas-book-fit-head {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: 1.5rem;
        padding: 1.55rem 1.65rem 1.35rem;
        border-bottom: 1px solid var(--journey-line);
      }
      .atlas-book-fit-identity {
        display: grid;
        grid-template-columns: 92px minmax(0, 1fr);
        align-items: center;
        gap: 1.15rem;
        min-width: 0;
      }
      .atlas-book-fit-title-wrap { min-width: 0; }
      .atlas-cover-card {
        position: relative;
        width: min(100%, 164px);
        margin: 0;
        aspect-ratio: 2 / 3;
        overflow: hidden;
        border: 1px solid rgba(23, 105, 224, .17);
        border-radius: 10px;
        background: linear-gradient(150deg, #1c6ed0 0%, #1556ad 47%, #0b2f6b 100%);
        box-shadow: 0 10px 24px rgba(18, 47, 39, .16);
        isolation: isolate;
      }
      .atlas-cover-card--fit { width: 92px; border-radius: 8px; box-shadow: 0 7px 18px rgba(18, 47, 39, .14); }
      .atlas-cover-card--detail { margin: .15rem auto 1rem; }
      .atlas-cover-placeholder {
        position: absolute;
        inset: 0;
        z-index: 0;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 13% 11%;
        color: rgba(255,255,255,.94);
        background:
          radial-gradient(circle at 76% 25%, rgba(105, 173, 255, .24), transparent 31%),
          linear-gradient(150deg, #1c6ed0 0%, #1556ad 52%, #0b2f6b 100%);
      }
      .atlas-cover-monogram { font-family: Georgia, serif; font-size: 1.35rem; line-height: 1; }
      .atlas-cover-placeholder strong {
        display: -webkit-box;
        overflow: hidden;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(.68rem, 1vw, .92rem);
        font-weight: 500;
        line-height: 1.2;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 5;
      }
      .atlas-cover-image {
        position: absolute;
        inset: 0;
        z-index: 1;
        width: 100%;
        height: 100%;
        display: block;
        object-fit: contain !important;
        background: #edf0ec;
      }
      .atlas-book-fit-kicker {
        display: flex;
        align-items: center;
        gap: .45rem;
        margin-bottom: .55rem;
        color: var(--journey-green);
        font-size: .66rem;
        font-weight: 760;
        letter-spacing: .1em;
        text-transform: uppercase;
      }
      .atlas-book-fit-kicker svg { width: 16px; height: 16px; }
      .atlas-book-fit h2 { margin: 0; color: var(--journey-text); font-size: 1.55rem; letter-spacing: -.025em; }
      .atlas-book-fit-meta { margin: .38rem 0 0; color: var(--journey-muted); font-size: .77rem; }
      .atlas-book-fit-score {
        --fit-score: 0;
        width: 104px;
        height: 104px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        background: conic-gradient(var(--journey-green) calc(var(--fit-score) * 1%), #e6e9e5 0);
      }
      .atlas-book-fit-score::before {
        width: 82px;
        height: 82px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: var(--journey-text);
        background: var(--journey-panel);
        content: attr(data-score);
        font-size: 1.15rem;
        font-weight: 760;
      }
      .atlas-book-fit-body { display: grid; grid-template-columns: 1.1fr .9fr; gap: 1.4rem; padding: 1.35rem 1.65rem 1.5rem; }
      .atlas-book-fit-verdict {
        display: inline-flex;
        align-items: center;
        min-height: 28px;
        margin-bottom: .72rem;
        padding: .25rem .58rem;
        border-radius: 99px;
        color: var(--journey-green-deep);
        background: #e4f0e8;
        font-size: .69rem;
        font-weight: 720;
      }
      .atlas-book-fit-copy { margin: 0; color: #3f4a47; font-size: .82rem; line-height: 1.65; }
      .atlas-book-fit-role { margin: .72rem 0 0; color: #60706a; font-size: .72rem; }
      .atlas-book-fit-role strong { color: var(--journey-text); }
      .atlas-book-fit-scores { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .55rem; }
      .atlas-book-fit-source-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
      .atlas-book-fit-source {
        display: inline-flex;
        align-items: center;
        min-height: 38px;
        padding: .5rem .7rem;
        border: 1px solid #dbe2dd;
        border-radius: 9px;
        color: #29456d !important;
        background: #fff;
        font-size: .71rem;
        font-weight: 650;
        text-decoration: none !important;
      }
      .atlas-book-fit-notes { margin: 1rem 0 0; padding: .85rem 1rem; border-radius: 10px; color: #5f4c2c; background: #fbf6e9; font-size: .72rem; line-height: 1.55; }
      .atlas-book-fit-trace { display: grid; gap: .48rem; margin-top: 1rem; }
      .atlas-book-fit-step { display: grid; grid-template-columns: 8px 1fr; gap: .55rem; color: #66736e; font-size: .69rem; line-height: 1.45; }
      .atlas-book-fit-step::before { width: 7px; height: 7px; margin-top: .25rem; border-radius: 50%; background: var(--journey-green); content: ""; }
      .atlas-book-fit-foot {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: .9rem 1.65rem;
        border-top: 1px solid var(--journey-line);
        color: #6a7672;
        font-size: .68rem;
      }
      .atlas-book-fit-foot a { color: var(--journey-green-deep) !important; font-weight: 680; text-decoration: none !important; }
      .atlas-top-actions { display: flex; align-items: center; gap: 1.15rem; transform: translateX(-.5rem); }
      .atlas-top-actions svg { width: 21px; height: 21px; color: #283032; }
      .atlas-avatar {
        width: 40px;
        height: 40px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: #ffffff;
        background: var(--journey-green-deep);
        font-size: .78rem;
        font-weight: 700;
      }

      .journey-page { color: var(--journey-text); }
      .journey-page-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: 0 1rem -.1875rem;
      }
      .journey-page-title { margin: 0; font-size: 2rem; font-weight: 660; letter-spacing: -.035em; }
      .journey-week { display: flex; align-items: center; gap: .65rem; color: #222a2c; font-size: .82rem; font-weight: 650; }
      .journey-week svg { width: 19px; height: 19px; }
      .journey-panel {
        border: 1px solid var(--journey-line);
        border-radius: 12px;
        background: var(--journey-panel);
        box-shadow: var(--journey-shadow);
      }

      .journey-stages {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .5rem;
        margin-bottom: 1.5rem;
        padding: 1.85rem 1.35rem;
      }
      .journey-stage {
        display: grid;
        grid-template-columns: 34px 52px 1fr;
        align-items: center;
        gap: .65rem;
        min-width: 0;
        min-height: 76px;
        padding: .42rem;
        border: 1px solid transparent;
        border-radius: 10px;
        color: inherit !important;
        text-decoration: none !important;
        transition: background-color var(--atlas-motion-fast) ease, border-color var(--atlas-motion-fast) ease, box-shadow var(--atlas-motion-fast) ease;
      }
      .journey-stage:hover { border-color: #d3e1da; background: #f7faf8; box-shadow: 0 6px 16px rgba(16,50,38,.05); }
      .journey-stage:focus-visible { outline: 3px solid rgba(23,105,224,.3); outline-offset: 2px; }
      .journey-stage.selected { border-color: #7890b0; background: #f3f7ff; }
      .journey-stage-number {
        width: 34px;
        height: 34px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: #6d7371;
        background: #f2f1ed;
        font-size: .78rem;
        font-weight: 700;
      }
      .journey-stage.active .journey-stage-number { color: #ffffff; background: var(--journey-green); }
      .journey-stage.complete:not(.active) .journey-stage-number { color: var(--journey-green-deep); background: #e4efff; }
      .journey-stage-icon {
        width: 52px;
        height: 52px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: #323b3b;
        background: #f4f2ee;
      }
      .journey-stage.active .journey-stage-icon { color: var(--journey-green); background: var(--journey-green-soft); }
      .journey-stage.selected:not(.active) .journey-stage-icon { color: var(--journey-green-deep); background: var(--journey-green-soft); }
      .journey-stage-icon svg { width: 25px; height: 25px; }
      .journey-stage-copy { min-width: 0; }
      .journey-stage-title {
        display: -webkit-box;
        min-height: 2.45em;
        overflow: hidden;
        color: #1c2325;
        font-size: .87rem;
        font-weight: 570;
        line-height: 1.22;
        overflow-wrap: anywhere;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
      }
      .journey-stage-status { display: block; margin-top: .22rem; color: #6d7b75; font-size: .61rem; font-weight: 650; }
      .journey-stage.active .journey-stage-status,
      .journey-stage.selected .journey-stage-status { color: var(--journey-green-deep); }
      .journey-track { height: 5px; overflow: hidden; margin-top: .72rem; border-radius: 999px; background: #e7e6e2; }
      .journey-track { display: block; width: 100%; }
      .journey-track span { display: block; height: 100%; border-radius: inherit; background: #cfd1cb; }
      .journey-stage.active .journey-track span { background: linear-gradient(90deg, var(--journey-green), #69adff); }
      .journey-stage.complete .journey-track span { background: #78aef0; }
      .journey-stage-context {
        grid-column: 1 / -1;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        margin: .65rem .4rem -.65rem;
        padding: .7rem .85rem;
        border-radius: 9px;
        color: #315247;
        background: #edf5f0;
        font-size: .7rem;
        line-height: 1.45;
      }
      .journey-stage-context a { flex: 0 0 auto; color: #0b57c7 !important; font-weight: 700; text-decoration: none !important; }
      .journey-stage-context a:hover { text-decoration: underline !important; }

      .journey-primary-grid { display: grid; grid-template-columns: minmax(0, 2.08fr) minmax(280px, 1fr); gap: 1.8rem; }
      .journey-current { overflow: hidden; }
      .journey-current-body { display: grid; grid-template-columns: 232px 1fr; gap: 2.1rem; padding: 1.35rem; }
      .journey-cover {
        position: relative;
        min-height: 0;
        height: 322px;
        align-self: start;
        overflow: hidden;
        padding: 1.15rem;
        border-radius: 8px;
        color: #fffaf0;
        background: linear-gradient(155deg, #0d4da8 0%, #2379dc 42%, #88bdf6 100%);
        box-shadow: 0 5px 12px rgba(10,40,31,.16);
      }
      .journey-cover-title {
        position: relative;
        z-index: 2;
        max-inline-size: 8ch;
        font-family: Georgia, "Songti SC", SimSun, serif;
        font-size: clamp(1.65rem, 2.45vw, 2.28rem);
        line-height: 1.02;
        letter-spacing: -.035em;
        text-wrap: balance;
      }
      .journey-cover-art { position: absolute; inset: 33% -4% -3% -4%; }
      .journey-cover-art svg { width: 100%; height: 100%; }
      .journey-cover-image {
        position: absolute;
        inset: 0;
        z-index: 3;
        width: 100%;
        height: 100%;
        object-fit: contain !important;
        background: #eef2ef;
      }
      .journey-current-copy { min-width: 0; padding: .35rem 0; }
      .journey-kicker {
        display: inline-flex;
        padding: .22rem .42rem;
        border-radius: 5px;
        color: var(--journey-green-deep);
        background: var(--journey-green-soft);
        font-size: .64rem;
        font-weight: 750;
        letter-spacing: .035em;
        text-transform: uppercase;
      }
      .journey-book-title {
        margin: .6rem 0 .25rem;
        font-family: Georgia, "Songti SC", SimSun, serif;
        font-size: clamp(2rem, 3.2vw, 3.25rem);
        font-weight: 500;
        line-height: 1.02;
        letter-spacing: -.045em;
        text-wrap: balance;
      }
      .journey-authors { margin-top: .35rem; color: #6d7672; font-size: .76rem; line-height: 1.45; }
      .journey-narratives { display: grid; gap: .78rem; margin-top: 1rem; }
      .journey-overview,
      .journey-why { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: .75rem; }
      .journey-overview-icon,
      .journey-why-icon {
        width: 36px;
        height: 36px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: var(--journey-green);
        background: var(--journey-green-soft);
      }
      .journey-overview-icon svg,
      .journey-why-icon svg { width: 19px; height: 19px; }
      .journey-overview strong,
      .journey-why strong { display: block; margin-bottom: .32rem; font-size: .84rem; }
      .journey-narrative-copy,
      .journey-narrative-preview,
      .journey-narrative-full { margin: 0; color: #3f4645; font-size: .78rem; line-height: 1.58; }
      .journey-narrative-disclosure { margin: 0; }
      .journey-narrative-disclosure summary { display: block; min-height: 0; list-style: none; color: inherit; font-weight: 400; }
      .journey-narrative-disclosure summary::-webkit-details-marker { display: none; }
      .journey-narrative-preview { display: block; }
      .journey-narrative-action {
        display: inline-flex;
        align-items: center;
        gap: .18rem;
        min-height: 28px;
        margin-top: .18rem;
        color: var(--journey-green-deep);
        font-size: .7rem;
        font-weight: 680;
      }
      .journey-narrative-action svg { width: 14px; height: 14px; transition: transform 160ms ease; }
      .journey-narrative-less-label { display: none; }
      .journey-narrative-disclosure[open] .journey-narrative-preview,
      .journey-narrative-disclosure[open] .journey-narrative-more-label { display: none; }
      .journey-narrative-disclosure[open] .journey-narrative-less-label { display: inline; }
      .journey-narrative-disclosure[open] .journey-narrative-action svg { transform: rotate(90deg); }
      .journey-narrative-full { margin-top: .25rem; max-inline-size: 65ch; }
      .journey-current-copy.zh .journey-overview p,
      .journey-current-copy.zh .journey-why p { max-inline-size: 390px; }
      .journey-confidence { display: flex; align-items: center; gap: .55rem; margin-top: 1rem; padding-top: .85rem; border-top: 1px solid var(--journey-line); font-size: .82rem; }
      .journey-confidence svg { width: 22px; height: 22px; color: var(--journey-green); }
      .journey-confidence strong { color: var(--journey-green); }
      .journey-source-pills { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: .85rem; }
      .journey-source-pill {
        min-height: 38px;
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .42rem .68rem;
        border: 1px solid var(--journey-line);
        border-radius: 8px;
        color: #293032 !important;
        background: #ffffff;
        font-size: .72rem;
        text-decoration: none !important;
      }
      .journey-source-pill:hover { border-color: #aec1b7; background: #f7faf8; }
      .journey-source-pill svg { width: 16px; height: 16px; }
      .journey-source-pill.more { border-color: transparent; color: var(--journey-green-deep) !important; background: var(--journey-green-soft); }
      .journey-current-foot { display: grid; grid-template-columns: auto 1fr auto auto auto; align-items: center; gap: .7rem; padding: .85rem 1.3rem; border-top: 1px solid var(--journey-line); font-size: .75rem; }
      .journey-current-foot strong { font-size: .88rem; }
      .journey-continue,
      .journey-mentor-link {
        min-height: 44px;
        display: inline-flex;
        align-items: center;
        gap: .55rem;
        padding: 0 .85rem;
        border-radius: 8px;
        font-size: .74rem;
        font-weight: 650;
        text-decoration: none !important;
      }
      .journey-continue { color: #ffffff !important; background: var(--journey-green); }
      .journey-continue:hover { background: var(--journey-green-deep); }
      .journey-mentor-link { color: var(--journey-green-deep) !important; border: 1px solid #b9cfc4; background: #ffffff; }
      .journey-mentor-link:hover { border-color: #82aae0; background: #f4f8ff; }
      .journey-continue svg,
      .journey-mentor-link svg { width: 16px; height: 16px; }

      .journey-learner { padding: 1.15rem; }
      .journey-panel-title { display: flex; align-items: center; gap: .65rem; font-size: .9rem; font-weight: 680; }
      .journey-panel-title .journey-title-icon {
        width: 36px;
        height: 36px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        color: var(--journey-green);
        background: var(--journey-green-soft);
      }
      .journey-panel-title svg { width: 19px; height: 19px; }
      .journey-model-summary { display: grid; grid-template-columns: 74px 1fr; align-items: center; gap: .9rem; padding: 1.1rem .2rem 1.15rem; border-bottom: 1px solid var(--journey-line); }
      .journey-ring {
        --value: 62%;
        width: 70px;
        height: 70px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        background: conic-gradient(var(--journey-green) var(--value), #e5e3de 0);
      }
      .journey-ring::before { content: ""; width: 60px; height: 60px; border-radius: 50%; background: var(--journey-panel); }
      .journey-ring strong { position: absolute; font-size: .8rem; }
      .journey-model-summary strong { display: block; font-size: .8rem; line-height: 1.35; }
      .journey-model-summary span { color: #68706e; font-size: .71rem; }
      .journey-model-list { display: grid; gap: 1rem; padding: 1.1rem .2rem .35rem; }
      .journey-model-row { display: grid; grid-template-columns: 22px 1fr auto; align-items: center; gap: .65rem; }
      .journey-model-row > svg { width: 21px; height: 21px; color: #4f5756; }
      .journey-model-label { display: block; margin-bottom: .38rem; font-size: .74rem; }
      .journey-model-value { color: #5c6462; font-size: .67rem; }
      .journey-model-row .journey-track { margin-top: 0; }

      .journey-sources { height: 148px; margin-top: 1.4rem; padding: 1.3rem 1.15rem .85rem; }
      .journey-sources-title { margin-bottom: .65rem; font-size: .9rem; font-weight: 680; line-height: 1.2; }
      .journey-source-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .6rem; }
      .journey-source-card {
        min-height: 64px;
        display: grid;
        grid-template-columns: 36px 1fr auto;
        align-items: center;
        gap: .6rem;
        padding: .65rem;
        border: 1px solid var(--journey-line);
        border-radius: 8px;
        color: #1e2628 !important;
        background: #ffffff;
        text-decoration: none !important;
      }
      .journey-source-card:hover { border-color: #abc0b5; background: #fafcfb; }
      .journey-source-initial { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 50%; color: var(--journey-green-deep); background: var(--journey-green-soft); font-size: .78rem; font-weight: 750; }
      .journey-source-name { overflow: hidden; display: block; font-size: .78rem; font-weight: 620; text-overflow: ellipsis; white-space: nowrap; }
      .journey-source-meta { display: block; margin-top: .2rem; color: #777d7b; font-size: .68rem; }
      .journey-source-card > svg { width: 16px; height: 16px; }

      .journey-brief-intro { margin: 1.5rem 0 1rem; }
      .journey-brief-intro h1 { margin: 0; font-size: 2rem; }
      .journey-brief-intro p { max-width: 680px; color: var(--journey-muted); }
      .st-key-atlas_goal_editor { margin-top: 1.25rem; }
      .st-key-atlas_goal_editor > [data-testid="stVerticalBlock"] { gap: .7rem; }
      .atlas-goal-entry {
        min-height: 96px;
        display: grid;
        grid-template-columns: 48px minmax(0, 1fr) auto;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.15rem;
        border: 1px solid #c8dcf8;
        border-radius: 16px;
        background: linear-gradient(118deg, #ffffff 0%, #f5f9ff 62%, #edf5ff 100%);
        box-shadow: 0 10px 28px rgba(28, 83, 153, .08);
      }
      .atlas-goal-entry-icon {
        width: 48px;
        height: 48px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        color: #1769e0;
        background: #e8f2ff;
      }
      .atlas-goal-entry-icon svg { width: 23px; height: 23px; }
      .atlas-goal-entry-copy { min-width: 0; }
      .atlas-goal-entry-copy > span {
        display: block;
        color: #1769e0;
        font-size: .7rem;
        font-weight: 760;
        letter-spacing: .08em;
        line-height: 1.2;
        text-transform: uppercase;
      }
      .atlas-goal-entry-copy strong {
        display: block;
        margin-top: .3rem;
        color: #162238;
        font-size: 1rem;
        font-weight: 720;
        line-height: 1.35;
      }
      .atlas-goal-entry-copy p {
        margin: .3rem 0 0;
        color: #667892;
        font-size: .76rem;
        line-height: 1.5;
      }
      .atlas-goal-entry-badge {
        justify-self: end;
        padding: .42rem .68rem;
        border: 1px solid #c9ddf8;
        border-radius: 999px;
        color: #285f9f;
        background: rgba(255,255,255,.78);
        font-size: .7rem;
        font-weight: 680;
        white-space: nowrap;
      }
      .st-key-atlas_goal_editor [data-testid="stExpander"] {
        border-color: #9fc2f1 !important;
        border-radius: 14px !important;
        background: #ffffff;
        box-shadow: 0 7px 20px rgba(28,83,153,.07);
      }
      .st-key-atlas_goal_editor [data-testid="stExpander"] summary {
        min-height: 54px;
        color: #155bbf;
        font-weight: 720;
      }
      .st-key-atlas_goal_editor [data-testid="stExpander"] summary:hover { background: #f2f7ff; }
      .atlas-anchor { height: 0; scroll-margin-top: 1.25rem; }
      .atlas-unlock {
        margin-top: 1.5rem;
        padding: 1.4rem;
        border: 1px solid var(--journey-line);
        border-radius: 16px;
        background: rgba(255,255,255,.72);
      }
      .atlas-unlock h2 { margin: 0; font-size: 1.05rem; letter-spacing: -.02em; }
      .atlas-unlock > p { margin: .4rem 0 1rem; color: var(--journey-muted); font-size: .83rem; }
      .atlas-unlock-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem; }
      .atlas-unlock-card {
        min-height: 132px;
        padding: 1rem;
        border: 1px solid var(--journey-line);
        border-radius: 12px;
        background: #ffffff;
        scroll-margin-top: 1.25rem;
      }
      .atlas-unlock-card svg { width: 21px; height: 21px; color: var(--journey-green); }
      .atlas-unlock-card strong { display: block; margin-top: .7rem; font-size: .8rem; }
      .atlas-unlock-card span { display: block; margin-top: .35rem; color: var(--journey-muted); font-size: .72rem; line-height: 1.45; }

      /* NexMind blue system — one palette across navigation, actions, learning, and evidence UI. */
      .stApp {
        background:
          radial-gradient(circle at 88% 0%, rgba(76, 148, 244, .11), transparent 28rem),
          var(--journey-bg);
      }
      [data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        border-color: #aac6ea;
        color: var(--journey-green-deep);
        background: #f2f7ff;
      }
      .atlas-side-label { color: #71839b; }
      .atlas-provider { border-color: #d8e4f2; background: #ffffff; }
      .atlas-provider-model { color: #6c7f99; }
      .atlas-live-dot { box-shadow: 0 0 0 4px rgba(23,105,224,.1); }
      .atlas-side-nav a { color: #253247 !important; }
      .atlas-side-nav a:hover { color: var(--journey-green-deep) !important; background: #edf4ff; }
      .atlas-side-nav a[aria-current="page"],
      .atlas-side-nav a[aria-current="location"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #1769e0, #0b4fb3);
        box-shadow: 0 7px 18px rgba(23,105,224,.2);
      }
      .atlas-side-nav a[aria-current="page"] span,
      .atlas-side-nav a[aria-current="page"] svg,
      .atlas-side-nav a[aria-current="location"] span,
      .atlas-side-nav a[aria-current="location"] svg { color: #ffffff !important; }
      .atlas-side-profile small,
      .atlas-side-reading-row,
      .journey-authors,
      .journey-model-summary span,
      .journey-model-value,
      .journey-source-meta { color: #687990; }
      .atlas-side-reading-row strong { color: #26354a; }

      .atlas-activity-summary { background: linear-gradient(135deg, #f1f7ff 0%, #ffffff 72%); }
      .atlas-activity-intro-icon,
      .atlas-version-dot,
      .journey-panel-title .journey-title-icon,
      .journey-overview-icon,
      .journey-why-icon,
      .journey-source-initial,
      .atlas-loop-step-icon { background: var(--journey-green-soft); }
      .atlas-activity-intro span,
      .atlas-activity-event span,
      .atlas-version-title small,
      .atlas-version-meta,
      .atlas-version-stage small,
      .atlas-section-copy,
      .atlas-form-kicker,
      .atlas-card-foot,
      .atlas-buy-edition,
      .atlas-buy-note,
      [data-testid="stMetricLabel"] p,
      .atlas-mentor-hero p,
      .atlas-accountability-detail,
      .atlas-loop-head p,
      .atlas-loop-step > span,
      .atlas-module-title span,
      .atlas-module-fact small { color: #65778f; }
      .atlas-activity-stat,
      .atlas-version-card,
      .atlas-score,
      [data-testid="stMetric"],
      .atlas-module-scope { border-color: #dce6f2; background: #fbfdff; }
      .atlas-version-card.current { border-color: #9ebfea; background: #f3f7ff; }
      .atlas-activity-stat strong,
      .atlas-activity-event strong,
      .atlas-version-title strong,
      .atlas-version-stage strong,
      .atlas-accountability-head strong,
      .atlas-accountability-next,
      .atlas-loop-step strong,
      .atlas-module-title strong,
      .atlas-module-fact span { color: #24364f; }
      .atlas-version-stage { border-color: #e4ebf5; }

      [data-testid="stTextInput"] input,
      [data-testid="stTextArea"] textarea,
      [data-testid="stNumberInput"] input,
      [data-baseweb="select"] > div { border-color: #d7e2f0 !important; background: #fbfdff !important; }
      [data-testid="stTextInput"] input:focus,
      [data-testid="stTextArea"] textarea:focus,
      [data-testid="stNumberInput"] input:focus,
      [data-baseweb="select"]:focus-within > div { box-shadow: 0 0 0 3px rgba(37,99,235,.12) !important; }
      [data-testid="stSidebar"] [data-testid="stTextInput"] input {
        border-color: #d7e2f0 !important;
        color: var(--journey-text) !important;
        -webkit-text-fill-color: var(--journey-text) !important;
        background: #ffffff !important;
      }
      [data-baseweb="tag"] { color: #174d9b !important; background: #e6f0ff !important; }
      [data-testid="stFormSubmitButton"] button[kind="primary"],
      [data-testid="stButton"] button[kind="primary"],
      button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #1769e0, #0b57c7);
        box-shadow: 0 8px 18px rgba(23,105,224,.18);
      }
      [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
      [data-testid="stButton"] button[kind="primary"]:hover,
      button[data-testid="stBaseButton-primary"]:hover { background: #0b4fb3; }
      .atlas-status { border-color: #d5e5f7; background: #eef5ff; }
      .atlas-status-name { color: #164f9e; }
      .atlas-status-meta { color: #60738c; }
      .atlas-trace-row { color: #40516a; background: #f5f8fc; }
      [data-testid="stExpander"] { box-shadow: 0 8px 24px rgba(30,64,120,.045); }
      .atlas-concept-card { box-shadow: 0 9px 28px rgba(30,64,120,.05); }
      .atlas-score { background: #f8fbff; }
      .atlas-score-top { color: #53667f; }
      .atlas-score-track,
      .journey-track { background: #e3e9f1; }
      .atlas-buy { border-color: #d9e5f3; background: #f5f9ff; }
      .atlas-buy-link { border-color: #d6e2f1; color: #194f96 !important; }
      .atlas-buy-link:hover { border-color: #8fb5e8; background: #f7faff; box-shadow: 0 6px 16px rgba(30,64,120,.07); }

      .atlas-mentor-hero {
        border-color: #d3e2f5;
        background: radial-gradient(circle at 92% 12%, rgba(190,218,255,.72), transparent 31%), linear-gradient(135deg, #fbfdff 0%, #edf5ff 100%);
        box-shadow: 0 12px 30px rgba(32,76,139,.075);
      }
      .atlas-mentor-kicker,
      .atlas-mentor-action { color: var(--atlas-accent); }
      .atlas-mentor-hero h3,
      .atlas-mentor-empty strong,
      .atlas-mentor-context strong,
      .atlas-loop-head h3 { color: #17243a; }
      .atlas-mentor-context { border-color: rgba(23,105,224,.14); }
      .atlas-mentor-thread { background: #fbfdff; }
      .atlas-mentor-empty { color: #65778f; }
      .atlas-mentor-avatar { background: var(--atlas-accent); }
      .atlas-mentor-message.user .atlas-mentor-avatar { color: #194f96; background: #e5effc; }
      .atlas-mentor-bubble { border-color: #d9e4f1; color: #29384e; font-size: 1rem; line-height: 1.75; box-shadow: 0 4px 12px rgba(34,73,128,.045); }
      .atlas-mentor-message.user .atlas-mentor-bubble { border-color: #cbdcf2; background: #edf5ff; }
      .atlas-mentor-action { border-color: #e2eaf5; }
      .atlas-accountability-card { border-color: #d9e4f1; }
      .atlas-loop-proof span { border-color: #d4e2f3; color: #315477; }
      .atlas-loop-flow,
      .atlas-loop-step { border-color: #dce6f2; }
      .atlas-module-title { background: #eef5ff; }
      .atlas-module-number { background: var(--atlas-accent); }
      .atlas-module-fact { border-color: #e1e9f4; }
      .st-key-atlas_mentor_workspace [data-testid="stForm"],
      [class*="st-key-book_mentor_"] [data-testid="stForm"] { border-color: #d8e4f2; }

      .atlas-topbar { background: rgba(251,253,255,.92); }
      .st-key-atlas_global_search [data-baseweb="input"],
      .st-key-atlas_global_search [data-testid="stTextInputRootElement"],
      .atlas-search-shell { border-color: #d2deed !important; }
      .st-key-atlas_global_search [data-baseweb="input"]:focus-within,
      .st-key-atlas_global_search [data-testid="stTextInputRootElement"]:focus-within,
      .atlas-search-shell:focus-within { box-shadow: 0 0 0 3px rgba(23,105,224,.12) !important; }
      .st-key-atlas_global_search input,
      .atlas-search-shell input { color: var(--journey-text) !important; -webkit-text-fill-color: var(--journey-text) !important; caret-color: var(--atlas-accent); }
      .atlas-search-results { border-color: #d6e1ef; box-shadow: 0 18px 42px rgba(28,58,103,.15); }
      .atlas-search-option:hover,
      .atlas-search-option.active,
      .atlas-search-option:focus-visible { background: #edf4ff; }
      .atlas-search-result-type,
      .atlas-search-empty { color: #62758d; }
      .atlas-search-agent-option { background: #f2f7ff; }
      .atlas-search-agent-option .atlas-search-result-type { background: #dfecff; }

      .atlas-cover-card {
        border-color: rgba(24,91,188,.2);
        background: linear-gradient(150deg, #1c6ed0 0%, #1556ad 48%, #0b2f6b 100%);
        box-shadow: 0 10px 24px rgba(24,70,133,.17);
      }
      .atlas-cover-placeholder {
        background: radial-gradient(circle at 76% 25%, rgba(167,207,255,.28), transparent 31%), linear-gradient(150deg, #1c6ed0 0%, #1556ad 52%, #0b2f6b 100%);
      }
      .atlas-cover-image,
      .journey-cover-image { background: #edf3fa; }
      .atlas-book-fit-score { background: conic-gradient(var(--journey-green) calc(var(--fit-score) * 1%), #e2e8f0 0); }
      .atlas-book-fit-verdict { background: #e6f0ff; }
      .atlas-book-fit-copy { color: #3f5067; }
      .atlas-book-fit-role { color: #62748b; }
      .atlas-book-fit-source { border-color: #d6e2f1; color: #23538f !important; }
      .atlas-book-fit-step { color: #62748b; }
      .atlas-book-fit-foot { color: #66788f; }
      .atlas-top-actions svg { color: #263449; }
      .atlas-avatar { background: linear-gradient(145deg, #1769e0, #0b4fb3); }

      .journey-stage:hover { border-color: #c9daee; background: #f4f8ff; box-shadow: 0 6px 16px rgba(30,64,120,.06); }
      .journey-stage:focus-visible { outline-color: rgba(37,99,235,.32); }
      .journey-stage.selected { border-color: #8db3e6; background: #f2f7ff; }
      .journey-stage-number { color: #64748b; background: #edf1f6; }
      .journey-stage.complete:not(.active) .journey-stage-number { color: var(--journey-green-deep); background: #e4efff; }
      .journey-stage-icon { color: #334155; background: #eef2f7; }
      .journey-stage.selected:not(.active) .journey-stage-icon { color: var(--journey-green-deep); background: #e8f2ff; }
      .journey-stage-title { color: #182235; }
      .journey-stage-status { color: #687990; }
      .journey-stage.active .journey-track span { background: linear-gradient(90deg, #1769e0, #69adff); }
      .journey-stage.complete .journey-track span { background: #78aef0; }
      .journey-stage-context { color: #315477; background: #edf4ff; }
      .journey-stage-context a { color: var(--journey-green-deep) !important; }
      .journey-cover {
        color: #f7fbff;
        background: linear-gradient(155deg, #0d4da8 0%, #2379dc 44%, #88bdf6 100%);
        box-shadow: 0 7px 18px rgba(24,70,133,.18);
      }
      .journey-narrative-copy,
      .journey-narrative-preview,
      .journey-narrative-full { color: #3f4b5f; }
      .journey-source-pill:hover { border-color: #a8c2e2; background: #f5f9ff; }
      .journey-mentor-link { border-color: #b7cce8; }
      .journey-mentor-link:hover { border-color: #82aae0; background: #f2f7ff; }
      .journey-ring { background: conic-gradient(var(--journey-green) var(--value), #e2e8f0 0); }
      .journey-model-row > svg { color: #4d5e75; }
      .journey-source-card { color: #1f2a3c !important; }
      .journey-source-card:hover { border-color: #a9c2e1; background: #f7faff; }

      @media (min-width: 901px) {
        [data-testid="stSidebarHeader"] { display: none !important; }
      }
      @media (min-width: 1181px) and (min-height: 820px) {
        .journey-current, .journey-learner { min-height: 438px; }
        .journey-current-body { min-height: 370px; }
      }

      @media (max-width: 1180px) {
        .journey-primary-grid { grid-template-columns: 1fr; }
        .journey-learner { display: grid; grid-template-columns: 1fr 1.4fr; gap: 1rem; }
        .journey-model-summary { border-bottom: 0; border-right: 1px solid var(--journey-line); }
        .journey-sources { height: auto; }
        .journey-source-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
      @media (max-width: 900px) {
        [data-testid="stSidebar"] { position: fixed !important; inset: 0 auto 0 0; z-index: 1000; }
        [data-testid="stMain"] { left: 0 !important; width: 100% !important; }
        [data-testid="stMainBlockContainer"] { padding: 0 1rem 4rem; }
        .atlas-topbar { margin: -2rem -1rem .9rem; padding-inline: 1rem; }
        .st-key-atlas_global_search { left: 0; width: min(395px, 58vw); }
        .atlas-search-wrap { margin-left: 0; }
        .atlas-top-actions { transform: none; }
        .journey-stages { grid-template-columns: 1fr; padding: 1rem; }
        .journey-stage { grid-template-columns: 34px 44px 1fr; }
        .journey-stage-icon { width: 44px; height: 44px; }
        .atlas-activity-summary { grid-template-columns: 1fr 1fr; }
        .atlas-activity-intro { grid-column: 1 / -1; }
        .atlas-activity-events { grid-template-columns: 1fr; }
        .atlas-activity-event { border-right: 0; border-bottom: 1px solid var(--atlas-line); }
        .atlas-activity-event:last-child { border-bottom: 0; }
        .atlas-side-nav { margin-inline: 0; }
        .atlas-side-nav a { min-height: 44px; gap: .75rem; }
        .atlas-side-profile { min-height: 0; margin: .75rem .2rem 1rem; }
        .atlas-unlock-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .atlas-mobile-nav {
          position: relative;
          z-index: 1190;
          display: block;
          margin: .2rem 0 .95rem;
        }
        .atlas-mobile-nav summary {
          min-height: 44px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: .75rem;
          padding: .65rem .85rem;
          border: 1px solid var(--journey-line);
          border-radius: 10px;
          color: var(--journey-text);
          background: #ffffff;
          box-shadow: 0 4px 14px rgba(24,45,37,.06);
          font-size: .82rem;
          font-weight: 650;
          cursor: pointer;
          list-style: none;
        }
        .atlas-mobile-nav summary::-webkit-details-marker { display: none; }
        .atlas-mobile-nav summary svg { width: 19px; height: 19px; }
        .atlas-mobile-nav-summary { display: inline-flex; align-items: center; gap: .6rem; }
        .atlas-mobile-nav-chevron { transition: transform var(--atlas-motion-fast) ease; }
        .atlas-mobile-nav[open] .atlas-mobile-nav-chevron { transform: rotate(90deg); }
        .atlas-mobile-nav-panel {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: .38rem;
          margin-top: .45rem;
          padding: .55rem;
          border: 1px solid var(--journey-line);
          border-radius: 12px;
          background: #ffffff;
          box-shadow: 0 18px 42px rgba(20,35,29,.13);
        }
        .atlas-mobile-nav-panel a {
          min-height: 44px;
          display: flex;
          align-items: center;
          gap: .55rem;
          padding: .55rem .65rem;
          border-radius: 8px;
          color: var(--journey-text) !important;
          font-size: .8rem;
          font-weight: 580;
          text-decoration: none !important;
        }
        .atlas-mobile-nav-panel a:hover,
        .atlas-mobile-nav-panel a:focus-visible { background: #edf5f0; }
        .atlas-mobile-nav-panel a:focus-visible {
          outline: 2px solid var(--atlas-focus);
          outline-offset: -2px;
        }
        .atlas-mobile-nav-panel a svg { width: 17px; height: 17px; flex: 0 0 auto; }
        .atlas-mobile-languages {
          grid-column: 1 / -1;
          display: flex;
          gap: .45rem;
          padding-top: .5rem;
          border-top: 1px solid var(--journey-line);
        }
        .atlas-mobile-languages a {
          min-height: 44px;
          flex: 1;
          justify-content: center;
          border: 1px solid var(--journey-line);
        }
        .atlas-mobile-languages a[aria-current="true"] {
          color: #ffffff !important;
          border-color: var(--journey-green);
          background: var(--journey-green);
        }
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
      }
      @media (max-width: 620px) {
        .atlas-goal-entry {
          grid-template-columns: 42px minmax(0, 1fr);
          gap: .75rem;
          padding: .9rem;
        }
        .atlas-goal-entry-icon { width: 42px; height: 42px; border-radius: 12px; }
        .atlas-goal-entry-copy p { font-size: .73rem; }
        .atlas-goal-entry-badge { grid-column: 2; justify-self: start; }
        .atlas-mentor-hero { grid-template-columns: 1fr; padding: 1rem; }
        .atlas-mentor-context { min-width: 0; }
        .atlas-mentor-message { max-width: 96%; }
        .atlas-activity-summary { grid-template-columns: 1fr; }
        .atlas-activity-intro { grid-column: auto; }
        .atlas-version-card summary { grid-template-columns: auto minmax(0, 1fr) auto; }
        .atlas-version-meta { grid-column: 2 / 3; white-space: normal; }
        .atlas-version-stages { padding-left: .85rem; }
        .journey-stage-context { align-items: flex-start; flex-direction: column; }
        .atlas-unlock-grid { grid-template-columns: 1fr; }
        .atlas-topbar { min-height: 66px; }
        .st-key-atlas_global_search { top: .7rem; width: calc(100% - 1rem); }
        .atlas-search-wrap { width: 100%; }
        .atlas-top-actions { display: none; }
        .atlas-book-fit-head { grid-template-columns: 1fr; padding: 1.15rem; }
        .atlas-book-fit-identity { grid-template-columns: 78px minmax(0, 1fr); gap: .9rem; }
        .atlas-cover-card--fit { width: 78px; }
        .atlas-cover-card--detail { width: min(44vw, 156px); }
        .atlas-book-fit-score { width: 88px; height: 88px; }
        .atlas-book-fit-score::before { width: 68px; height: 68px; }
        .atlas-book-fit-body { grid-template-columns: 1fr; padding: 1.1rem 1.15rem 1.25rem; }
        .atlas-book-fit-scores { grid-template-columns: 1fr; }
        .atlas-book-fit-foot { align-items: flex-start; flex-direction: column; padding-inline: 1.15rem; }
        .journey-page-head { align-items: flex-start; flex-direction: column; }
        .journey-page-title { font-size: 1.55rem; }
        .journey-current-body { grid-template-columns: 1fr; gap: 1rem; padding: 1rem; }
        .journey-cover { width: min(100%, 275px); min-height: 350px; margin-inline: auto; }
        .journey-book-title { font-size: 2rem; }
        .journey-current-foot { grid-template-columns: auto 1fr auto; }
        .journey-current-foot .journey-mentor-link,
        .journey-current-foot .journey-continue { grid-column: 1 / -1; justify-content: center; }
        .journey-learner { display: block; }
        .journey-model-summary { border-right: 0; border-bottom: 1px solid var(--journey-line); }
        .journey-source-grid { grid-template-columns: 1fr; }
      }
    </style>
    """


_ICON_MARKUP = {
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
    "library": '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/><path d="M2 20h20"/>',
    "network": '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v5M7 18l4-5M17 18l-4-5"/>',
    "bulb": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M8.6 15.2A7 7 0 1 1 15.4 15c-.9.7-1.4 1.7-1.4 2.8h-4c0-1-.5-2-1.4-2.6Z"/>',
    "box": '<path d="m21 8-9 5-9-5 9-5 9 5Z"/><path d="m3 8 9 5 9-5v8l-9 5-9-5V8Z"/>',
    "note": '<path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    "pencil": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 3v3M21 12h-3M12 21v-3M3 12h3"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    "bot": '<rect x="4" y="7" width="16" height="12" rx="4"/><path d="M12 3v4M8 12h.01M16 12h.01M9 16h6M2 12h2M20 12h2"/>',
    "scale": '<path d="m16 16 3-8 3 8a5 5 0 0 1-6 0ZM2 16l3-8 3 8a5 5 0 0 1-6 0ZM7 21h10M12 3v18M3 7h18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "chevron": '<path d="m9 18 6-6-6-6"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "play": '<path d="m7 4 13 8-13 8Z"/>',
}


def _icon_svg(name: str, class_name: str = "") -> str:
    class_attr = f' class="{escape(class_name, quote=True)}"' if class_name else ""
    return (
        f'<svg{class_attr} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        f'{_ICON_MARKUP[name]}</svg>'
    )


def _companion_svg(class_name: str = "") -> str:
    """Return the friendly Atlas companion mark used only for coaching states."""
    class_attr = f' class="{escape(class_name, quote=True)}"' if class_name else ""
    return (
        f'<svg{class_attr} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" '
        'aria-hidden="true" focusable="false">'
        '<path d="M32 8v7" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>'
        '<circle cx="32" cy="7" r="3" fill="currentColor"/>'
        '<rect x="13" y="15" width="38" height="31" rx="11" fill="currentColor" opacity=".18"/>'
        '<rect x="13" y="15" width="38" height="31" rx="11" stroke="currentColor" stroke-width="3"/>'
        '<circle cx="25" cy="29" r="3.5" fill="currentColor"/>'
        '<circle cx="39" cy="29" r="3.5" fill="currentColor"/>'
        '<path d="M25 38c2.2 1.5 4.5 2.2 7 2.2s4.8-.7 7-2.2" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M8 28h5M51 28h5M22 47v6M42 47v6" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M19 55h26" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>'
        '</svg>'
    )


def brand_html() -> str:
    return """
    <div class="atlas-brand" role="img" aria-label="NexMind — Agentic Intelligence">
      <span class="atlas-brand-mark" aria-hidden="true"><img src="app/static/nexmind-logo.png" alt=""></span>
      <span class="atlas-brand-wordmark" aria-hidden="true"><img src="app/static/nexmind-logo.png" alt=""></span>
    </div>
    """


def new_profile_entry_html(is_zh: bool, user_id: str) -> str:
    label = "新建学习档案" if is_zh else "New learning profile"
    hint = "从空白学习需求开始，保留现有档案" if is_zh else "Start with blank goals; keep your existing profile"
    plus = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke-linecap="round"/></svg>'
    return (
        f'<a class="atlas-new-profile" href="{escape(new_learning_profile_url(is_zh, user_id), quote=True)}" '
        f'target="_self" title="{hint}">{plus}<span>{label}</span></a>'
    )


def profile_return_html(is_zh: bool, user_id: str, *, return_language: str = "") -> str:
    label = "返回原学习档案" if is_zh else "Back to previous profile"
    original_is_zh = return_language == "zh" if return_language in {"zh", "en"} else is_zh
    return (
        f'<a class="atlas-profile-return" href="{escape(learning_profile_url(original_is_zh, user_id), quote=True)}" '
        f'target="_self">{_icon_svg("history")}<span>{label} · {escape(user_id)}</span></a>'
    )


def sidebar_navigation_html(is_zh: bool, user_id: str, *, preview: bool = False) -> str:
    workspace_url = '?' + urlencode({'ui_language': 'zh' if is_zh else 'en', 'user_id': user_id})
    items = (
        ("book", "Reading Journey", "阅读旅程", "#reading-journey", True),
        ("library", "Recommendations", "推荐书目", "#reading-route", False),
        ("network", "Knowledge Map", "知识地图", "#knowledge-map", False),
        ("bulb", "Learning Tools", "学习工具", "#learning-loop", False),
        ("shield", "Sources", "书目来源", "#journey-sources", False),
        ("target", "Goals", "学习目标", "#learning-brief", False),
        ("history", "Plan history", "历史方案", workspace_url + "&history=1", False),
    )
    links = []
    for index, (icon, english, chinese, href, active) in enumerate(items):
        if index == 5:
            links.append('<div class="atlas-side-divider" aria-hidden="true"></div>')
        current = ' aria-current="page"' if (icon == 'history' if preview else active) else ""
        label = chinese if is_zh else english
        if preview and href.startswith('#'):
            href = workspace_url + href
        links.append(
            f'<a href="{escape(href, quote=True)}" target="_self"{current}>{_icon_svg(icon)}<span>{escape(label)}</span></a>'
        )
    initials = "".join(part[:1] for part in user_id.replace("-", " ").split())[:2].upper() or "NA"
    profile_label = "当前用户" if is_zh else "Current profile"
    primary_label = "主导航" if is_zh else "Primary navigation"
    return (
        new_profile_entry_html(is_zh, user_id)
        + f'<nav class="atlas-side-nav" aria-label="{primary_label}">'
        + "".join(links)
        + "</nav>"
        + '<div class="atlas-side-profile">'
        + '<div class="atlas-side-profile-main">'
        + f'<span class="atlas-avatar">{escape(initials)}</span>'
        + f'<span><strong>{escape(user_id)}</strong><small>{profile_label}</small></span></div>'
        + "</div>"
    )


def mobile_navigation_html(is_zh: bool, user_id: str, *, preview: bool = False, return_profile_id: str = "", return_language: str = "") -> str:
    """Return a compact navigation and language switcher for narrow screens."""
    items = (
        ("book", "Reading Journey", "阅读旅程", "#reading-journey"),
        ("library", "Recommendations", "推荐书目", "#reading-route"),
        ("network", "Knowledge Map", "知识地图", "#knowledge-map"),
        ("bulb", "Learning Tools", "学习工具", "#learning-loop"),
        ("shield", "Sources", "书目来源", "#journey-sources"),
        ("target", "Goals", "学习目标", "#learning-brief"),
        ("history", "Plan history", "历史方案", '?' + urlencode({'ui_language': 'zh' if is_zh else 'en', 'user_id': user_id, 'history': '1'})),
    )
    if preview:
        workspace_url = '?' + urlencode({'ui_language': 'zh' if is_zh else 'en', 'user_id': user_id})
        items = tuple((icon, en, zh, workspace_url + href if href.startswith('#') else href)
                      for icon, en, zh, href in items)
    links = "".join(
        f'<a href="{escape(href, quote=True)}" target="_self">{_icon_svg(icon)}<span>{escape(chinese if is_zh else english)}</span></a>'
        for icon, english, chinese, href in items
    )
    origin_language = return_language if return_language in {"zh", "en"} else ("zh" if is_zh else "en")
    draft_params = {"new_profile": "1", "return_profile": return_profile_id, "return_language": origin_language} if return_profile_id else {}
    language_anchor = "#learning-brief" if return_profile_id else "#reading-journey"
    english_url = "?" + urlencode(
        {"ui_language": "en", "set_language": "en", "user_id": user_id, **draft_params}
    ) + language_anchor
    chinese_url = "?" + urlencode(
        {"ui_language": "zh", "set_language": "zh", "user_id": user_id, **draft_params}
    ) + language_anchor
    menu_label = "导航与语言" if is_zh else "Navigation & language"
    nav_label = "移动端导航" if is_zh else "Mobile navigation"
    return (
        f'<details class="atlas-mobile-nav"><summary aria-label="{nav_label}">'
        f'<span class="atlas-mobile-nav-summary">{_icon_svg("book")}<span>{menu_label}</span></span>'
        f'{_icon_svg("chevron", "atlas-mobile-nav-chevron")}</summary>'
        f'<nav class="atlas-mobile-nav-panel" aria-label="{nav_label}">{links}'
        '<div class="atlas-mobile-profile-action">'
        f'{new_profile_entry_html(is_zh, user_id)}</div>'
        '<div class="atlas-mobile-languages" aria-label="Language">'
        f'<a href="{escape(english_url, quote=True)}" target="_self" aria-current="{str(not is_zh).lower()}">English</a>'
        f'<a href="{escape(chinese_url, quote=True)}" target="_self" aria-current="{str(is_zh).lower()}">中文</a>'
        '</div></nav></details>'
    )


def topbar_html(
    is_zh: bool,
    search_items: Sequence[tuple[str, str, str, str]] | None = None,
    initial_query: str = "",
    agent_search_enabled: bool = False,
    search_user_id: str = "",
    native_search: bool = False,
) -> str:
    placeholder = "输入书名或 ISBN，评估契合度" if is_zh else "Enter a book title or ISBN to assess fit"
    results_label = "搜索结果" if is_zh else "Search results"
    no_results = (
        "当前学习路径中没有匹配结果，请尝试输入书名、主题或知识类型。"
        if is_zh
        else "No matches in this reading path. Try a book title, topic, or knowledge area."
    )
    empty_message = (
        "请先生成学习路径，Atlas 才能依据你的目标评估书籍。"
        if is_zh
        else "Create a reading path first so Atlas can assess books against your goal."
    )
    agent_label = "联网搜索并评估" if is_zh else "Search online and assess"
    agent_category = "Atlas"
    payload = json.dumps(
        [
            {"label": label, "category": category, "href": href, "keywords": keywords}
            for label, category, href, keywords in (search_items or ())
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    search_html = '<div class="atlas-native-search-slot" aria-hidden="true"></div>' if native_search else (
        f'<div class="atlas-search-wrap" id="agent-search" data-language="{"zh" if is_zh else "en"}" '
        f'data-search-items="{escape(payload, quote=True)}" '
        f'data-no-results="{escape(no_results, quote=True)}" '
        f'data-empty-message="{escape(empty_message, quote=True)}" '
        f'data-agent-enabled="{str(agent_search_enabled).lower()}" '
        f'data-agent-label="{escape(agent_label, quote=True)}" '
        f'data-agent-category="{escape(agent_category, quote=True)}" '
        f'data-search-user-id="{escape(search_user_id, quote=True)}">'
        '<label class="atlas-search-shell">'
        f'{_icon_svg("search")}<input type="text" inputmode="search" enterkeyhint="search" '
        f'aria-label="{escape(placeholder, quote=True)}" '
        f'placeholder="{escape(placeholder, quote=True)}" value="{escape(initial_query, quote=True)}" '
        'autocomplete="off" spellcheck="false" '
        'role="combobox" aria-autocomplete="list" aria-expanded="false" '
        'aria-controls="atlas-search-results" data-atlas-search-input>'
        "</label>"
        f'<div id="atlas-search-results" class="atlas-search-results" role="listbox" '
        f'aria-label="{escape(results_label, quote=True)}" hidden></div>'
        '<span class="atlas-sr-only" aria-live="polite" data-atlas-search-status></span>'
        "</div>"
    )
    return (
        '<header class="atlas-topbar">'
        + search_html
        + '<div class="atlas-top-actions">'
        + f'<span class="atlas-avatar" aria-label="{escape(("当前用户：" if is_zh else "Current profile: ") + (search_user_id or "NexMind Atlas"), quote=True)}">'
        + escape("".join(part[:1] for part in search_user_id.replace("-", " ").split())[:2].upper() or "NA")
        + "</span>"
        + "</div></header>"
    )


def workspace_intro_html(is_zh: bool) -> str:
    # The hero already introduces Atlas and owns the page's H1. Keep only the
    # navigation targets here so first-time users do not encounter two nearly
    # identical introductions before the actual form.
    return (
        '<div id="atlas-main" tabindex="-1">'
        '<div class="atlas-anchor" id="reading-journey" aria-hidden="true"></div>'
        '</div>'
    )


def learning_goal_editor_html(is_zh: bool, *, topic: str) -> str:
    eyebrow = "当前学习目标" if is_zh else "CURRENT LEARNING GOAL"
    title = f"正在学习：{topic}" if is_zh else f"Learning now: {topic}"
    copy = (
        "学习方向或时间安排有变化？你可以更新学习主题、已有基础、每周时间和书目偏好。Atlas 会保存为新版本，已记录的阅读进度不会丢失。"
        if is_zh
        else "Changed direction or availability? Update the topic, starting point, weekly time, or book preferences. Atlas saves a new version without losing recorded progress."
    )
    badge = "保留已有进度" if is_zh else "Progress stays saved"
    return (
        '<section class="atlas-goal-entry" aria-label="'
        + escape(eyebrow, quote=True)
        + '">'
        + f'<span class="atlas-goal-entry-icon">{_icon_svg("target")}</span>'
        + '<div class="atlas-goal-entry-copy">'
        + f'<span>{escape(eyebrow)}</span><strong>{escape(title)}</strong><p>{escape(copy)}</p>'
        + "</div>"
        + f'<span class="atlas-goal-entry-badge">{escape(badge)}</span>'
        + "</section>"
    )


def section_anchor(anchor_id: str) -> str:
    return f'<div class="atlas-anchor" id="{escape(anchor_id, quote=True)}" aria-hidden="true"></div>'


def navigation_empty_state_html(is_zh: bool) -> str:
    title = "完成首次规划后，即可使用以下功能" if is_zh else "Your workspaces will appear after you create a reading path"
    detail = (
        "填写学习需求并生成路径后，可从侧边栏查看知识地图、推荐书目和书目来源，开始答疑与练习。"
        if is_zh
        else "Complete the learning goals above. The sidebar will then take you directly to each workspace."
    )
    locked = "生成学习路径后可用" if is_zh else "Available after you create your first reading path"
    cards = (
        ("knowledge-map", "network", "知识地图" if is_zh else "Knowledge Map"),
        ("reading-route", "library", "推荐书目" if is_zh else "Recommendations"),
        ("journey-sources", "shield", "书目来源" if is_zh else "Sources & Verification"),
        ("learning-loop", "bulb", "学习工具" if is_zh else "Learning Tools"),
    )
    card_html = "".join(
        f'<article class="atlas-unlock-card" id="{anchor_id}">{_icon_svg(icon)}'
        f'<strong>{escape(label)}</strong><span>{escape(locked)}</span></article>'
        for anchor_id, icon, label in cards
    )
    return (
        '<section class="atlas-unlock" id="agent-progress" aria-labelledby="atlas-unlock-title">'
        f'<h2 id="atlas-unlock-title">{escape(title)}</h2><p>{escape(detail)}</p>'
        f'<div class="atlas-unlock-grid">{card_html}</div></section>'
    )


def hash_navigation_html() -> str:
    """Install hash navigation for Streamlit's nested main scroll container."""
    return """
    <script>
      (() => {
        const host = window.parent;
        const doc = host.document;
        const interfaceLanguage = new URL(host.location.href).searchParams.get('ui_language');
        doc.documentElement.lang = interfaceLanguage === 'zh' ? 'zh-CN' : 'en';
        const reducedMotion = host.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const navSelector = '.atlas-side-nav a, .atlas-mobile-nav-panel > a';

        const setActive = (activeLink) => {
          doc.querySelectorAll(navSelector).forEach((link) => {
            if (link === activeLink) link.setAttribute('aria-current', 'location');
            else link.removeAttribute('aria-current');
          });
        };

        const scrollToTarget = (hash, preferredLink = null) => {
          const id = decodeURIComponent((hash || '').replace(/^#/, ''));
          const target = id ? doc.getElementById(id) : null;
          if (!target) return;
          host.requestAnimationFrame(() => {
            const isScrollable = (element) => {
              if (!element) return false;
              const overflowY = host.getComputedStyle(element).overflowY;
              return /(auto|scroll|overlay)/.test(overflowY)
                && element.scrollHeight > element.clientHeight + 2;
            };
            let scrollContainer = target.parentElement;
            while (scrollContainer && scrollContainer !== doc.documentElement
              && !isScrollable(scrollContainer)) {
              scrollContainer = scrollContainer.parentElement;
            }
            if (!isScrollable(scrollContainer)) {
              scrollContainer = [
                doc.querySelector('[data-testid="stMain"]'),
                doc.querySelector('[data-testid="stAppViewContainer"]'),
                doc.scrollingElement
              ].find(isScrollable) || null;
            }
            const targetLinks = Array.from(doc.querySelectorAll(navSelector))
              .filter((link) => link.getAttribute('href') === `#${id}`);
            const activeLink = preferredLink
              || targetLinks.find((link) => link.hasAttribute('aria-current'))
              || targetLinks[0];
            if (activeLink) {
              activeLink.dataset.atlasScrollContainer = scrollContainer?.getAttribute('data-testid')
                || scrollContainer?.tagName?.toLowerCase()
                || 'native';
              activeLink.dataset.atlasTargetTop = String(Math.round(target.getBoundingClientRect().top));
            }
            if (!scrollContainer) {
              target.scrollIntoView({
                behavior: reducedMotion ? 'auto' : 'smooth',
                block: 'start',
                inline: 'nearest'
              });
              return;
            }
            const targetRect = target.getBoundingClientRect();
            const containerRect = scrollContainer.getBoundingClientRect();
            const top = scrollContainer.scrollTop + targetRect.top - containerRect.top - 16;
            scrollContainer.scrollTo({ top, behavior: reducedMotion ? 'auto' : 'smooth' });
            host.setTimeout(() => {
              if (activeLink) activeLink.dataset.atlasScrollTop = String(Math.round(scrollContainer.scrollTop));
            }, 500);
          });
        };

        let searchWrap = doc.querySelector('.atlas-search-wrap');
        let searchInput = searchWrap?.querySelector('[data-atlas-search-input]');
        let searchResults = searchWrap?.querySelector('.atlas-search-results');
        let searchStatus = searchWrap?.querySelector('[data-atlas-search-status]');
        let searchItems = [];
        let searchItemsRaw = searchWrap?.dataset.searchItems || '[]';
        let activeResultIndex = -1;

        if (searchWrap) {
          try {
            searchItems = JSON.parse(searchItemsRaw);
          } catch (_error) {
            searchItems = [];
          }
          const languageUrl = new URL(host.location.href);
          if (languageUrl.searchParams.get('ui_language') !== searchWrap.dataset.language) {
            languageUrl.searchParams.set('ui_language', searchWrap.dataset.language);
            host.history.replaceState(null, '', languageUrl.toString());
          }
        }

        const refreshSearchReferences = () => {
          const nextWrap = doc.querySelector('.atlas-search-wrap');
          if (!nextWrap) return false;
          const nextInput = nextWrap.querySelector('[data-atlas-search-input]');
          const nextResults = nextWrap.querySelector('.atlas-search-results');
          const nextStatus = nextWrap.querySelector('[data-atlas-search-status]');
          const nextItemsRaw = nextWrap.dataset.searchItems || '[]';
          const changed = nextWrap !== searchWrap || nextInput !== searchInput;
          searchWrap = nextWrap;
          searchInput = nextInput;
          searchResults = nextResults;
          searchStatus = nextStatus;
          if (changed || nextItemsRaw !== searchItemsRaw) {
            searchItemsRaw = nextItemsRaw;
            try {
              searchItems = JSON.parse(searchItemsRaw);
            } catch (_error) {
              searchItems = [];
            }
          }
          return changed;
        };

        const normalizeSearchText = (value) => String(value || '')
          .normalize('NFKC')
          .toLocaleLowerCase(searchWrap?.dataset.language === 'zh' ? 'zh-CN' : 'en-US');

        const closeSearchResults = () => {
          if (!searchInput || !searchResults) return;
          searchResults.hidden = true;
          searchResults.replaceChildren();
          searchInput.setAttribute('aria-expanded', 'false');
          searchInput.removeAttribute('aria-activedescendant');
          activeResultIndex = -1;
        };

        const setActiveResult = (nextIndex) => {
          if (!searchInput || !searchResults) return;
          const options = Array.from(searchResults.querySelectorAll('.atlas-search-option'));
          if (!options.length) return;
          activeResultIndex = (nextIndex + options.length) % options.length;
          options.forEach((option, index) => {
            const isActive = index === activeResultIndex;
            option.classList.toggle('active', isActive);
            option.setAttribute('aria-selected', isActive ? 'true' : 'false');
          });
          searchInput.setAttribute('aria-activedescendant', options[activeResultIndex].id);
          options[activeResultIndex].scrollIntoView({ block: 'nearest' });
        };

        const openSearchTarget = (item) => {
          if (!item?.href) return;
          if (searchInput) {
            const draft = item.label || '';
            searchInput.value = draft;
          }
          closeSearchResults();
          const matchingLink = Array.from(doc.querySelectorAll(navSelector))
            .find((link) => link.getAttribute('href') === item.href);
          if (matchingLink) setActive(matchingLink);
          if (host.location.hash !== item.href) host.history.pushState(null, '', item.href);
          scrollToTarget(item.href, matchingLink || null);
          searchInput?.focus({ preventScroll: true });
        };

        const launchAgentSearch = (query) => {
          const trimmed = String(query || '').trim().slice(0, 160);
          if (!trimmed || searchWrap?.dataset.agentEnabled !== 'true') return;
          const url = new URL(host.location.href);
          url.searchParams.set('book_query', trimmed);
          url.searchParams.set('ui_language', searchWrap.dataset.language);
          if (searchWrap.dataset.searchUserId) {
            url.searchParams.set('user_id', searchWrap.dataset.searchUserId);
          }
          url.hash = 'book-fit-results';
          host.location.assign(url.toString());
        };

        const renderSearchResults = (queryOverride = null) => {
          refreshSearchReferences();
          if (!searchWrap || !searchInput || !searchResults) return;
          const rawQuery = String(queryOverride ?? searchInput.value).trim();
          const query = normalizeSearchText(rawQuery);
          searchResults.replaceChildren();
          activeResultIndex = -1;
          searchInput.removeAttribute('aria-activedescendant');
          if (!query) {
            closeSearchResults();
            if (searchStatus) searchStatus.textContent = '';
            return;
          }

          const matches = searchItems
            .map((item) => {
              const label = normalizeSearchText(item.label);
              const searchable = normalizeSearchText(
                `${item.label || ''} ${item.category || ''} ${item.keywords || ''}`
              );
              const score = label.startsWith(query) ? 0 : label.includes(query) ? 1 : 2;
              return { item, searchable, score };
            })
            .filter(({ searchable }) => searchable.includes(query))
            .sort((left, right) => left.score - right.score)
            .slice(0, 7);

          if (searchWrap.dataset.agentEnabled === 'true') {
            const option = doc.createElement('button');
            option.type = 'button';
            option.id = 'atlas-search-option-agent';
            option.className = 'atlas-search-option atlas-search-agent-option';
            option.setAttribute('role', 'option');
            option.setAttribute('aria-selected', 'false');
            const label = doc.createElement('span');
            label.className = 'atlas-search-result-label';
            label.textContent = `${searchWrap.dataset.agentLabel} “${rawQuery}”`;
            const category = doc.createElement('span');
            category.className = 'atlas-search-result-type';
            category.textContent = searchWrap.dataset.agentCategory;
            option.append(label, category);
            option.addEventListener('pointermove', () => setActiveResult(0));
            option.addEventListener('click', () => launchAgentSearch(rawQuery));
            searchResults.append(option);
          }

          if (searchWrap.dataset.agentEnabled !== 'true' && !searchItems.length) {
            const empty = doc.createElement('div');
            empty.className = 'atlas-search-empty';
            empty.setAttribute('role', 'status');
            empty.textContent = searchWrap.dataset.emptyMessage;
            searchResults.append(empty);
          } else if (matches.length) {
            matches.forEach(({ item }, index) => {
              const option = doc.createElement('button');
              option.type = 'button';
              const optionIndex = searchResults.querySelectorAll('.atlas-search-option').length;
              option.id = `atlas-search-option-${optionIndex}`;
              option.className = 'atlas-search-option';
              option.setAttribute('role', 'option');
              option.setAttribute('aria-selected', 'false');
              const label = doc.createElement('span');
              label.className = 'atlas-search-result-label';
              label.textContent = item.label;
              const category = doc.createElement('span');
              category.className = 'atlas-search-result-type';
              category.textContent = item.category;
              option.append(label, category);
              option.addEventListener('pointermove', () => setActiveResult(optionIndex));
              option.addEventListener('click', () => openSearchTarget(item));
              searchResults.append(option);
            });
          }

          searchResults.hidden = false;
          searchInput.setAttribute('aria-expanded', 'true');
          if (searchStatus) {
            const count = matches.length + (searchWrap.dataset.agentEnabled === 'true' ? 1 : 0);
            searchStatus.textContent = searchWrap.dataset.language === 'zh'
              ? `${count} 个搜索结果`
              : `${count} search result${count === 1 ? '' : 's'}`;
          }
        };

        const bindSearchInput = () => {
          refreshSearchReferences();
          if (!searchInput || !searchResults || searchInput.dataset.atlasSearchBound === 'true') return;
          searchInput.dataset.atlasSearchBound = 'true';
          searchInput.addEventListener('keydown', (event) => {
            if (event.isComposing || event.keyCode === 229) return;
            refreshSearchReferences();
            let options = searchResults.querySelectorAll('.atlas-search-option');
            if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && !options.length) {
              renderSearchResults(event.currentTarget.value);
              options = searchResults.querySelectorAll('.atlas-search-option');
            }
            if (event.key === 'ArrowDown' && options.length) {
              event.preventDefault();
              setActiveResult(activeResultIndex + 1);
            } else if (event.key === 'ArrowUp' && options.length) {
              event.preventDefault();
              setActiveResult(activeResultIndex < 0 ? options.length - 1 : activeResultIndex - 1);
            } else if (event.key === 'Enter') {
              event.preventDefault();
              if (options.length && activeResultIndex >= 0) {
                options[activeResultIndex].click();
              } else {
                launchAgentSearch(event.currentTarget.value);
              }
            } else if (event.key === 'Escape') {
              closeSearchResults();
            }
          });
        };

        bindSearchInput();

        if (host.__nexmindAtlasSearchObserver) {
          host.__nexmindAtlasSearchObserver.disconnect();
        }
        host.__nexmindAtlasSearchObserver = new host.MutationObserver(() => {
          const changed = refreshSearchReferences();
          if (!changed) return;
          bindSearchInput();
        });
        host.__nexmindAtlasSearchObserver.observe(doc.body, { childList: true, subtree: true });

        if (host.__nexmindAtlasSearchOutsideHandler) {
          doc.removeEventListener('pointerdown', host.__nexmindAtlasSearchOutsideHandler);
        }
        host.__nexmindAtlasSearchOutsideHandler = (event) => {
          if (searchWrap && !searchWrap.contains(event.target)) closeSearchResults();
        };
        doc.addEventListener('pointerdown', host.__nexmindAtlasSearchOutsideHandler);

        const syncFromHash = () => {
          const hash = host.location.hash;
          if (!hash) {
            const firstLink = doc.querySelector('.atlas-side-nav a');
            if (firstLink) setActive(firstLink);
            return;
          }
          const matchingLinks = Array.from(doc.querySelectorAll(navSelector))
            .filter((link) => link.getAttribute('href') === hash);
          const matchingLink = matchingLinks.find((link) => link.hasAttribute('aria-current'))
            || matchingLinks[0];
          if (matchingLink) setActive(matchingLink);
          scrollToTarget(hash);
        };

        doc.querySelectorAll(navSelector).forEach((link) => {
          if (link.dataset.atlasNavigationBound === 'true') return;
          link.dataset.atlasNavigationBound = 'true';
          link.addEventListener('click', () => {
            setActive(link);
            link.closest('.atlas-mobile-nav')?.removeAttribute('open');
            host.setTimeout(() => scrollToTarget(link.getAttribute('href'), link), 0);
          });
        });

        doc.querySelectorAll('.atlas-mobile-languages a').forEach((link) => {
          if (link.dataset.atlasLanguageBound === 'true') return;
          link.dataset.atlasLanguageBound = 'true';
          link.addEventListener('click', (event) => {
            event.preventDefault();
            host.location.assign(link.href);
          });
        });

        if (host.__nexmindAtlasHashHandler) {
          host.removeEventListener('hashchange', host.__nexmindAtlasHashHandler);
        }
        host.__nexmindAtlasHashHandler = syncFromHash;
        host.addEventListener('hashchange', syncFromHash);
        host.setTimeout(syncFromHash, 60);
      })();
    </script>
    """


def interaction_result_html(target_id: str) -> str:
    """An explicit completion signal; never emitted before slow work finishes."""
    return (f'<div id="{escape(target_id, quote=True)}" tabindex="-1" '
            f'data-atlas-result-token="{uuid4().hex}" style="scroll-margin-top:120px"></div>')


def form_scroll_restoration_html() -> str:
    """Keep learning-loop forms in view across Streamlit reruns."""
    return """
    <script>
      (() => {
        const host = window.parent;
        const doc = host.document;
        const storageKey = 'nexmind:form-scroll';
        const maxAgeMs = 360000;

        const isScrollable = (element) => {
          if (!element) return false;
          const overflowY = host.getComputedStyle(element).overflowY;
          return /(auto|scroll|overlay)/.test(overflowY)
            && element.scrollHeight > element.clientHeight + 2;
        };

        const mainScroller = () => [
          doc.querySelector('[data-testid="stMain"]'),
          doc.querySelector('[data-testid="stAppViewContainer"]'),
          doc.scrollingElement
        ].find(isScrollable) || doc.scrollingElement;

        const readSaved = () => {
          let saved = null;
          try {
            saved = JSON.parse(host.sessionStorage.getItem(storageKey) || 'null');
          } catch (_error) {
            host.sessionStorage.removeItem(storageKey);
          }
          if (!saved || Date.now() - Number(saved.savedAt || 0) > maxAgeMs) {
            host.sessionStorage.removeItem(storageKey);
            return null;
          }
          return saved;
        };

        const restoreSavedPosition = () => {
          const saved = readSaved();
          if (!saved) return false;
          const scroller = mainScroller();
          if (!scroller) return false;
          if (saved.waitForResult) {
            const result = doc.getElementById(saved.targetId);
            if (!result?.dataset.atlasResultToken || result.dataset.atlasResultToken === saved.beforeToken) return false;
            const rect = result.getBoundingClientRect();
            if (result.closest('[role="tabpanel"][hidden]')) return false;
            if (rect.top < 100 || rect.top > host.innerHeight - 340) {
              result.scrollIntoView({ block: 'start', behavior: host.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
            }
            result.focus({ preventScroll: true });
            result.parentElement?.classList.add('atlas-result-arrived');
            doc.querySelectorAll('.atlas-submit-status').forEach(node => node.remove());
            doc.querySelectorAll('[data-atlas-busy]').forEach(node => { node.removeAttribute('aria-busy'); node.removeAttribute('data-atlas-busy'); });
            host.sessionStorage.removeItem(storageKey);
            host.__nexmindAtlasPendingForm = null;
            return true;
          }
          const forms = Array.from(doc.querySelectorAll('[data-testid="stForm"]'));
          const restoredForm = forms[Number(saved.formIndex || 0)];
          if (!restoredForm) return false;
          let targetTop = Number(saved.top || 0);
          if (Number.isFinite(Number(saved.formViewportTop))) {
            targetTop = scroller.scrollTop
              + restoredForm.getBoundingClientRect().top
              - Number(saved.formViewportTop);
          }
          scroller.scrollTo({ top: Math.max(0, targetTop), behavior: 'auto' });
          const resultAnchor = doc.getElementById(saved.targetId || 'knowledge-check-results');
          if (resultAnchor?.matches('[tabindex]')) {
            resultAnchor.focus({ preventScroll: true });
          }
          host.sessionStorage.removeItem(storageKey);
          host.__nexmindAtlasPendingForm = null;
          return true;
        };

        const scheduleRestore = () => {
          const pending = host.__nexmindAtlasPendingForm;
          if (pending?.form?.isConnected && !pending.saved.waitForResult) return;
          host.clearTimeout(host.__nexmindAtlasFormRestoreTimer);
          host.__nexmindAtlasFormRestoreTimer = host.setTimeout(() => {
            host.requestAnimationFrame(() => restoreSavedPosition());
          }, 180);
        };

        if (host.__nexmindAtlasFormSubmitHandler) {
          doc.removeEventListener(
            'click',
            host.__nexmindAtlasFormSubmitHandler,
            true
          );
        }

        host.__nexmindAtlasFormSubmitHandler = (event) => {
          const submitButton = event.target.closest('[data-testid="stFormSubmitButton"] button');
          const form = submitButton?.closest('[data-testid="stForm"]');
          const isKnowledgeCheck = Boolean(
            form?.querySelector('[data-atlas-knowledge-check-form]')
          );
          const isLearningLoopForm = Boolean(
            form?.querySelector('[data-atlas-learning-loop-form]')
          );
          const targetMarker = form?.querySelector('[data-atlas-form-target]');
          if (!isKnowledgeCheck && !isLearningLoopForm && !targetMarker) return;
          const targetId = targetMarker?.dataset.atlasFormTarget
            || (isKnowledgeCheck ? 'knowledge-check-results' : 'learning-loop');
          const scroller = mainScroller();
          const forms = Array.from(doc.querySelectorAll('[data-testid="stForm"]'));
          const waitForResult = Boolean(form.querySelector('[data-atlas-wait-result]'));
          if (waitForResult && form.querySelector('.atlas-submit-status') && readSaved()) {
            event.preventDefault(); event.stopPropagation(); return;
          }
          const saved = {
            top: scroller?.scrollTop || 0,
            savedAt: Date.now(),
            targetId,
            formIndex: Math.max(0, forms.indexOf(form)),
            formViewportTop: form.getBoundingClientRect().top,
            waitForResult,
            beforeToken: doc.getElementById(targetId)?.dataset.atlasResultToken || ''
          };
          if (waitForResult) {
            form.setAttribute('aria-busy', 'true'); form.setAttribute('data-atlas-busy', 'true');
            const status = doc.createElement('span');
            status.className = 'atlas-submit-status'; status.setAttribute('role', 'status');
            status.textContent = /[\u4e00-\u9fff]/.test(submitButton.textContent) ? '已收到，Atlas 正在处理…' : 'Received. Atlas is working…';
            form.appendChild(status);
          }
          host.sessionStorage.setItem(storageKey, JSON.stringify(saved));
          host.__nexmindAtlasPendingForm = { form, saved };
        };
        doc.addEventListener('click', host.__nexmindAtlasFormSubmitHandler, true);

        if (host.__nexmindAtlasFormObserver) {
          host.__nexmindAtlasFormObserver.disconnect();
        }
        host.__nexmindAtlasFormObserver = new host.MutationObserver(scheduleRestore);
        host.__nexmindAtlasFormObserver.observe(doc.body, { childList: true, subtree: true });

        // Streamlit can reuse an identical script node across reruns. The
        // observer above handles that case; this call handles a newly executed
        // script after the old form has already been replaced.
        scheduleRestore();
      })();
    </script>
    """


def _journey_narrative_html(text: str, *, is_zh: bool, kind: str) -> str:
    """Render a compact, sentence-safe preview with native full-text disclosure."""
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return "<p></p>"

    limit = 88 if is_zh else 210
    if len(normalized) <= limit:
        return f'<p class="journey-narrative-copy">{escape(normalized)}</p>'

    sentence_marks = "。！？!?。" if is_zh else ".!?"
    minimum = 42 if is_zh else 80
    sentence_ends = [
        index + 1
        for index, character in enumerate(normalized[:limit])
        if character in sentence_marks and index + 1 >= minimum
    ]
    if sentence_ends:
        preview = normalized[: sentence_ends[-1]].strip()
    else:
        soft_marks = "，；,:; "
        candidates = [
            index + 1
            for index, character in enumerate(normalized[:limit])
            if character in soft_marks and index + 1 >= minimum
        ]
        cutoff = candidates[-1] if candidates else limit
        preview = normalized[:cutoff].rstrip("，；,:; ")
        preview += "。" if is_zh else "."

    more_label = {
        (True, "overview"): "展开完整简介",
        (True, "reason"): "展开完整推荐理由",
        (False, "overview"): "Read full overview",
        (False, "reason"): "Read full rationale",
    }[(is_zh, kind)]
    less_label = "收起" if is_zh else "Show less"
    return (
        '<details class="journey-narrative-disclosure">'
        '<summary>'
        f'<span class="journey-narrative-preview">{escape(preview)}</span>'
        '<span class="journey-narrative-action">'
        f'<span class="journey-narrative-more-label">{escape(more_label)}</span>'
        f'<span class="journey-narrative-less-label">{escape(less_label)}</span>'
        f'{_icon_svg("chevron")}</span>'
        '</summary>'
        f'<p class="journey-narrative-full">{escape(normalized)}</p>'
        '</details>'
    )


def reading_dashboard_html(
    *,
    is_zh: bool,
    topic: str,
    duration_weeks: int,
    stage_labels: Sequence[str],
    book_title: str,
    authors: Sequence[str],
    reason: str,
    confidence: str,
    source_links: Sequence[tuple[str, str | None]],
    data_mode: str,
    overview: str = "",
    book: BookCandidate | None = None,
    progress_percent: int = 0,
    current_stage_number: int = 1,
    active_stage_number: int | None = None,
    active_progress_percent: int | None = None,
    stage_progress: Sequence[int] | None = None,
    learner_percent: int | None = None,
    user_id: str = "",
    interface_language: str | None = None,
) -> str:
    title = "阅读旅程" if is_zh else "Reading Journey"
    # A duration is not an elapsed week; no start-date signal is available here.
    week_label = f"计划周期 {duration_weeks} 周" if is_zh else f"{duration_weeks}-week plan"
    stage_word = "阶段" if is_zh else "Stage"
    overview_label = "内容简介" if is_zh else "About this book"
    why_label = "为什么推荐" if is_zh else "Why it fits your path"
    active_stage_number = active_stage_number or current_stage_number
    active_progress_percent = (
        progress_percent if active_progress_percent is None else active_progress_percent
    )
    is_active_view = current_stage_number == active_stage_number
    viewing_completed = progress_percent >= 100 and not is_active_view
    current_label = (
        "当前阅读" if is_zh else "Now reading"
    ) if is_active_view else (
        "阶段回顾" if is_zh else "Reviewing stage"
    ) if viewing_completed else (
        "阶段预览" if is_zh else "Previewing stage"
    )
    evidence_label = "书目信息核验程度" if is_zh else "Book record verification"
    progress_label = "阅读进度" if is_zh else "Reading progress"
    continue_label = "继续阅读" if is_zh else "Continue reading"
    mentor_label = "和 Atlas 聊这本书" if is_zh else "Ask Atlas about this book"
    learner_label = "学习状态" if is_zh else "Learning status"
    source_heading = "书目来源与核验结果" if is_zh else "Sources & verification"
    display_title = book_title.split("：", 1)[0].split(":", 1)[0].strip() if is_zh else book_title

    stage_icons = ("book", "bot", "scale")
    stage_items = []
    normalized_labels = list(stage_labels[:3])
    stage_language = interface_language or ("zh" if is_zh else "en")
    stage_urls: dict[int, str] = {}
    for stage_number in range(1, len(normalized_labels) + 1):
        params = {"ui_language": stage_language, "stage_view": stage_number}
        if user_id:
            params["user_id"] = user_id
        stage_urls[stage_number] = "?" + urlencode(params) + "#reading-journey"
    for index, label in enumerate(normalized_labels, start=1):
        active = index == active_stage_number
        selected = index == current_stage_number
        if stage_progress and index <= len(stage_progress):
            width = min(100, max(0, int(stage_progress[index - 1])))
        else:
            width = 100 if index < active_stage_number else active_progress_percent if active else 0
        complete = width >= 100
        if active:
            stage_status = "当前阶段" if is_zh else "Active stage"
        elif selected and complete:
            stage_status = "正在回顾 · 已完成" if is_zh else "Reviewing · Complete"
        elif selected:
            stage_status = "正在预览" if is_zh else "Previewing"
        elif complete:
            stage_status = "已完成" if is_zh else "Complete"
        else:
            stage_status = f"{width}%"
        state_classes = " ".join(
            item
            for item, enabled in (
                ("active", active),
                ("selected", selected),
                ("complete", complete),
            )
            if enabled
        )
        aria_current = ' aria-current="step"' if selected else ""
        aria_label = (
            f"{stage_word} {index}，{label}，{stage_status}"
            if is_zh
            else f"{stage_word} {index}, {label}, {stage_status}"
        )
        stage_items.append(
            f'<a class="journey-stage {state_classes}" href="{escape(stage_urls[index], quote=True)}" target="_self"'
            f' aria-label="{escape(aria_label, quote=True)}"{aria_current}>'
            f'<span class="journey-stage-number">{index}</span>'
            f'<span class="journey-stage-icon">{_icon_svg(stage_icons[index - 1])}</span>'
            '<span class="journey-stage-copy">'
            f'<span class="journey-stage-title">{stage_word} {index} · {escape(label)}</span>'
            f'<span class="journey-stage-status">{escape(stage_status)}</span>'
            f'<span class="journey-track" role="progressbar" aria-label="{escape(label, quote=True)}" '
            f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{width}"><span style="width:{width}%"></span></span>'
            "</span></a>"
        )

    stage_context = ""
    if not is_active_view:
        context_copy = (
            f"你正在查看第 {current_stage_number} 阶段；主线学习仍在第 {active_stage_number} 阶段。查看、复习或预览不会改变已保存的进度。"
            if is_zh
            else f"You are viewing Stage {current_stage_number}; your active learning stage remains Stage {active_stage_number}. Reviewing or previewing does not change saved progress."
        )
        return_label = "返回当前阶段" if is_zh else "Return to active stage"
        stage_context = (
            '<div class="journey-stage-context" role="status">'
            f'<span>{escape(context_copy)}</span>'
            f'<a href="{escape(stage_urls[active_stage_number], quote=True)}" target="_self">{escape(return_label)}</a>'
            '</div>'
        )

    safe_sources = list(source_links)
    source_pills = []
    for name, url in safe_sources[:2]:
        if url:
            source_pills.append(
                f'<a class="journey-source-pill" href="{escape(str(url), quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'{_icon_svg("library")}<span>{escape(name)}</span></a>'
            )
        else:
            source_pills.append(f'<span class="journey-source-pill">{_icon_svg("library")}<span>{escape(name)}</span></span>')
    if len(safe_sources) > 2:
        source_pills.append(f'<span class="journey-source-pill more">+ {len(safe_sources) - 2} {"个来源" if is_zh else "sources"}</span>')

    source_cards = []
    for name, url in safe_sources[:4]:
        initial = name.strip()[:1].upper() or "S"
        if name == "Amazon Bedrock":
            source_meta = "推理模型" if is_zh else "AI model"
        elif name in {"Transparent scoring rubric", "透明评分规则"}:
            source_meta = "本地评估方法" if is_zh else "Local assessment method"
        else:
            source_meta = "书目信息已核验" if is_zh else "Book details verified"
        inner = (
            f'<span class="journey-source-initial">{escape(initial)}</span>'
            f'<span><span class="journey-source-name">{escape(name)}</span>'
            f'<span class="journey-source-meta">{escape(source_meta)}</span></span>'
            f'{_icon_svg("chevron")}'
        )
        if url:
            source_cards.append(
                f'<a class="journey-source-card" href="{escape(str(url), quote=True)}" target="_blank" rel="noopener noreferrer">{inner}</a>'
            )
        else:
            source_cards.append(f'<div class="journey-source-card">{inner}</div>')

    author_text = ", ".join(authors) if authors else ("暂无作者信息" if is_zh else "Author not available")
    confidence_text = {"high": "高" if is_zh else "High", "medium": "中" if is_zh else "Medium", "low": "低" if is_zh else "Low"}.get(confidence, confidence)
    # This dashboard is rendered only after RecommendationResult exists, so every
    # pipeline step shown here has completed. Source provenance is kept visible
    # without presenting cached or mixed evidence as an active background task.
    progress_values = [min(100, max(0, int(value))) for value in (stage_progress or [progress_percent])]
    overall_progress = round(sum(progress_values) / max(1, len(progress_values)))
    has_mastery = learner_percent is not None
    mastery_value = min(100, max(0, int(learner_percent or 0)))
    summary_percent = mastery_value if has_mastery else overall_progress
    understanding = (
        "本书已答题目的理解参考" if is_zh else "Understanding estimate from this book's answers"
    ) if has_mastery else (
        f"“{topic}”阅读路径总进度" if is_zh else f"Overall reading progress for {topic}"
    )
    rows = (
        ("book", "当前阶段阅读" if is_zh else "Active-stage reading", min(100, max(0, int(active_progress_percent)))),
        ("network", "知识诊断" if is_zh else "Knowledge diagnosis", mastery_value),
        ("target", "整条路径进度" if is_zh else "Overall path progress", overall_progress),
    )
    model_rows = "".join(
        '<div class="journey-model-row">'
        f'{_icon_svg(icon)}<span><span class="journey-model-label">{escape(label)}</span>'
        f'<span class="journey-track" role="progressbar" aria-label="{escape(label, quote=True)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{value}"><span style="width:{value}%"></span></span></span>'
        f'<span class="journey-model-value">{value}%</span></div>'
        for icon, label, value in rows
    )
    cover_art = (
        '<svg viewBox="0 0 240 210" preserveAspectRatio="none" aria-hidden="true">'
        '<path d="M0 82 54 34l46 42 45-55 95 78v111H0Z" fill="#174f9f" opacity=".88"/>'
        '<path d="M0 132 62 86l46 36 48-52 84 58v82H0Z" fill="#397ac3" opacity=".92"/>'
        '<path d="M0 167 69 123l55 34 48-31 68 38v46H0Z" fill="#8ebced"/>'
        '<path d="M104 210c1-39 20-39 11-78-3-15-1-26 9-39 6 25 1 40 10 58 10 20 5 40-2 59Z" fill="#d9ebff" opacity=".92"/>'
        '<circle cx="120" cy="119" r="24" fill="#123d7c"/><path d="M109 104c12-16 33-7 31 9-2 13-8 18-2 29h-31c6-14 3-24 2-38Z" fill="#0d2e61"/>'
        '<circle cx="120" cy="119" r="33" fill="none" stroke="#b9d8fb" stroke-width=".7" opacity=".55"/>'
        '<path d="M88 119h64M120 86v66M96 96l48 48M144 96l-48 48" stroke="#b9d8fb" stroke-width=".7" opacity=".5"/>'
        '</svg>'
    )
    cover_url = _book_cover_url(book) if book is not None else None
    cover_image = ""
    if cover_url:
        cover_alt = f"《{book_title}》封面" if is_zh else f"Cover of {book_title}"
        cover_class = "journey-cover-image google-cover" if "books.google." in cover_url else "journey-cover-image"
        cover_image = (
            f'<img class="{cover_class}" src="{escape(cover_url, quote=True)}" '
            f'alt="{escape(cover_alt, quote=True)}" width="464" height="696" '
            'loading="eager" fetchpriority="high" onerror="this.hidden=true">'
        )
    overview_text = overview.strip() or (
        f"《{book_title}》的内容将在下方推荐书目中详细介绍。"
        if is_zh
        else f"A detailed introduction to {book_title} appears in the recommendation section below."
    )
    overview_html = _journey_narrative_html(overview_text, is_zh=is_zh, kind="overview")
    reason_html = _journey_narrative_html(reason, is_zh=is_zh, kind="reason")

    return (
        '<main class="journey-page" id="atlas-main" tabindex="-1">'
        '<div class="journey-page-head" id="reading-journey" aria-labelledby="reading-journey-title">'
        f'<div class="journey-page-title" id="reading-journey-title" role="heading" aria-level="1">{escape(title)}</div>'
        f'<div class="journey-week">{_icon_svg("calendar")}<span>{escape(week_label)}</span></div></div>'
        f'<section class="journey-panel journey-stages" aria-label="{escape(title, quote=True)}">{"".join(stage_items)}{stage_context}</section>'
        '<div class="journey-primary-grid">'
        '<article class="journey-panel journey-current">'
        '<div class="journey-current-body">'
        f'<div class="journey-cover"><div class="journey-cover-title">{escape(book_title)}</div><div class="journey-cover-art">{cover_art}</div>{cover_image}</div>'
        f'<div class="journey-current-copy{" zh" if is_zh else ""}">'
        f'<span class="journey-kicker">{escape(current_label)}</span><h2 class="journey-book-title" aria-label="{escape(book_title, quote=True)}">{escape(display_title)}</h2>'
        f'<div class="journey-authors">{escape(author_text)}</div>'
        '<div class="journey-narratives">'
        f'<div class="journey-overview"><span class="journey-overview-icon">{_icon_svg("note")}</span><span><strong>{escape(overview_label)}</strong>{overview_html}</span></div>'
        f'<div class="journey-why"><span class="journey-why-icon">{_icon_svg("book")}</span><span><strong>{escape(why_label)}</strong>{reason_html}</span></div>'
        '</div>'
        f'<div class="journey-confidence">{_icon_svg("shield")}<span>{escape(evidence_label)}{"：" if is_zh else ": "}<strong>{escape(confidence_text)}</strong></span></div>'
        f'<div class="journey-source-pills">{"".join(source_pills)}</div>'
        '</div></div>'
        '<div class="journey-current-foot">'
        f'<span>{escape(progress_label)}</span><span class="journey-track" role="progressbar" aria-label="{escape(progress_label, quote=True)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{progress_percent}"><span style="width:{progress_percent}%"></span></span>'
        f'<strong>{progress_percent}%</strong><a class="journey-mentor-link" href="#book-stage-{current_stage_number}">{_icon_svg("bot")}{escape(mentor_label)}</a>'
        f'<a class="journey-continue" href="{escape("#learning-loop" if is_active_view else stage_urls[active_stage_number], quote=True)}" target="_self">'
        f'{escape(continue_label if is_active_view else ("返回当前阶段" if is_zh else "Return to active stage"))}{_icon_svg("chevron")}</a>'
        '</div></article>'
        '<aside class="journey-panel journey-learner">'
        f'<div class="journey-panel-title"><span class="journey-title-icon">{_icon_svg("user")}</span><span>{escape(learner_label)}</span></div>'
        '<div class="journey-model-summary">'
        f'<span class="journey-ring" style="--value:{summary_percent}%"><strong>{summary_percent}%</strong></span>'
        f'<span><strong>{escape(understanding)}</strong><span>{escape(week_label)}</span></span></div>'
        f'<div class="journey-model-list">{model_rows}</div></aside>'
        '</div>'
        f'<section class="journey-panel journey-sources" id="journey-sources"><div class="journey-sources-title" role="heading" aria-level="2">{escape(source_heading)}</div><div class="journey-source-grid">{"".join(source_cards)}</div></section>'
        '</main>'
    )


def _hero_book_scene_svg() -> str:
    # Blank lines end raw-HTML blocks in Streamlit's Markdown renderer. Keep
    # the model one continuous HTML block so its geometry stays inside the SVG.
    return "".join(line.strip() for line in hero_book_scene_svg().splitlines())



def hero_html(is_zh: bool, *, has_path: bool = False) -> str:
    if is_zh:
        eyebrow = "ATLAS · 你的智能阅读伙伴"
        title_lines = ("找到适合你的书，", "把疑问变成理解。")
        copy = "从学习目标和已有基础出发，Atlas 帮你核对书籍、安排阅读顺序。读不懂时随时提问，再通过小练习和进度反馈调整后续计划。"
        visual_label = "立体书籍向全息智能球体汇聚知识，象征 Atlas 从选书、答疑到练习的学习支持"
        motion_toggle_label = "暂停或播放背景动态"
        motion_pause = "暂停动态"
        motion_play = "播放动态"
        primary_label = "继续我的阅读" if has_path else "开始规划我的阅读"
        secondary_label = "和 Atlas 聊聊"
    else:
        eyebrow = "ATLAS · AGENTIC READING COMPANION"
        title_lines = ("From the right book", "to real understanding.")
        copy = "Find books that fit your goals and experience, with sources checked and a clear reading order. Ask when you're stuck, test your understanding, and shape the next step with your feedback."
        visual_label = "An animated book linked to a holographic intelligence sphere, representing Atlas support from discovery through questions and practice"
        motion_toggle_label = "Pause or play background motion"
        motion_pause = "Pause motion"
        motion_play = "Play motion"
        primary_label = "Continue reading" if has_path else "Tell Atlas what I want to learn"
        secondary_label = "Ask Atlas"
    primary_href = "#reading-journey" if has_path else "#learning-brief"
    secondary_href = "#learning-loop"
    secondary_action_html = (
        f'<a class="atlas-hero-action" href="{secondary_href}">{_icon_svg("bot")}{escape(secondary_label)}</a>'
        if has_path
        else ""
    )
    title_html = "".join(
        f'<span class="atlas-hero-title-line">{escape(line)}</span>' for line in title_lines
    )
    return (
        f'<section class="atlas-hero {"atlas-hero-zh" if is_zh else "atlas-hero-en"}" '
        'id="atlas-introduction" aria-labelledby="atlas-introduction-title">'
        '<div class="atlas-hero-stage"><div class="atlas-hero-copy-column">'
        f'<div class="atlas-eyebrow">{escape(eyebrow)}</div>'
        # Streamlit rewrites literal h1 elements with a permalink row. Retain
        # heading semantics and a stable labelledby target without that chrome.
        f'<div class="atlas-hero-title" id="atlas-introduction-title" role="heading" aria-level="1">{title_html}</div>'
        f'<p class="atlas-hero-copy">{escape(copy)}</p>'
        '<div class="atlas-hero-actions">'
        f'<a class="atlas-hero-action primary" href="{primary_href}">{escape(primary_label)}{_icon_svg("chevron")}</a>'
        f'{secondary_action_html}'
        '</div></div>'
        f'<div class="atlas-hero-visual" aria-label="{escape(visual_label, quote=True)}">'
        '<input class="atlas-motion-toggle" id="atlas-motion-toggle" type="checkbox" role="switch" '
        f'aria-label="{escape(motion_toggle_label, quote=True)}">'
        '<label class="atlas-motion-control" for="atlas-motion-toggle">'
        f'<span class="atlas-motion-pause">{_icon_svg("pause")}{escape(motion_pause)}</span>'
        f'<span class="atlas-motion-play">{_icon_svg("play")}{escape(motion_play)}</span></label>'
        f'{_hero_book_scene_svg()}</div></div>'
        "</section>"
    )


def activity_history_html(
    paths: Sequence[ReadingPath],
    *,
    active_version: int,
    verified_book_count: int,
    data_mode: str,
    is_zh: bool,
) -> str:
    """Render a user-facing activity summary and inspectable plan versions."""
    versions = sorted(paths, key=lambda item: item.version, reverse=True)
    if not versions:
        return ""

    if is_zh:
        intro_title = "你的旧方案仍然保留"
        intro_copy = "每次调整都会另存为一个版本，不会覆盖先前方案或已经记录的阅读进度。展开任一版本即可查看当时的阶段顺序。"
        active_label = "当前方案"
        earlier_label = "历史版本"
        active_stat = "当前版本"
        saved_stat = "已保存版本"
        version_heading = "路径版本"
        version_note = "保存在你的 Atlas 工作区，可随时回看"
        stage_unit = "个阶段"
        hour_unit = "小时"
        events = (
            ("理解学习需求", "已记录学习目标、已有基础和时间安排"),
            ("核验候选书目", f"已核验并评估 {verified_book_count} 本入选书籍"),
            ("生成当前路径", f"路径 v{active_version} 已启用，旧版本继续保留"),
        )
    else:
        intro_title = "Your earlier plans are still available"
        intro_copy = "Every adjustment is saved as a separate version. Earlier plans and recorded reading progress are never overwritten. Expand any version to review its stage order."
        active_label = "Current plan"
        earlier_label = "Earlier version"
        active_stat = "Current version"
        saved_stat = "Saved versions"
        version_heading = "Plan versions"
        version_note = "Saved in your Atlas workspace for review"
        stage_unit = "stages"
        hour_unit = "hours"
        events = (
            ("Understood your goal", "Saved your learning goal, background, and available time"),
            ("Verified the books", f"Verified and assessed {verified_book_count} selected books"),
            ("Built the active path", f"Plan v{active_version} is active and earlier versions remain available"),
        )

    source_label = {
        "live": "实时来源" if is_zh else "Live sources",
        "mixed": "实时与已核验缓存" if is_zh else "Live and verified cache",
        "cached_demo": "已核验缓存" if is_zh else "Verified cache",
    }.get(data_mode, "已保存" if is_zh else "Saved")
    event_html = "".join(
        '<div class="atlas-activity-event">'
        f'<span class="atlas-activity-event-index">{index:02}</span>'
        f'<span><strong>{escape(title)}</strong><span>{escape(detail)}</span></span></div>'
        for index, (title, detail) in enumerate(events, start=1)
    )
    version_cards = []
    for path in versions:
        is_current = path.version == active_version
        status = active_label if is_current else earlier_label
        stages = "".join(
            '<div class="atlas-version-stage">'
            f'<span>{stage.stage_number:02}</span>'
            f'<strong>{escape(stage.title)}</strong>'
            f'<small>{stage.estimated_hours:g} {escape(hour_unit)}</small></div>'
            for stage in path.stages
        )
        version_cards.append(
            f'<details class="atlas-version-card{" current" if is_current else ""}"{" open" if is_current else ""}>'
            '<summary>'
            f'<span class="atlas-version-dot">{_icon_svg("history")}</span>'
            f'<span class="atlas-version-title"><strong>v{path.version}</strong><small>{escape(status)}</small></span>'
            f'<span class="atlas-version-meta">{len(path.stages)} {escape(stage_unit)} · {path.total_estimated_hours:g} {escape(hour_unit)}</span>'
            f'{_icon_svg("chevron")}</summary>'
            f'<div class="atlas-version-stages">{stages}</div></details>'
        )

    return (
        '<section class="atlas-activity-shell" aria-label="'
        + escape(version_heading, quote=True)
        + '">'
        '<div class="atlas-activity-summary">'
        '<div class="atlas-activity-intro">'
        f'<span class="atlas-activity-intro-icon">{_icon_svg("history")}</span>'
        f'<span><strong>{escape(intro_title)}</strong><span>{escape(intro_copy)}</span></span></div>'
        f'<div class="atlas-activity-stat"><small>{escape(active_stat)}</small><strong>v{active_version} · {escape(source_label)}</strong></div>'
        f'<div class="atlas-activity-stat"><small>{escape(saved_stat)}</small><strong>{len(versions)}</strong></div>'
        '</div>'
        f'<div class="atlas-activity-events">{event_html}</div>'
        '<div class="atlas-version-list">'
        f'<div class="atlas-version-heading"><strong>{escape(version_heading)}</strong><span>{escape(version_note)}</span></div>'
        + "".join(version_cards)
        + '</div></section>'
    )


def section_header(index: str, title: str, description: str = "") -> str:
    detail = f'<p class="atlas-section-copy">{escape(description)}</p>' if description else ""
    title_html = f'<h2>{escape(title)}</h2>' if title else ""
    compact_class = " compact" if not title else ""
    return (
        f'<div class="atlas-section-head{compact_class}">'
        f'<div><div class="atlas-section-index">{escape(index)}</div>{title_html}</div>'
        f"{detail}</div>"
    )


def provider_html(name: str, model: str, live: bool = True, state_label: str | None = None) -> str:
    state = state_label or ("Live model" if live else "Demo model")
    offline_class = "" if live else " offline"
    return (
        f'<div class="atlas-provider{offline_class}" role="status">'
        f'<div class="atlas-provider-top"><span class="atlas-live-dot"></span>{escape(name)} · {escape(state)}</div>'
        f'<div class="atlas-provider-model">{escape(model)}</div>'
        "</div>"
    )


def status_html(label: str, detail: str, warning: bool = False) -> str:
    warning_class = " warning" if warning else ""
    return (
        f'<div class="atlas-status{warning_class}" role="status">'
        f'<span class="atlas-status-name">{escape(label)}</span>'
        f'<span class="atlas-status-meta">{escape(detail)}</span>'
        "</div>"
    )


def learning_module_scope_html(
    *,
    is_zh: bool,
    number: int,
    title: str,
    responsibility: str,
    input_text: str,
    output_text: str,
    boundary: str,
) -> str:
    """Make one learning-loop module's responsibility and guardrail explicit."""
    labels = (
        ("你可以告诉 Atlas", "你会得到", "不会发生")
        if is_zh
        else ("Tell Atlas", "You will get", "Will not happen")
    )
    module_label = "这里可以" if is_zh else "Use this for"
    label_separator = "：" if is_zh else ": "
    facts = "".join(
        f'<div class="atlas-module-fact"><small>{escape(label)}</small><span>{escape(value)}</span></div>'
        for label, value in zip(labels, (input_text, output_text, boundary), strict=True)
    )
    return (
        '<section class="atlas-module-scope">'
        '<div class="atlas-module-title">'
        f'<span class="atlas-module-number">{number}</span><span><strong>{escape(title)}</strong>'
        f'<span>{escape(module_label)}{label_separator}{escape(responsibility)}</span></span></div>{facts}</section>'
    )


def mentor_workspace_html(
    *,
    is_zh: bool,
    book_title: str,
    stage_number: int,
    progress_percent: int,
) -> str:
    heading = "随时告诉 Atlas 你的真实情况" if is_zh else "Tell Atlas what is really happening"
    copy = (
        "你可以直接提问、汇报进度、说明某本书不合适，或要求重新安排整条路径。Atlas 会先说明将采取的行动，再更新你的学习状态。"
        if is_zh
        else "Ask a question, report progress, explain why a book is not working, or request a new plan. Atlas explains the action it takes before updating your learning state."
    )
    kicker = "AI 阅读导师" if is_zh else "AI READING MENTOR"
    stage_label = f"第 {stage_number} 阶段 ·《{book_title}》" if is_zh else f"Stage {stage_number} · {book_title}"
    progress_label = "当前进度" if is_zh else "Current progress"
    return (
        '<section class="atlas-mentor-hero">'
        '<div>'
        f'<span class="atlas-mentor-kicker">{_icon_svg("bot")}{escape(kicker)}</span>'
        f'<h3>{escape(heading)}</h3><p>{escape(copy)}</p>'
        '</div>'
        '<div class="atlas-mentor-context">'
        f'<span>{escape(progress_label)}</span><strong>{escape(stage_label)}</strong>'
        f'<span class="journey-track" role="progressbar" aria-label="{escape(progress_label, quote=True)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{progress_percent}"><span style="width:{progress_percent}%"></span></span>'
        '</div></section>'
    )


def mentor_conversation_html(
    messages: Sequence[dict[str, object]],
    *,
    is_zh: bool,
    compact: bool = False,
) -> str:
    if not messages:
        title = "从一句真实反馈开始" if is_zh else "Start with one honest update"
        examples = (
            "例如：“我读到 40%，第三章没看懂”或“这本书太理论，请只替换这一本”。"
            if is_zh
            else 'For example: “I am 40% through and chapter 3 is unclear” or “This is too theoretical—replace only this book.”'
        )
        return (
            '<div class="atlas-mentor-thread" role="log" aria-live="polite">'
            f'<div class="atlas-mentor-empty"><span><strong>{escape(title)}</strong>{escape(examples)}</span></div></div>'
        )
    visible_messages = list(messages[-6:] if compact else messages[-16:])
    rendered = []
    for message in visible_messages:
        role = "user" if message.get("role") == "user" else "assistant"
        avatar = "我" if is_zh and role == "user" else "You" if role == "user" else "A"
        plain_content = str(message.get("content", "")).replace("**", "").replace("###", "")
        content = escape(plain_content).replace("\n", "<br>")
        action = message.get("action") if isinstance(message.get("action"), dict) else {}
        next_step = str(action.get("next_step", "")).strip() if action else ""
        action_html = ""
        if role == "assistant" and next_step:
            label = "下一步" if is_zh else "Next step"
            separator = "：" if is_zh else ": "
            action_html = (
                f'<span class="atlas-mentor-action">{_icon_svg("target")}<span>'
                f'{escape(label)}{separator}{escape(next_step)}</span></span>'
            )
        rendered.append(
            f'<article class="atlas-mentor-message {role}"><span class="atlas-mentor-avatar">{escape(avatar)}</span>'
            f'<div class="atlas-mentor-bubble">{content}{action_html}</div></article>'
        )
    return '<div class="atlas-mentor-thread" role="log" aria-live="polite">' + "".join(rendered) + "</div>"


def accountability_card_html(
    *,
    is_zh: bool,
    next_step: str,
    cadence: str,
    target_minutes: int,
    enabled: bool,
    companion_enabled: bool,
    check_in_due: bool,
) -> str:
    if not enabled:
        title = "学习检查尚未开启" if is_zh else "Progress check-ins are off"
        status = "未开启" if is_zh else "Off"
        detail = (
            "打开下方设置后，Atlas 会在你下次访问时按所选节奏询问进展。"
            if is_zh
            else "Turn on the setting below and Atlas will ask for progress on a future visit."
        )
        state_class = "is-off"
    elif check_in_due:
        if is_zh:
            title = "小 Atlas 在等你汇报" if companion_enabled else "该汇报学习进展了"
            detail = f"检查节奏：{cadence}。只在你打开本页时提醒，不会在后台打扰你。"
            status = "现在检查"
        else:
            title = (
                "Atlas is ready for your check-in"
                if companion_enabled
                else "Your check-in is due"
            )
            detail = (
                f"Cadence: {cadence}. Reminders appear only while this page is open; "
                "no background notification is sent."
            )
            status = "Due now"
        state_class = "is-due"
    else:
        if is_zh:
            title = "小 Atlas · 你的学习伙伴" if companion_enabled else "学习检查已开启"
            detail = (
                f"从下方开始一次 {target_minutes} 分钟专注阅读；结束后直接汇报进度和疑问。"
                if companion_enabled
                else "到期后会在你下次打开本页时询问进展；你的汇报和自测会更新下一步。"
            )
        else:
            title = (
                "Little Atlas · Your study companion"
                if companion_enabled
                else "Progress check-ins are active"
            )
            detail = (
                f"Start a {target_minutes}-minute focus session below, then report your progress and questions here."
                if companion_enabled
                else "When due, Atlas will ask for progress on your next visit. Reports and knowledge checks refresh your next step."
            )
        status = cadence
        state_class = "is-active"
    icon = _companion_svg() if companion_enabled and enabled else _icon_svg("calendar")
    next_label = "当前下一步" if is_zh else "Current next step"
    separator = "：" if is_zh else ": "
    next_html = (
        f'<p class="atlas-accountability-next">{escape(next_label)}{separator}{escape(next_step)}</p>'
        if enabled
        else ""
    )
    return (
        f'<section class="atlas-accountability-card {state_class}" '
        f'aria-label="{escape(title, quote=True)}">'
        f'<span class="atlas-accountability-icon">{icon}</span>'
        '<div class="atlas-accountability-copy">'
        f'<div class="atlas-accountability-head"><strong>{escape(title)}</strong>'
        f'<span class="atlas-accountability-status">{escape(status)}</span></div>'
        f'<p class="atlas-accountability-detail">{escape(detail)}</p>{next_html}</div></section>'
    )


def companion_preview_html(
    *,
    is_zh: bool,
    cadence: str,
    target_minutes: int,
    tone: str,
) -> str:
    """Show an unmistakable preview of the enabled Atlas study companion."""
    tone_key = tone if tone in {"supportive", "direct", "concise"} else "supportive"
    if is_zh:
        title = "小 Atlas 已显示"
        samples = {
            "supportive": f"今天能读一点就是进展。准备好时，先专注 {target_minutes} 分钟，回来告诉我哪里顺利、哪里卡住。",
            "direct": f"今天的目标是专注阅读 {target_minutes} 分钟。完成后请立即汇报进度和一个具体问题。",
            "concise": f"本次目标：阅读 {target_minutes} 分钟。完成后汇报。",
        }
        meta = f"提醒节奏：{cadence} · 这是提醒语气示例"
    else:
        title = "Little Atlas is visible"
        samples = {
            "supportive": f"Any reading today is progress. Focus for {target_minutes} {'minute' if target_minutes == 1 else 'minutes'}, then tell me what felt clear or difficult.",
            "direct": f"Today’s target is {target_minutes} focused minutes. Report your progress and one specific question when you finish.",
            "concise": f"Goal: read for {target_minutes} {'minute' if target_minutes == 1 else 'minutes'}. Report when finished.",
        }
        meta = f"Check-in rhythm: {cadence} · Coaching-tone preview"
    return (
        '<section class="atlas-companion-preview" role="status">'
        f'<span class="atlas-companion-preview-mark">{_companion_svg()}</span>'
        f'<div><strong>{escape(title)}</strong><p>{escape(samples[tone_key])}</p>'
        f'<small>{escape(meta)}</small></div></section>'
    )


def reading_session_completion_html(
    *,
    is_zh: bool,
    book_title: str,
    target_minutes: int,
    actual_minutes: int,
    progress_percent: int,
) -> str:
    """Celebrate a saved focus session and make the reflection step explicit."""
    safe_target = max(1, min(int(target_minutes), 180))
    safe_actual = max(1, int(actual_minutes))
    safe_progress = max(0, min(int(progress_percent), 100))
    reached_target = safe_actual >= safe_target
    if is_zh:
        kicker = "专注阅读已完成" if reached_target else "本次阅读已保存"
        title = "做得很好，这一段读完了"
        timing = (
            f"小 Atlas 已记录这次 {safe_target} 分钟专注阅读。"
            if reached_target
            else f"你提前结束了本次阅读，小 Atlas 已记录 {safe_actual} 分钟。"
        )
        detail = (
            f"{timing} 趁内容还新鲜，可以提出一个疑问，或让我用一道题检查你的理解。"
        )
        progress_label = f"阅读进度 {safe_progress}%"
        book_label = f"《{book_title}》"
    else:
        kicker = "Focus session complete" if reached_target else "Session saved"
        title = "Nice work—you finished this reading block"
        timing = (
            f"Little Atlas recorded your {safe_target}-minute focus session."
            if reached_target
            else f"You finished early, and Little Atlas recorded {safe_actual} {'minute' if safe_actual == 1 else 'minutes'}."
        )
        detail = (
            f"{timing} While it is fresh, ask one question or let me check your understanding with one prompt."
        )
        progress_label = f"Reading progress {safe_progress}%"
        book_label = book_title
    return (
        '<section class="atlas-session-complete" role="status" aria-live="polite">'
        f'<span class="atlas-session-complete-mark" aria-hidden="true">{_companion_svg()}</span>'
        '<div>'
        f'<span class="atlas-session-complete-kicker">{escape(kicker)}</span>'
        f'<h3>{escape(title)}</h3><p>{escape(detail)}</p>'
        '<div class="atlas-session-complete-meta">'
        f'<span>{escape(book_label)}</span><span>{escape(progress_label)}</span>'
        '</div></div></section>'
    )


def reading_session_timer_html(
    *,
    is_zh: bool,
    book_title: str,
    target_minutes: int,
    elapsed_seconds: int,
) -> str:
    """Render a self-contained, accessible focus timer for a running reading session."""
    safe_target = max(1, min(int(target_minutes), 180))
    safe_elapsed = max(0, int(elapsed_seconds))
    title = "小 Atlas 正在为你计时" if is_zh else "Little Atlas is timing this session"
    book_label = f"正在阅读《{book_title}》" if is_zh else f"Reading {book_title}"
    remaining_label = "剩余时间" if is_zh else "Time remaining"
    done_label = "时间到了，可以在下方汇报" if is_zh else "Time is up—report below when ready"
    helper = (
        "即使提前完成，也可以直接汇报；计时不会限制你的操作。"
        if is_zh
        else "You can report early; the timer never blocks your controls."
    )
    return f"""
    <style>
      html, body {{ margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; color: #17243a; background: transparent; }}
      .focus-session {{ display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 14px; align-items: center; min-height: 76px; padding: 14px 16px; border: 1px solid #cfe0fa; border-radius: 14px; background: linear-gradient(135deg, #f8fbff 0%, #edf5ff 100%); box-sizing: border-box; }}
      .focus-icon {{ width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px; color: white; background: linear-gradient(145deg, #2f80ed, #155bc7); box-shadow: 0 7px 16px rgba(23, 105, 224, .2); }}
      .focus-icon svg {{ width: 22px; height: 22px; }}
      .focus-copy strong {{ display: block; margin-bottom: 3px; font-size: 16px; line-height: 1.35; }}
      .focus-copy span {{ display: block; overflow-wrap: anywhere; color: #60738e; font-size: 14px; line-height: 1.45; }}
      .focus-clock {{ min-width: 116px; text-align: right; }}
      .focus-clock small {{ display: block; margin-bottom: 2px; color: #65778f; font-size: 12px; font-weight: 650; }}
      .focus-clock strong {{ color: #1769e0; font-size: 26px; font-variant-numeric: tabular-nums; letter-spacing: .02em; }}
      .focus-done {{ display: none; margin-top: 3px; color: #155bc7; font-size: 12px; font-weight: 700; }}
      .focus-helper {{ grid-column: 2 / -1; margin: -5px 0 0; color: #6a7b92; font-size: 12px; }}
      @media (max-width: 560px) {{
        .focus-session {{ grid-template-columns: auto minmax(0, 1fr); }}
        .focus-clock {{ grid-column: 2; text-align: left; }}
        .focus-helper {{ grid-column: 1 / -1; }}
      }}
      @media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
    </style>
    <section class="focus-session" aria-label="{escape(title, quote=True)}">
      <span class="focus-icon" aria-hidden="true">{_companion_svg()}</span>
      <div class="focus-copy"><strong>{escape(title)}</strong><span>{escape(book_label)}</span></div>
      <div class="focus-clock">
        <small>{escape(remaining_label)}</small>
        <strong id="atlas-focus-clock">--:--</strong>
        <span id="atlas-focus-done" class="focus-done" role="status">{escape(done_label)}</span>
      </div>
      <p class="focus-helper">{escape(helper)}</p>
    </section>
    <script>
      (() => {{
        const total = {safe_target * 60};
        const startedElapsed = {safe_elapsed};
        const startedAt = Date.now();
        const clock = document.getElementById('atlas-focus-clock');
        const done = document.getElementById('atlas-focus-done');
        let announced = false;
        const render = () => {{
          const liveElapsed = Math.floor((Date.now() - startedAt) / 1000);
          const remaining = Math.max(0, total - startedElapsed - liveElapsed);
          const minutes = Math.floor(remaining / 60);
          const seconds = remaining % 60;
          clock.textContent = `${{String(minutes).padStart(2, '0')}}:${{String(seconds).padStart(2, '0')}}`;
          if (remaining === 0) {{
            done.style.display = 'block';
            if (!announced) {{ done.setAttribute('aria-live', 'polite'); announced = true; }}
            return false;
          }}
          return true;
        }};
        render();
        const timer = window.setInterval(() => {{ if (!render()) window.clearInterval(timer); }}, 1000);
      }})();
    </script>
    """


def execution_trace_html(steps: Iterable[str]) -> str:
    rows = "".join(
        '<div class="atlas-trace-row">'
        f'<span class="atlas-trace-step">{index:02}</span><span>{escape(step)}</span>'
        "</div>"
        for index, step in enumerate(steps, start=1)
    )
    return f'<div class="atlas-trace">{rows}</div>'


def concept_card_html(role: str, concept: str, importance_label: str, importance: str) -> str:
    return (
        '<article class="atlas-concept-card">'
        f'<div class="atlas-card-role">{escape(role)}</div>'
        f'<div class="atlas-card-title">{escape(concept)}</div>'
        f'<div class="atlas-card-foot">{escape(importance_label)} · {escape(importance)}</div>'
        "</article>"
    )


def score_grid_html(scores: Sequence[tuple[str, float]]) -> str:
    cards = "".join(
        '<div class="atlas-score">'
        f'<div class="atlas-score-top"><span>{escape(label)}</span><strong>{value:.0%}</strong></div>'
        f'<div class="atlas-score-track" role="progressbar" aria-label="{escape(label, quote=True)}" '
        f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{max(0, min(100, value * 100)):.0f}">'
        f'<div class="atlas-score-fill" style="width:{max(0, min(100, value * 100)):.0f}%"></div></div>'
        "</div>"
        for label, value in scores
    )
    return f'<div class="atlas-score-grid">{cards}</div>'


def fit_score_dimensions(
    assessment: BookAssessment, is_zh: bool
) -> tuple[tuple[str, float], ...]:
    """Return the canonical, consistently ordered labels for all six fit scores."""
    labels = (
        ("目标相关性", "Goal relevance", assessment.goal_relevance),
        ("学习基础匹配度", "Prior-knowledge fit", assessment.prerequisite_fit),
        ("书目信息核验充分度", "Bibliographic verification", assessment.evidence_strength),
        ("视角补充价值", "Perspective value", assessment.perspective_value),
        ("阅读时间可行性", "Time feasibility", assessment.time_feasibility),
        ("语言偏好匹配度", "Language fit", assessment.language_fit),
    )
    return tuple((chinese if is_zh else english, value) for chinese, english, value in labels)


def _book_cover_url(book: BookCandidate) -> str | None:
    explicit = getattr(book, "cover_url", None)
    if explicit:
        return str(explicit)
    return None


def book_cover_html(book: BookCandidate, is_zh: bool, variant: str = "detail") -> str:
    """Render a stable 2:3 cover frame with a graceful title-based fallback."""
    variant = "fit" if variant == "fit" else "detail"
    cover_url = _book_cover_url(book)
    title = book.title.strip()
    monogram = next((char.upper() for char in title if char.isalnum()), "N")
    accessible_label = f"《{title}》封面" if is_zh else f"Cover of {title}"
    image_html = ""
    if cover_url:
        loading = "eager" if variant == "fit" else "lazy"
        fetch_priority = ' fetchpriority="high"' if variant == "fit" else ""
        image_html = (
            f'<img class="atlas-cover-image atlas-cover-image--{variant}" src="{escape(cover_url, quote=True)}" alt="" '
            f'width="328" height="492" loading="{loading}" decoding="async"{fetch_priority} '
            'onerror="this.hidden=true">'
        )
    return (
        f'<figure class="atlas-cover-card atlas-cover-card--{variant}" role="img" '
        f'aria-label="{escape(accessible_label, quote=True)}">'
        '<span class="atlas-cover-placeholder" aria-hidden="true">'
        f'<span class="atlas-cover-monogram">{escape(monogram)}</span>'
        f'<strong>{escape(title)}</strong></span>{image_html}</figure>'
    )


def book_fit_result_html(evaluation: BookSearchEvaluation, is_zh: bool) -> str:
    book = evaluation.book
    assessment = evaluation.assessment
    score = max(0, min(100, round(assessment.overall_rank_score * 100)))
    if score >= 80:
        verdict = "高度契合" if is_zh else "Strong fit"
    elif score >= 65:
        verdict = "较为契合" if is_zh else "Good fit"
    elif score >= 50:
        verdict = "部分契合" if is_zh else "Partial fit"
    else:
        verdict = "契合度较低" if is_zh else "Low fit"
    role_labels = {
        "Conceptual Foundation": "基础概念" if is_zh else "Foundational concepts",
        "Technical/Application": "技术原理与应用" if is_zh else "Technical principles & applications",
        "Critical/Cross-disciplinary": "批判思考与跨学科视角" if is_zh else "Critical & interdisciplinary perspectives",
    }
    dimensions = fit_score_dimensions(assessment, is_zh)
    dimension_html = "".join(
        '<div class="atlas-score">'
        f'<div class="atlas-score-top"><span>{escape(label)}</span><strong>{value:.0%}</strong></div>'
        f'<div class="atlas-score-track" role="progressbar" aria-label="{escape(label, quote=True)}" '
        f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{value * 100:.0f}">'
        f'<div class="atlas-score-fill" style="width:{value * 100:.0f}%"></div></div></div>'
        for label, value in dimensions
    )
    sources = []
    seen_source_names: set[str] = set()
    for record in book.source_records:
        if record.source_name in seen_source_names:
            continue
        seen_source_names.add(record.source_name)
        label = escape(record.source_name)
        if record.source_url:
            sources.append(
                f'<a class="atlas-book-fit-source" href="{escape(str(record.source_url), quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{label}</a>'
            )
        else:
            sources.append(f'<span class="atlas-book-fit-source">{label}</span>')
    source_html = "".join(sources) or (
        '<span class="atlas-book-fit-source">暂无可用来源</span>'
        if is_zh
        else '<span class="atlas-book-fit-source">No source link available</span>'
    )
    notes = list(dict.fromkeys([*assessment.reservations, *evaluation.warnings]))
    notes_html = ""
    if notes:
        notes_html = (
            f'<div class="atlas-book-fit-notes"><strong>{"注意事项" if is_zh else "Limitations"}</strong><br>'
            + "<br>".join(escape(item) for item in notes)
            + "</div>"
        )
    trace_html = "".join(
        f'<div class="atlas-book-fit-step"><span>{escape(item)}</span></div>'
        for item in evaluation.execution_trace
    )
    author = ", ".join(book.authors) or ("作者信息暂无" if is_zh else "Author unavailable")
    metadata = [author]
    if book.published_year:
        metadata.append(str(book.published_year))
    if book.language:
        metadata.append(book.language.upper())
    model_label = (
        "Amazon Bedrock 语义评估 + 透明评分规则"
        if is_zh
        else "Amazon Bedrock semantic review + transparent scoring rubric"
    ) if evaluation.used_live_model else (
        "透明评分规则（模型不可用）" if is_zh else "Transparent scoring rubric (model unavailable)"
    )
    role = role_labels.get(evaluation.evaluated_role, evaluation.evaluated_role)
    title_match = "书名匹配度" if is_zh else "Title match"
    role_separator = "：" if is_zh else ": "
    cover_html = book_cover_html(book, is_zh, "fit")
    is_recommended = (
        assessment.goal_relevance >= 0.3 and assessment.overall_rank_score >= 0.35
    )
    role_summary = (
        (
            "路径判断：<strong>不建议纳入当前学习路径</strong>"
            if is_zh
            else "Path decision: <strong>Not recommended for this learning path</strong>"
        )
        if not is_recommended
        else (
            f'{("最适合补充的知识类型" if is_zh else "Best role in this path")}{role_separator}'
            f'<strong>{escape(role)}</strong>'
        )
    )
    return (
        '<section class="atlas-book-fit" aria-labelledby="atlas-book-fit-title">'
        '<div class="atlas-book-fit-head"><div class="atlas-book-fit-identity">'
        f'{cover_html}<div class="atlas-book-fit-title-wrap">'
        f'<div class="atlas-book-fit-kicker">{_icon_svg("search")}{"Atlas 书籍评估" if is_zh else "Atlas book assessment"}</div>'
        f'<h2 id="atlas-book-fit-title">{escape(book.title)}</h2>'
        f'<p class="atlas-book-fit-meta">{escape(" · ".join(metadata))}</p></div></div>'
        f'<div class="atlas-book-fit-score" style="--fit-score:{score}" data-score="{score}%" '
        f'role="img" aria-label="{escape(("综合契合度" if is_zh else "Overall fit score") + f" {score}%", quote=True)}"></div></div>'
        '<div class="atlas-book-fit-body"><div>'
        f'<span class="atlas-book-fit-verdict">{escape(verdict)} · {score}%</span>'
        f'<p class="atlas-book-fit-copy">{escape(assessment.recommendation_reason)}</p>'
        f'<p class="atlas-book-fit-role">{role_summary} · {title_match} {evaluation.title_match_score:.0%}</p>'
        f'<div class="atlas-book-fit-source-row">{source_html}</div>'
        f'{notes_html}</div><div><div class="atlas-book-fit-scores">{dimension_html}</div>'
        f'<div class="atlas-book-fit-trace">{trace_html}</div></div></div>'
        '<div class="atlas-book-fit-foot">'
        f'<span>{escape(model_label)}</span>'
        f'<p class="atlas-book-fit-note">{"这些指标用于比较候选书，不是适合你的概率；阅读时间按选读范围估算，不代表读完整本书。" if is_zh else "These indicators compare candidates, not the probability of a good fit. Time estimates cover selected reading, not the entire book."}</p>'
        f'<a href="#book-search">{"评估另一本书" if is_zh else "Assess another book"}</a>'
        "</div></section>"
    )


def purchase_links_html(links: Sequence[tuple[str, str]], isbn: str | None) -> str:
    edition = f"ISBN {escape(isbn)}" if isbn else "购买前请核对版本"
    anchors = "".join(
        f'<a class="atlas-buy-link" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
        f'<span>{escape(platform)}</span><svg class="atlas-external-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">'
        '<path d="M7 5h8v8M15 5 6 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg></a>"
        for platform, url in links
    )
    return (
        '<section class="atlas-buy">'
        f'<div class="atlas-buy-head"><span class="atlas-buy-title">购买这本书</span><span class="atlas-buy-edition">{edition}</span></div>'
        f'<div class="atlas-buy-grid">{anchors}</div>'
        '<p class="atlas-buy-note">以下链接仅用于搜索正版书籍，不含返利。下单前请核对书名和 ISBN，并优先选择平台自营、出版社旗舰店或官方旗舰店。</p>'
        "</section>"
    )
