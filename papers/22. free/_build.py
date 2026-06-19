"""
FREE (ACL 2025 Findings) — single-file HTML builder.

Reads structured.json + translations/manual.json + analysis.json + tabs_data/*.json
+ config.json + assets/, emits a single self-contained HTML with v3 tokens and
3rd-gen interactions. All raster assets are base64-inlined. Tab 5 / 6 are shells.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / "assets"
TR = ROOT / "translations"
TD = ROOT / "tabs_data"

config   = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
struct   = json.loads((ROOT / "structured.json").read_text(encoding="utf-8"))
analysis = json.loads((ROOT / "analysis.json").read_text(encoding="utf-8"))
tr       = json.loads((TR / "manual.json").read_text(encoding="utf-8"))
diss     = json.loads((TD / "dissection.json").read_text(encoding="utf-8"))
know     = json.loads((TD / "knowledge.json").read_text(encoding="utf-8"))
ques     = json.loads((TD / "questions.json").read_text(encoding="utf-8"))

T = {s["sentence_id"]: s for s in tr["sentences"]}

asset_for_para = {}
for aid, pid, kind in config["asset_layout"]:
    asset_for_para.setdefault(pid, []).append((aid, kind))
WIDE = set(config["wide_assets"])
CAP  = config["captions"]

def b64img(name):
    p = ASSETS / name
    return f"data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"

ASSET_DATAURI = {n.stem: b64img(n.name) for n in ASSETS.glob("*.png") if not n.name.startswith("_")}

GEN_DIR = ASSETS / "generated"
GEN_DATAURI = {}
if GEN_DIR.exists():
    for n in GEN_DIR.glob("*.png"):
        raw = n.read_bytes()
        GEN_DATAURI[n.stem] = f"data:image/png;base64,{base64.b64encode(raw).decode()}"

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ----------------------------------------------------------------
# Tab 1 — sentence pairs + assets bound to paragraphs
# ----------------------------------------------------------------
HOTSPOTS = analysis.get("hotspots", {})
CALLOUTS = analysis.get("callouts", {})
INTERPS  = analysis.get("interpretations", {})
BEGINS   = analysis.get("beginner_notes", {})
QUIZZES  = analysis.get("quizzes", {})

def render_paragraph(p):
    pid = p["paragraph_id"]
    en_parts, kr_parts = [], []
    hot = set(HOTSPOTS.get(pid, []))
    for s in p["sentences"]:
        sid = s["sentence_id"]
        info = T.get(sid, {"original": s["text"], "translation": ""})
        cls = "sent hotspot" if sid in hot else "sent"
        en_parts.append(f'<span class="{cls}" data-pair="{sid}">{esc(info["original"])}</span>')
        kr_parts.append(f'<span class="{cls}" data-pair="{sid}">{info["translation"]}</span>')
    en_html = " ".join(en_parts)
    kr_html = " ".join(kr_parts)

    co_html = ""
    if pid in CALLOUTS:
        items = []
        for c in CALLOUTS[pid]:
            if isinstance(c, dict):
                c_type = c.get("variant", "key")
                c_text = c.get("text", "")
            else:
                c_type, c_text = c
            klass = "callout-key" if c_type == "key" else "callout-warn"
            items.append(f'<div class="callout {klass}"><p>{c_text}</p></div>')
        co_html = '<div class="callout-stack">' + "".join(items) + '</div>'

    sub = p.get("section_subtitle", "")
    sub_html = f'<p class="paragraph-subtitle">{esc(sub)}</p>' if sub else ""

    asset_html = ""
    for aid, kind in asset_for_para.get(pid, []):
        if aid not in ASSET_DATAURI: continue
        wide = " asset-wide" if aid in WIDE else ""
        cap = CAP.get(aid, "")
        interp = INTERPS.get(aid, "")
        beginner = BEGINS.get(aid, "")
        label = aid.replace("_", " ").upper()
        interp_html = f'<div class="interpretation"><h4>해석</h4><p>{interp}</p></div>' if interp else ""
        beginner_html = ""
        if beginner:
            beg_safe = esc(beginner).replace("\n", "<br>")
            beginner_html = (
                '<details class="beginner-note">'
                '<summary>초보자를 위한 설명</summary>'
                f'<div class="beginner-body">{beg_safe}</div>'
                '</details>'
            )
        fab_html = (
            f'<button class="study-fab" data-asset="{aid}" type="button">'
            '<span class="study-fab-glyph">?</span>학습 가이드</button>'
        )
        asset_html += (
            f'<figure class="asset-card{wide}" id="{aid}">'
            f'<div class="asset-image-wrap">'
            f'{fab_html}'
            f'<img src="{ASSET_DATAURI[aid]}" alt="{label}" />'
            '</div>'
            '<figcaption>'
            f'<span class="asset-label">{label}</span>'
            f'<p class="asset-cap">{esc(cap)}</p>'
            f'{interp_html}'
            f'{beginner_html}'
            '</figcaption>'
            '</figure>'
        )
    if asset_html:
        asset_html = f'<div class="asset-stack">{asset_html}</div>'

    return (
        f'<article class="paragraph-block" id="{pid}">'
        f'<span class="pid-tag">{pid}</span>'
        f'{sub_html}'
        '<div class="bilingual">'
        '<div class="col col-en"><div class="col-label">English</div>'
        f'<p class="english">{en_html}</p></div>'
        '<div class="col col-kr"><div class="col-label">한국어</div>'
        f'<p class="korean">{kr_html}</p></div>'
        '</div>'
        f'{co_html}'
        f'{asset_html}'
        '</article>'
    )

def render_section(sec):
    sid = sec["section_id"]
    paras_html = "\n".join(render_paragraph(p) for p in sec["paragraphs"])
    quiz_html = ""
    if sid in QUIZZES:
        items = []
        for q in QUIZZES[sid]:
            items.append(
                '<details class="recall-item">'
                f'<summary>{esc(q["q"])}</summary>'
                f'<div class="recall-answer"><p>{q["a"]}</p></div>'
                '</details>'
            )
        quiz_html = (
            '<aside class="recall-card">'
            '<span class="recall-tag">자가 점검</span>'
            '<h4>이 섹션 자가 점검</h4>'
            + "".join(items) + '</aside>'
        )
    return (
        f'<section class="section" id="{sid}">'
        '<div class="section-header">'
        f'<h2 class="section-title-en">{esc(sec["title"])}</h2>'
        '</div>'
        f'{paras_html}'
        f'{quiz_html}'
        '</section>'
    )

tab_reading = "\n".join(render_section(s) for s in struct["sections"])

# ----------------------------------------------------------------
# Tab 2 — Dissection 7+1
# ----------------------------------------------------------------
def render_diss_card(c):
    rows = "".join(
        f'<div class="diss-row"><dt class="diss-tag">{esc(r["tag"])}</dt>'
        f'<dd class="diss-body">{r["body"]}</dd></div>'
        for r in c["rows"]
    )
    overview_html = ""
    if c.get("cls") == "diss-summary" and "dissection_overview" in GEN_DATAURI:
        overview_html = (
            '<figure class="diss-overview-figure">'
            f'<img src="{GEN_DATAURI["dissection_overview"]}" alt="FREE 한 장 정리" />'
            '<figcaption>PROBLEM &rarr; KEY OBSERVATIONS &rarr; METHOD &rarr; WHAT&rsquo;S NEW &rarr; RESULTS &mdash; 5단 가로 흐름으로 본 FREE. 본문 9-row와 동일 내용의 시각 요약.</figcaption>'
            '</figure>'
        )
    return (
        f'<article class="diss-card {c["cls"]}">'
        f'<div class="diss-step">{c["id"]:02d}</div>'
        '<div class="diss-head">'
        f'<h3>{esc(c["title"])}</h3>'
        f'<p class="diss-lead">{esc(c["lead"])}</p>'
        '</div>'
        + overview_html
        + f'<dl class="diss-rows">{rows}</dl>'
        + '</article>'
    )

tab_dissection = (
    '<div class="tab-intro">'
    '<h2>Paper Dissection — 7+1 카드 분석</h2>'
    '<p>저자의 사고 흐름을 동기 → 관찰 → 비교 → 실행 → 검증 → 위험 → 확장 7단계로 분해하고, 마지막 카드에 한 장으로 압축한다.</p>'
    '</div>'
    '<div class="diss-grid">'
    + "".join(render_diss_card(c) for c in diss["cards"])
    + '</div>'
)

# ----------------------------------------------------------------
# Tab 3 — Knowledge: primer + fund cards + equations + concepts
# ----------------------------------------------------------------
primer = know["primer"]
fund_cards_html = "".join(
    f'<div class="fund-card">'
    f'<div class="fund-step">{i+1}</div>'
    f'<span class="fund-label-tag">{esc(fc.get("label",""))}</span>'
    f'<h4>{esc(fc["title"])}</h4>'
    f'<p class="fund-body">{fc["body"]}</p>'
    '</div>'
    for i, fc in enumerate(primer["fund_cards"])
)

eq_cards_html = ""
for eq in know["equations"]:
    eq_cards_html += (
        f'<div class="eq-card" id="{eq["eq_id"]}">'
        '<div class="eq-head">'
        f'<span class="eq-label">{esc(eq["label"])}</span>'
        '</div>'
        f'<div class="eq-display">$$ {eq["tex"]} $$</div>'
        '<div class="eq-meta">'
        f'<div class="eq-section"><h5>기호 의미</h5><p>{eq["where"]}</p></div>'
        f'<div class="eq-section"><h5>직관·연결</h5><p>{eq["intuition"]}</p></div>'
        '</div>'
        '</div>'
    )

concept_cards_html = "".join(
    '<div class="knw-card">'
    f'<span class="knw-label-tag">{esc(cc.get("label",""))}</span>'
    f'<h3>{esc(cc["title"])}</h3>'
    f'<div class="knw-body">{cc["body"]}</div>'
    '</div>'
    for cc in know["concept_cards"]
)

# Pipeline hero figure (generated) — FREE doesn't use a separate one
pipeline_hero_html = ""

tab_knowledge = (
    '<div class="tab-intro">'
    '<h2>Background &amp; 핵심 수식</h2>'
    '<p>FREE를 이해하기 위한 6개 핵심 빌딩 블록 + 6개 수식 + 7개 개념 카드. VLM/Early Exit/GAN/BLIP-2/KD/CapFilt → 그 위에 mid-crisis · ET · FC · EC = C_N 재사용의 본 논문 신개념.</p>'
    '</div>'
    '<section class="fund-panel">'
    f'<h3 class="panel-title">{esc(primer["title"])}</h3>'
    f'<p class="panel-sub">{esc(primer["caption"])}</p>'
    f'{pipeline_hero_html}'
    f'<div class="fund-grid">{fund_cards_html}</div>'
    '</section>'
    '<section class="eq-panel">'
    '<h3 class="panel-title">핵심 수식 6개</h3>'
    '<p class="panel-sub">Backbone CE loss / FC (discriminator) / Hard label CE / KL distillation / Inference confidence / Speedup 정의 — FREE의 정량 골격 여섯 줄.</p>'
    f'<div class="eq-grid eq-grid-detailed">{eq_cards_html}</div>'
    '</section>'
    '<section class="fund-panel">'
    '<h3 class="panel-title">개념 카드</h3>'
    '<p class="panel-sub">본 논문이 정립·도입한 7개 핵심 개념 — Mid-crisis · Overthinking · ET · FC · EC = C_N 재사용 · CapFilt · catastrophic forgetting의 GAN 변종.</p>'
    f'<div class="knw-grid">{concept_cards_html}</div>'
    '</section>'
)

# ----------------------------------------------------------------
# Tab 4 — Questions: q/a rows + diagrams
# ----------------------------------------------------------------
def render_q_card(c):
    rows = "".join(
        '<details class="recall-item">'
        f'<summary>{esc(r["q"])}</summary>'
        f'<div class="recall-answer"><p>{r["a"]}</p></div>'
        '</details>'
        for r in c["rows"]
    )
    return (
        f'<article class="coach-card {c["cls"]}">'
        f'<span class="coach-tag">{esc(c["title"])}</span>'
        f'<h3>{esc(c["lead"])}</h3>'
        f'<div class="q-rows">{rows}</div>'
        '</article>'
    )

# Diagrams above question cards
ques_diagrams_html = ""
for d in ques.get("diagrams", []):
    stem = Path(d["image_path"]).stem
    if stem in GEN_DATAURI:
        ques_diagrams_html += (
            '<figure class="concept-figure">'
            f'<img src="{GEN_DATAURI[stem]}" alt="{stem}" />'
            '<figcaption>'
            '<span class="cf-label">학습 보조 · 다이어그램</span>'
            f'<h4>{esc(d["title"])}</h4>'
            f'<p>{d["caption"]}</p>'
            '</figcaption>'
            '</figure>'
        )

tab_questions = (
    '<div class="tab-intro">'
    '<h2>Questions &amp; Diagrams</h2>'
    '<p>본문이 명시하지 않은 가정 · 흔한 오해 · 비판적 질문 · 확장 가능성을 4개 카드로 분해. Mid-crisis 검증 · ET 깊이 ablation 부재 · cosine 직접 비교 빈자리 · 자동 exit placement까지.</p>'
    '</div>'
    f'{ques_diagrams_html}'
    '<div class="coach-grid">'
    + "".join(render_q_card(c) for c in ques["cards"])
    + '</div>'
)

# ----------------------------------------------------------------
# Tab 5 / 6 — shells only
# ----------------------------------------------------------------
tab_simulator = (
    '<div class="tab-intro">'
    '<h2>Simulator &amp; Code</h2>'
    '<p>핵심 알고리즘 시뮬레이터·의사코드·코드 비교가 들어갈 자리입니다.</p>'
    '</div>'
    '<section class="section section-empty">'
    '<p class="section-empty-note">이 탭은 별도 요청 시 작성됩니다.</p>'
    '</section>'
)
tab_qa = (
    '<div class="tab-intro">'
    '<h2>학습 기초 Q &amp; A</h2>'
    '<p>자가 점검을 위한 카테고리별 Q&amp;A가 들어갈 자리입니다.</p>'
    '</div>'
    '<section class="section section-empty">'
    '<p class="section-empty-note">이 탭은 별도 요청 시 작성됩니다.</p>'
    '</section>'
)

# ----------------------------------------------------------------
# Page assembly — HEAD (style) + BODY (markup)
# ----------------------------------------------------------------
meta = config.get("metadata") or config.get("meta")
HEAD = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(meta["short_name"])}: {esc(meta["title"])}</title>
<script>
  MathJax = {{
    tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], processEscapes: true }},
    options: {{ skipHtmlTags: ['script','noscript','style','textarea','pre','code'] }}
  }};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
:root {{
  --bg: #fbfaff; --paper: #ffffff; --ink: #1f1d24; --muted: #7a7484; --line: #ece8f0;
  --accent: #8b75c0; --accent-soft: #e4d9ff; --accent-pale: #d2c2f5;
  --azure: #6b95b3; --azure-soft: #d9ebff; --azure-pale: #c0dcf5;
  --rose: #b87887;  --rose-soft: #ffdde6;
  --mint: #75ad8e; --mint-soft: #e3eee7;
  --amber: #ad8e4e; --amber-soft: #f3ead4;
  --hero-gradient: linear-gradient(135deg, #c0dcf5 0%, #d2c2f5 100%);
}}
*{{box-sizing:border-box}} html,body{{margin:0;padding:0}}
body{{font-family:"Pretendard Variable","Noto Sans KR","Segoe UI",Tahoma,sans-serif;background:var(--bg);color:var(--ink);line-height:1.72}}
.app{{max-width:1280px;margin:0 auto;padding:28px 26px 90px}}
.brand-tag{{display:inline-block;padding:5px 11px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-weight:700;font-size:12px;letter-spacing:0.06em;text-transform:uppercase}}
header.hero{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:28px 32px;box-shadow:0 12px 32px rgba(60,40,90,0.07);margin-bottom:22px;background-image:linear-gradient(180deg,#ffffff 60%,#fbf8ff 100%)}}
header.hero h1{{margin:12px 0 6px;font-family:Georgia,"Times New Roman",serif;font-size:30px;line-height:1.22;color:var(--ink)}}
header.hero .subtitle{{margin:0 0 14px;color:var(--muted)}}
header.hero .meta{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;font-size:13px;color:var(--muted)}}
header.hero .meta .meta-item strong{{display:block;color:var(--ink);font-size:11px;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:3px}}
nav.tabs{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;position:sticky;top:0;z-index:50;background:rgba(251,250,255,0.94);backdrop-filter:blur(6px);padding:10px 6px;border-radius:14px;border:1px solid var(--line)}}
.tab-btn{{flex:1 1 auto;min-width:170px;padding:10px 14px;border-radius:10px;border:1px solid transparent;background:transparent;font:inherit;font-weight:600;color:var(--muted);cursor:pointer}}
.tab-btn:hover{{color:var(--accent)}}
.tab-btn.active{{background:var(--paper);color:var(--accent);border-color:var(--line);box-shadow:0 4px 14px rgba(80,60,140,0.06)}}
.tab-pane{{display:none}} .tab-pane.active{{display:block}}
.tab-intro{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:18px 22px;margin-bottom:18px}}
.tab-intro h2{{margin:0 0 6px;font-family:Georgia,"Times New Roman",serif;color:var(--accent);font-size:22px}}
.tab-intro p{{margin:0;color:var(--muted);font-size:14px}}
.section{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:26px 28px 28px;margin-bottom:22px;box-shadow:0 8px 24px rgba(80,60,140,0.05)}}
.section.section-empty{{padding-bottom:16px}}
.section-header{{border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:18px}}
.section-title-en{{margin:0;font-family:Georgia,"Times New Roman",serif;font-size:22px;color:var(--accent)}}
.section-empty-note{{color:var(--muted);font-size:14px;font-style:italic}}
.paragraph-block{{position:relative;background:linear-gradient(180deg,#ffffff,#faf8ff);border:1px solid #ece8f0;border-radius:18px;padding:20px 22px 22px;margin-bottom:20px}}
.pid-tag{{position:absolute;top:-10px;left:18px;background:var(--accent);color:#fff;font-size:11px;font-weight:700;letter-spacing:0.08em;padding:4px 10px;border-radius:999px;text-transform:uppercase}}
.paragraph-subtitle{{margin:0 0 12px;font-family:Georgia,serif;font-style:italic;color:var(--accent);font-size:14px;font-weight:600}}
.bilingual{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.col{{background:rgba(255,255,255,0.85);border-radius:12px;padding:14px 16px}}
.col-en{{border-left:3px solid var(--accent)}} .col-kr{{border-left:3px solid var(--azure)}}
.col-label{{font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}}
.col p{{margin:0;font-size:15px;color:var(--ink)}}
.col p.english{{font-family:Georgia,"Times New Roman",serif}}
.col p.korean{{font-size:15.5px}}
.col p .sent{{display:inline;border-radius:4px;padding:0 2px;transition:background 130ms ease,box-shadow 130ms ease}}
.col p .sent.pair-active{{background:var(--amber-soft);box-shadow:0 0 0 1px var(--amber)}}
.col p .sent.hotspot{{background:#fff4d6;padding:1px 4px;border-left:4px solid var(--amber);margin-left:-4px;padding-left:8px;border-radius:4px}}
.col p .sent.hotspot.pair-active{{background:#ffe4a1;box-shadow:0 0 0 1px var(--amber)}}
.callout-stack{{margin-top:14px;display:grid;gap:10px}}
.callout{{position:relative;border-left:4px solid;padding:14px 16px 14px 20px;border-radius:10px;font-size:14.5px}}
.callout p{{margin:0}}
.callout::before{{display:inline-block;content:attr(data-label);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;padding:3px 9px;border-radius:999px;margin-right:10px;vertical-align:1px}}
.callout-key{{background:var(--amber-soft);border-color:var(--amber);color:#5a4716}}
.callout-key::before{{content:"★ 핵심 포인트";background:var(--amber);color:#fff}}
.callout-warn{{background:var(--rose-soft);border-color:var(--rose);color:#6c2c3a}}
.callout-warn::before{{content:"주의 / 흔한 오해";background:var(--rose);color:#fff}}
.asset-stack{{margin-top:18px;display:grid;gap:16px}}
.asset-card{{background:#ffffff;border:1px solid var(--line);border-radius:16px;padding:14px 16px 16px;margin:0;position:relative}}
.asset-card.asset-wide{{margin-left:-12px;margin-right:-12px}}
.asset-image-wrap{{position:relative;background:#fbfaff;border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;justify-content:center}}
.asset-image-wrap img{{max-width:100%;height:auto;display:block;cursor:zoom-in}}
.asset-card figcaption{{padding-top:12px}}
.asset-label{{display:inline-block;font-weight:700;font-size:12px;color:var(--accent);background:var(--accent-soft);padding:3px 10px;border-radius:999px;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:8px}}
.asset-cap{{font-size:14px;color:var(--ink);margin:4px 0 10px}}
.interpretation{{background:#f8f3ff;border:1px dashed var(--accent-pale);border-radius:12px;padding:12px 16px;margin-top:10px}}
.interpretation h4{{margin:0 0 6px;font-size:12px;letter-spacing:0.06em;text-transform:uppercase;color:var(--accent)}}
.interpretation p{{margin:0;font-size:14px;line-height:1.7;color:var(--ink)}}
details.beginner-note{{margin-top:10px;background:#f0f6ff;border:1px solid var(--azure-pale);border-radius:12px;padding:10px 14px}}
details.beginner-note > summary{{cursor:pointer;font-weight:700;color:var(--azure);font-size:13px;list-style:none}}
details.beginner-note > summary::-webkit-details-marker{{display:none}}
details.beginner-note > summary::before{{content:"▶";display:inline-block;margin-right:8px;transition:transform 0.15s ease;font-size:0.8em}}
details.beginner-note[open] > summary::before{{transform:rotate(90deg)}}
details.beginner-note .beginner-body{{margin-top:10px;font-size:13.5px;line-height:1.7}}
.recall-card{{background:var(--mint-soft);border:1px solid #b8d0c0;border-left:4px solid var(--mint);border-radius:14px;padding:18px 22px 14px;margin:22px 0 4px}}
.recall-tag{{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;background:var(--mint);color:#fff;padding:3px 10px;border-radius:999px}}
.recall-card h4{{margin:8px 0 4px;font-family:Georgia,serif;font-size:17px;color:#1f3d31}}
.recall-item{{background:#ffffff;border:1px solid #cfe0d4;border-radius:10px;padding:10px 14px;margin-top:10px}}
.recall-item summary{{cursor:pointer;font-weight:600;color:#1f3d31;list-style:none;font-size:14.5px}}
.recall-item summary::-webkit-details-marker{{display:none}}
.recall-item summary::before{{content:"▸";display:inline-block;margin-right:6px;color:var(--mint);transition:transform 150ms ease}}
.recall-item[open] summary::before{{transform:rotate(90deg)}}
.recall-answer{{margin-top:10px;padding:12px 14px;background:#f5fbf6;border-radius:8px;border-left:3px solid var(--mint)}}
.recall-answer p{{margin:0;font-size:14px;line-height:1.65}}
.ref-link{{color:var(--accent);text-decoration:underline dotted;text-decoration-thickness:1px;text-underline-offset:2px;cursor:pointer;font-weight:600}}
.ref-link:hover{{background:var(--accent-soft);border-radius:4px}}
@keyframes flash-target{{0%{{box-shadow:0 0 0 4px var(--accent)}}60%{{box-shadow:0 0 0 4px var(--accent-soft)}}100%{{box-shadow:0 0 0 0 transparent}}}}
.flash-target{{animation:flash-target 1.6s ease-out;border-radius:14px}}
.diss-grid{{display:grid;grid-template-columns:1fr;gap:18px}}
.diss-card{{position:relative;background:var(--paper);border:1px solid var(--line);border-left:5px solid var(--accent);border-radius:18px;padding:22px 24px 22px 78px;box-shadow:0 6px 20px rgba(80,60,140,0.05)}}
.diss-card.diss-motivation{{border-left-color:var(--accent)}}
.diss-card.diss-observe{{border-left-color:var(--mint)}}
.diss-card.diss-compare{{border-left-color:var(--amber)}}
.diss-card.diss-logic{{border-left-color:var(--azure)}}
.diss-card.diss-verify{{border-left-color:#7a5db5}}
.diss-card.diss-risk{{border-left-color:var(--rose)}}
.diss-card.diss-extend{{border-left-color:#3aa185}}
.diss-card.diss-summary{{border-left-color:#3d2a5e;grid-column:1/-1;background:linear-gradient(180deg,#ffffff,#f5edff)}}
.diss-overview-figure{{margin:18px 0 22px;padding:14px;background:#ffffff;border:1px solid var(--line);border-radius:14px;box-shadow:0 6px 18px rgba(80,60,140,0.06)}}
.diss-overview-figure img{{display:block;width:100%;height:auto;border-radius:10px;cursor:zoom-in}}
.diss-overview-figure figcaption{{margin-top:10px;font-size:13.5px;color:var(--muted);line-height:1.55;font-style:italic}}
.diss-step{{position:absolute;top:22px;left:22px;width:42px;height:42px;border-radius:12px;background:var(--accent-soft);color:var(--accent);font-family:Georgia,serif;font-weight:700;font-size:18px;display:flex;align-items:center;justify-content:center}}
.diss-card.diss-observe .diss-step{{background:var(--mint-soft);color:var(--mint)}}
.diss-card.diss-compare .diss-step{{background:var(--amber-soft);color:var(--amber)}}
.diss-card.diss-logic .diss-step{{background:var(--azure-soft);color:var(--azure)}}
.diss-card.diss-verify .diss-step{{background:#ece2f8;color:#7a5db5}}
.diss-card.diss-risk .diss-step{{background:var(--rose-soft);color:var(--rose)}}
.diss-card.diss-extend .diss-step{{background:#dceee8;color:#3aa185}}
.diss-card.diss-summary .diss-step{{background:#e4d9ff;color:#3d2a5e}}
.diss-head h3{{margin:0 0 4px;font-family:Georgia,serif;font-size:18px;color:var(--ink)}}
.diss-lead{{margin:0 0 14px;color:var(--muted);font-size:13.5px;font-style:italic}}
.diss-rows{{margin:0}}
.diss-row{{margin-top:12px;padding:12px 14px;background:rgba(251,250,255,0.7);border-radius:10px;display:flex;flex-direction:column;gap:8px;align-items:flex-start}}
.diss-tag{{align-self:start;justify-self:start;width:max-content;white-space:nowrap;line-height:1.4;display:inline-block;background:var(--accent);color:#fff;font-size:11px;font-weight:700;letter-spacing:0.05em;padding:3px 9px;border-radius:999px;margin-bottom:6px}}
.diss-card.diss-observe .diss-tag{{background:var(--mint)}}
.diss-card.diss-compare .diss-tag{{background:var(--amber)}}
.diss-card.diss-logic .diss-tag{{background:var(--azure)}}
.diss-card.diss-verify .diss-tag{{background:#7a5db5}}
.diss-card.diss-risk .diss-tag{{background:var(--rose)}}
.diss-card.diss-extend .diss-tag{{background:#3aa185}}
.diss-card.diss-summary .diss-tag{{background:#3d2a5e}}
.diss-body{{margin:0;font-size:14.5px;line-height:1.7;color:var(--ink)}}
.diss-rows dd.diss-body{{margin-left:0}}
.fund-panel,.eq-panel,.diagram-panel{{background:var(--paper);border:1px solid var(--line);border-radius:22px;padding:26px 28px;margin-bottom:22px;box-shadow:0 8px 24px rgba(80,60,140,0.05)}}
.panel-title{{margin:0 0 6px;font-family:Georgia,serif;color:var(--accent);font-size:22px}}
.panel-sub{{margin:0 0 16px;color:var(--muted);font-size:14px}}
.fund-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:22px}}
.fund-card{{position:relative;background:#fefcff;border:1px solid var(--line);border-left:4px solid var(--azure);border-radius:14px;padding:18px 20px 16px}}
.fund-card:nth-child(1){{border-left-color:var(--accent)}}
.fund-card:nth-child(2){{border-left-color:var(--amber)}}
.fund-card:nth-child(3){{border-left-color:var(--mint)}}
.fund-card:nth-child(4){{border-left-color:var(--azure)}}
.fund-card:nth-child(5){{border-left-color:var(--rose)}}
.fund-step{{position:absolute;top:14px;right:16px;font-family:Georgia,serif;font-size:26px;color:var(--muted);opacity:0.45}}
.fund-card h4{{margin:0 0 10px;font-family:Georgia,serif;font-size:17px;color:var(--ink);padding-right:36px}}
.fund-row{{margin-top:8px}}
.fund-label{{display:inline-block;font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;background:#f3eafe;color:var(--accent);padding:3px 9px;border-radius:999px;margin-bottom:4px}}
.fund-row p{{margin:2px 0 0;font-size:14px;line-height:1.65;color:var(--ink)}}
.fund-row.fund-intuition p{{color:#3a3742;font-style:italic}}
.fund-row.fund-link .fund-label{{background:var(--accent-soft);color:var(--accent)}}
.fund-row.fund-link p{{color:#1f1d24}}
.eq-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:4px}}
.eq-card{{background:linear-gradient(180deg,#fefcff,#f3edff);border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 6px 18px rgba(80,60,140,0.05)}}
.eq-head{{display:flex;align-items:center;gap:10px}}
.eq-label{{display:inline-block;background:var(--accent);color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:999px;letter-spacing:0.06em}}
.eq-head h4{{margin:0;font-family:Georgia,serif;font-size:17px;color:var(--ink)}}
.eq-display{{margin:14px 0 12px;background:#1f1814;color:#fff5dc;padding:18px 14px;border-radius:12px;font-size:18px;overflow-x:auto}}
.eq-display mjx-container{{color:#fff5dc !important}}
.eq-meta{{display:grid;gap:10px}}
.eq-section{{background:#fefcff;border-radius:10px;padding:10px 12px;border:1px solid #e8def8}}
.eq-section h5{{margin:0 0 4px;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:var(--accent)}}
.eq-section p{{margin:0;font-size:13.5px;color:var(--ink);line-height:1.65}}
.eq-grid-detailed{{grid-template-columns:1fr;gap:22px}}
.eq-grid-detailed .eq-display{{font-size:19px;padding:22px 16px}}
.knw-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}
.knw-card{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:22px 24px;box-shadow:0 6px 20px rgba(80,60,140,0.05)}}
.knw-card h3{{margin:0 0 14px;font-family:Georgia,serif;font-size:18px;color:var(--accent)}}
.knw-row{{margin-bottom:12px}}
.knw-row.knw-intuition{{background:#fdf6e8;border-radius:10px;padding:10px 12px}}
.knw-row.knw-link{{background:var(--mint-soft);border-radius:10px;padding:10px 12px}}
.knw-label{{display:inline-block;background:var(--mint-soft);color:var(--mint);font-weight:700;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;padding:3px 9px;border-radius:999px;margin-bottom:4px}}
.knw-row.knw-intuition .knw-label{{background:var(--amber-soft);color:var(--amber)}}
.knw-row.knw-link .knw-label{{background:var(--mint);color:#fff}}
.knw-row p{{margin:4px 0 0;font-size:14px}}
.coach-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}
.coach-card{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:22px 24px;box-shadow:0 6px 20px rgba(80,60,140,0.05);border-top:4px solid var(--accent)}}
.coach-card.q-hidden{{border-top-color:var(--accent)}}
.coach-card.q-myth{{border-top-color:var(--amber)}}
.coach-card.q-critic{{border-top-color:var(--rose)}}
.coach-card.q-extend{{border-top-color:var(--mint)}}
.coach-tag{{display:inline-block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;padding:3px 10px;border-radius:999px;margin-bottom:8px;background:var(--accent-soft);color:var(--accent)}}
.coach-card.q-myth .coach-tag{{background:var(--amber-soft);color:var(--amber)}}
.coach-card.q-critic .coach-tag{{background:var(--rose-soft);color:var(--rose)}}
.coach-card.q-extend .coach-tag{{background:var(--mint-soft);color:var(--mint)}}
.coach-card h3{{margin:0 0 12px;font-family:Georgia,serif;font-size:17px;color:var(--ink)}}
.q-rows{{display:grid;gap:8px}}
.q-rows .recall-item{{margin-top:0}}
.to-top{{position:fixed;bottom:26px;right:26px;width:48px;height:48px;border-radius:50%;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:22px;line-height:1;font-weight:700;box-shadow:0 8px 22px rgba(80,60,140,0.32);opacity:0;transform:translateY(8px);pointer-events:none;transition:opacity 220ms ease,transform 220ms ease,background 160ms ease;z-index:200}}
.to-top.visible{{opacity:1;transform:translateY(0);pointer-events:auto}}
.to-top:hover{{background:#6e54a3}}
.study-fab{{position:absolute;top:14px;right:14px;display:inline-flex;align-items:center;gap:6px;padding:7px 13px 7px 11px;border-radius:999px;background:rgba(139,117,192,0.94);color:#ffffff;border:1px solid rgba(255,255,255,0.4);font:inherit;font-size:12.5px;font-weight:700;letter-spacing:0.04em;cursor:pointer;box-shadow:0 6px 18px rgba(80,60,140,0.32);backdrop-filter:blur(2px);transition:transform 140ms ease,background 140ms ease;z-index:5}}
.study-fab:hover{{transform:translateY(-1px);background:var(--accent);box-shadow:0 10px 22px rgba(80,60,140,0.42)}}
.study-fab .study-fab-glyph{{display:inline-block;width:18px;height:18px;line-height:18px;border-radius:50%;background:#ffffff;color:var(--accent);font-size:12px;text-align:center;font-weight:800}}
.study-modal{{position:fixed;inset:0;z-index:300;display:none;align-items:flex-start;justify-content:center;background:rgba(31,29,36,0.55);padding:6vh 16px 24px;overflow-y:auto}}
.study-modal.open{{display:flex}}
.study-modal-card{{position:relative;width:100%;max-width:720px;background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:24px 28px 26px;box-shadow:0 24px 60px rgba(20,10,30,0.42);animation:study-pop 200ms ease-out}}
@keyframes study-pop{{0%{{opacity:0;transform:translateY(12px) scale(0.97)}}100%{{opacity:1;transform:translateY(0) scale(1)}}}}
.study-modal-head{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:12px;margin-bottom:14px;border-bottom:1px solid var(--line)}}
.study-modal-title{{margin:0;font-family:Georgia,serif;font-size:19px;color:var(--accent)}}
.study-modal-close{{border:1px solid var(--line);background:#ffffff;border-radius:50%;width:34px;height:34px;font-size:18px;line-height:1;color:var(--muted);cursor:pointer;flex-shrink:0}}
.study-modal-close:hover{{color:var(--accent);border-color:var(--accent)}}
.study-modal-body{{font-size:14px;line-height:1.7;color:var(--ink)}}
.study-modal-body .study-section{{margin-bottom:16px}} .study-modal-body .study-section:last-child{{margin-bottom:0}}
.study-modal-body .study-label{{display:inline-block;font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;margin:0 0 6px;padding:3px 10px;border-radius:999px}}
.study-modal-body .s-look .study-label{{background:var(--accent-soft);color:var(--accent)}}
.study-modal-body .s-num .study-label{{background:var(--amber-soft);color:var(--amber)}}
.study-modal-body .s-author .study-label{{background:var(--rose-soft);color:var(--rose)}}
.study-modal-body .s-check .study-label{{background:var(--mint-soft);color:var(--mint)}}
.study-modal-body .study-section p{{margin:4px 0 0}}
.study-modal-body .study-section ul{{margin:6px 0 0;padding-left:20px}}
.study-modal-body .study-section li{{margin-bottom:6px}}
.study-modal-body .study-section strong{{color:var(--accent)}}
.study-modal-body .study-num-row{{display:grid;grid-template-columns:minmax(160px,max-content) 1fr;gap:6px 14px;margin-top:8px;padding:10px 12px;background:#fbfaff;border:1px dashed var(--line);border-radius:10px;font-size:13.5px}}
.study-modal-body .study-num-row > b{{font-family:"Consolas","Courier New",monospace;color:var(--accent);font-weight:800}}
@media (max-width: 640px){{
  .study-modal-body .study-num-row{{grid-template-columns:1fr}}
}}
.concept-figure{{background:var(--paper);border:1px solid var(--line);border-radius:18px;padding:18px 20px;margin:0 0 22px;box-shadow:0 6px 18px rgba(80,60,140,0.05)}}
.concept-figure img{{display:block;max-width:760px;width:100%;height:auto;margin:0 auto;border-radius:12px;border:1px solid var(--line);background:#fbfaff;cursor:zoom-in}}
.concept-figure figcaption{{margin-top:12px;text-align:center}}
.concept-figure figcaption .cf-label{{display:inline-block;font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--accent);background:var(--accent-soft);padding:3px 10px;border-radius:999px;margin-bottom:6px}}
.concept-figure figcaption h4{{margin:4px 0 6px;font-family:Georgia,serif;font-size:17px;color:var(--ink)}}
.concept-figure figcaption p{{margin:0;font-size:13.5px;color:var(--muted);line-height:1.65;max-width:640px;margin-left:auto;margin-right:auto}}
footer.foot{{text-align:center;margin-top:40px;color:var(--muted);font-size:12.5px}}
@media print{{
  body{{background:white}}
  nav.tabs,.to-top,.study-fab,.study-modal{{display:none !important}}
  .tab-pane{{display:none !important}} .tab-pane.active{{display:block !important}}
  .paragraph-block,.diss-card,.knw-card,.eq-card,.coach-card,.fund-card,.concept-figure{{break-inside:avoid}}
  .sent.pair-active{{background:transparent;box-shadow:none}}
  canvas,svg{{break-inside:avoid}}
  .eq-display{{background:#f4eeff;color:#1f1814}} .eq-display mjx-container{{color:#1f1814 !important}}
}}
@media (max-width: 640px){{
  .app{{padding:16px 12px 60px}}
  nav.tabs{{flex-wrap:wrap}}
  .tab-btn{{flex:1 1 45%;font-size:13px;padding:8px 6px;min-width:0}}
  .bilingual{{grid-template-columns:1fr}}
  header.hero .meta{{grid-template-columns:1fr}}
  .knw-grid,.coach-grid,.fund-grid,.diss-grid,.eq-grid{{grid-template-columns:1fr}}
  table{{font-size:12px}}
  .tab-pane table{{overflow-x:auto;display:block}}
  svg{{max-width:100%;height:auto;overflow-x:auto}}
}}
.diagram-svg{{cursor:zoom-in}}
.img-lightbox{{position:fixed;inset:0;background:rgba(20,15,30,0.86);display:none;align-items:center;justify-content:center;z-index:2000;cursor:zoom-out;overflow:hidden}}
.img-lightbox.open{{display:flex}}
.img-lightbox-stage{{position:relative;width:96vw;height:96vh;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.img-lightbox img{{max-width:96vw;max-height:96vh;width:auto;height:auto;display:block;user-select:none;transform-origin:center center;transition:transform 0.18s ease;border-radius:6px;box-shadow:0 12px 48px rgba(0,0,0,0.5)}}
.img-lightbox.dragging img{{transition:none;cursor:grabbing}}
.img-lightbox-caption{{position:absolute;left:50%;bottom:18px;transform:translateX(-50%);max-width:80vw;padding:8px 16px;background:rgba(0,0,0,0.6);color:#fff;font-size:13px;border-radius:999px;text-align:center;pointer-events:none}}
.img-lightbox-close{{position:absolute;top:18px;right:24px;background:rgba(255,255,255,0.12);color:#fff;border:0;font-size:28px;width:42px;height:42px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center}}
.img-lightbox-close:hover{{background:rgba(255,255,255,0.22)}}
.img-lightbox-hint{{position:absolute;top:18px;left:24px;color:rgba(255,255,255,0.7);font-size:12px;background:rgba(0,0,0,0.4);padding:6px 12px;border-radius:999px;pointer-events:none}}
@media print {{.img-lightbox,.study-modal,.to-top{{display:none !important}}}}
</style>
</head>
'''

JS = r'''
<script>
(function(){
  const buttons = document.querySelectorAll('.tab-btn');
  const panes = document.querySelectorAll('.tab-pane');
  const scrollMem = {};
  function activate(tab){
    if (document.querySelector('.tab-pane.active')){
      const cur = document.querySelector('.tab-pane.active').id;
      scrollMem[cur] = window.scrollY;
    }
    buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
    panes.forEach(p => p.classList.toggle('active', p.id === tab));
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise().catch(()=>{});
    }
    window.scrollTo({top: scrollMem[tab] || 0, behavior: 'instant'});
  }
  buttons.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));

  document.querySelectorAll('.sent[data-pair]').forEach(el => {
    el.addEventListener('mouseenter', () => {
      const pid = el.dataset.pair;
      document.querySelectorAll('.sent[data-pair="'+pid+'"]').forEach(s => s.classList.add('pair-active'));
    });
    el.addEventListener('mouseleave', () => {
      const pid = el.dataset.pair;
      document.querySelectorAll('.sent[data-pair="'+pid+'"]').forEach(s => s.classList.remove('pair-active'));
    });
  });

  function autoLink(){
    const targetTabFor = (kind) => kind === 'Eq' ? 'tab-knowledge' : 'tab-reading';
    const re = /\b(Eq\.?|Equation|Fig\.?|Figure|Table)\s*(\d+)/g;
    document.querySelectorAll('.tab-pane .col p, .diss-body, .knw-card p, .coach-card li, .coach-card .recall-answer p, .fund-row p, .eq-section p').forEach(p => {
      const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      const texts = [];
      while(walker.nextNode()) texts.push(walker.currentNode);
      texts.forEach(node => {
        if (node.parentNode.tagName === 'A') return;
        const txt = node.nodeValue;
        if (!re.test(txt)) return;
        re.lastIndex = 0;
        const frag = document.createDocumentFragment();
        let last = 0, m;
        while((m = re.exec(txt)) !== null){
          frag.appendChild(document.createTextNode(txt.slice(last, m.index)));
          const a = document.createElement('a');
          a.className = 'ref-link';
          const kind = m[1].startsWith('Eq') || m[1].startsWith('Equation') ? 'Eq' : (m[1].startsWith('T') ? 'Table' : 'Fig');
          a.dataset.targetTab = targetTabFor(kind);
          if (kind === 'Fig') a.dataset.targetId = 'fig_' + m[2];
          else if (kind === 'Table') a.dataset.targetId = 'table_' + m[2];
          else a.dataset.targetId = '';
          a.textContent = m[0];
          a.addEventListener('click', (e) => {
            e.preventDefault();
            activate(a.dataset.targetTab);
            const id = a.dataset.targetId;
            if (id){
              const el = document.getElementById(id);
              if (el){
                setTimeout(()=>{
                  el.scrollIntoView({behavior:'smooth', block:'center'});
                  el.classList.add('flash-target');
                  setTimeout(()=>el.classList.remove('flash-target'), 1700);
                }, 50);
              }
            }
          });
          frag.appendChild(a);
          last = m.index + m[0].length;
        }
        frag.appendChild(document.createTextNode(txt.slice(last)));
        node.parentNode.replaceChild(frag, node);
      });
    });
  }
  autoLink();

  const toTop = document.createElement('button');
  toTop.className = 'to-top';
  toTop.setAttribute('aria-label', '맨 위로');
  toTop.textContent = '↑';
  document.body.appendChild(toTop);
  window.addEventListener('scroll', () => {
    toTop.classList.toggle('visible', window.scrollY > 360);
  });
  toTop.addEventListener('click', () => {
    const cur = document.querySelector('.tab-pane.active');
    if (cur) scrollMem[cur.id] = 0;
    window.scrollTo({top: 0, behavior: 'smooth'});
  });

  const modal = document.createElement('div');
  modal.className = 'study-modal';
  modal.innerHTML =
    '<div class="study-modal-card">' +
      '<div class="study-modal-head">' +
        '<div><span class="study-label">학습 가이드</span><h3 class="study-modal-title"></h3></div>' +
        '<button class="study-modal-close" aria-label="닫기">×</button>' +
      '</div>' +
      '<div class="study-modal-body"></div>' +
    '</div>';
  document.body.appendChild(modal);
  const modalTitle = modal.querySelector('.study-modal-title');
  const modalBody = modal.querySelector('.study-modal-body');
  modal.querySelector('.study-modal-close').addEventListener('click', () => modal.classList.remove('open'));
  modal.addEventListener('click', e => { if(e.target === modal) modal.classList.remove('open'); });

  const STUDY = STUDY_GUIDES_PLACEHOLDER;
  document.querySelectorAll('.study-fab').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const aid = btn.dataset.asset;
      const data = STUDY[aid] || {title:'학습 가이드', html:'<p>이 자산에 대한 가이드는 곧 추가됩니다.</p>'};
      modalTitle.textContent = data.title;
      modalBody.innerHTML = data.html;
      modal.classList.add('open');
      if (window.MathJax && window.MathJax.typesetPromise) window.MathJax.typesetPromise([modalBody]).catch(()=>{});
    });
  });

  // Image Lightbox — proportional zoom + drag pan + ESC/click close.
  const lb = document.querySelector('.img-lightbox');
  if (lb) {
    const lbImg = lb.querySelector('img');
    const lbCap = lb.querySelector('.img-lightbox-caption');
    const lbClose = lb.querySelector('.img-lightbox-close');
    let scale = 1, tx = 0, ty = 0, dragging = false, sx = 0, sy = 0;
    function apply(){ lbImg.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')'; }
    function reset(){ scale = 1; tx = 0; ty = 0; apply(); }
    function lbOpen(src, alt){
      lbImg.src = src;
      lbCap.textContent = alt || '';
      reset();
      lb.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
    function lbCloseFn(){
      lb.classList.remove('open');
      document.body.style.overflow = '';
    }
    lbClose.addEventListener('click', (e) => { e.stopPropagation(); lbCloseFn(); });
    lb.addEventListener('click', (e) => { if (e.target === lb || e.target.classList.contains('img-lightbox-stage')) lbCloseFn(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && lb.classList.contains('open')) lbCloseFn(); });
    lb.addEventListener('wheel', (e) => {
      if (!lb.classList.contains('open')) return;
      e.preventDefault();
      const delta = -e.deltaY * 0.0015;
      const next = Math.max(0.3, Math.min(8, scale * (1 + delta)));
      scale = next;
      apply();
    }, {passive:false});
    lbImg.addEventListener('mousedown', (e) => {
      if (scale <= 1) return;
      e.preventDefault();
      dragging = true;
      sx = e.clientX - tx;
      sy = e.clientY - ty;
      lb.classList.add('dragging');
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      tx = e.clientX - sx;
      ty = e.clientY - sy;
      apply();
    });
    window.addEventListener('mouseup', () => {
      if (!dragging) return;
      dragging = false;
      lb.classList.remove('dragging');
    });
    lbImg.addEventListener('dblclick', () => reset());
    document.querySelectorAll('.asset-image-wrap img, .concept-figure img, .diss-overview-figure img, .diagram-svg').forEach(img => {
      img.addEventListener('click', (e) => {
        if (img.closest('.img-lightbox')) return;
        e.preventDefault();
        const src = img.tagName === 'IMG' ? img.src : (img.dataset.src || '');
        const alt = img.alt || img.getAttribute('aria-label') || '';
        if (src) lbOpen(src, alt);
      });
    });
  }
})();
</script>
'''

# Per-asset study guides — 4-section canonical pattern
# (SGL §12 component_rules.md: s-look / s-num / s-author / s-check)
STUDY_MODALS = analysis.get("study_modals", {})

def _render_study_html(sm: dict) -> str:
    rows = []
    for item in sm.get("nums", []):
        if isinstance(item, dict):
            lbl = item.get("label", "")
            val = item.get("value", "")
            note = item.get("note", "")
            note_html = f' <em>{esc(note)}</em>' if note else ""
            rows.append(f'<div class="study-num-row"><b>{esc(lbl)}</b><span>{esc(val)}{note_html}</span></div>')
        else:
            lbl, val = item[0], item[1]
            rows.append(f'<div class="study-num-row"><b>{esc(lbl)}</b><span>{esc(val)}</span></div>')
    nums_html = "".join(rows)
    check_html = "".join(f"<li>{c}</li>" for c in sm.get("check", []))
    return (
        '<div class="study-section s-look">'
        '<span class="study-label">▸ 어디를 먼저 볼까</span>'
        f'<p>{sm.get("look", "")}</p>'
        '</div>'
        '<div class="study-section s-num">'
        '<span class="study-label">▸ 결정적 숫자</span>'
        f'{nums_html}'
        '</div>'
        '<div class="study-section s-author">'
        '<span class="study-label">▸ 저자가 말하는 것</span>'
        f'<p>{sm.get("author", "")}</p>'
        '</div>'
        '<div class="study-section s-check">'
        '<span class="study-label">▸ 학습 체크포인트</span>'
        f'<ul>{check_html}</ul>'
        '</div>'
    )

study = {}
for aid in ASSET_DATAURI:
    label = aid.replace("_", " ").upper()
    sm = STUDY_MODALS.get(aid)
    if sm:
        study[aid] = {"title": sm.get("title", f"학습 가이드 — {label}"),
                       "html": _render_study_html(sm)}
    else:
        study[aid] = {"title": f"학습 가이드 — {label}",
                       "html": '<div class="study-section s-look"><span class="study-label">▸ 준비 중</span><p>이 자산의 학습 가이드는 곧 추가됩니다.</p></div>'}

study_json = json.dumps(study, ensure_ascii=False)
JS_FINAL = JS.replace("STUDY_GUIDES_PLACEHOLDER", study_json)

BODY = f'''<body>
<main class="app">
  <header class="hero">
    <span class="brand-tag">Paper Review · v3</span>
    <h1>{esc(meta["title"])}</h1>
    <p class="subtitle">{esc(meta["short_name"])} — {esc(meta["venue"])} ({meta["year"]})</p>
    <div class="meta">
      <span class="meta-item"><strong>Authors</strong>{esc(meta["authors"])}</span>
      <span class="meta-item"><strong>Affiliation</strong>{esc(meta["affiliation"])}</span>
      <span class="meta-item"><strong>Source</strong>{esc(meta["source_pdf"])}</span>
    </div>
  </header>
  <nav class="tabs" role="tablist">
    <button class="tab-btn active" data-tab="tab-reading">① 원문 / 번역</button>
    <button class="tab-btn" data-tab="tab-dissection">② Paper Dissection</button>
    <button class="tab-btn" data-tab="tab-knowledge">③ Background &amp; 핵심 수식</button>
    <button class="tab-btn" data-tab="tab-questions">④ Questions &amp; Diagrams</button>
    <button class="tab-btn" data-tab="tab-simulator">⑤ Simulator &amp; Code</button>
    <button class="tab-btn" data-tab="tab-qa">⑥ 학습 기초 Q &amp; A</button>
  </nav>
  <section id="tab-reading" class="tab-pane active">
    <div class="tab-intro">
      <h2>원문 ↔ 번역 정렬 뷰</h2>
      <p>문장 단위 hover로 원문과 번역이 짝을 이룬다. 도표 아래 해석/초보자 토글, 섹션 끝의 자가 점검 카드가 함께 묶여 있다.</p>
    </div>
{tab_reading}
  </section>
  <section id="tab-dissection" class="tab-pane">
{tab_dissection}
  </section>
  <section id="tab-knowledge" class="tab-pane">
{tab_knowledge}
  </section>
  <section id="tab-questions" class="tab-pane">
{tab_questions}
  </section>
  <section id="tab-simulator" class="tab-pane">
{tab_simulator}
  </section>
  <section id="tab-qa" class="tab-pane">
{tab_qa}
  </section>
  <footer class="foot">
    <p>Paper Review HTML · v3 · ACL 2025 FREE — VLM에 GAN-style Early Exit를 심다</p>
  </footer>
</main>
<div class="img-lightbox" role="dialog" aria-label="이미지 확대보기" aria-hidden="true">
  <div class="img-lightbox-hint">휠: 확대/축소 · 드래그: 이동 · 더블클릭: 원본 · ESC: 닫기</div>
  <button class="img-lightbox-close" type="button" aria-label="닫기">×</button>
  <div class="img-lightbox-stage"><img src="" alt="" /></div>
  <div class="img-lightbox-caption"></div>
</div>
{JS_FINAL}
</body>
</html>
'''

OUT_HTML = ROOT / "FREE_output.html"
OUT_HTML.write_text(HEAD + BODY, encoding="utf-8")
size_mb = OUT_HTML.stat().st_size / (1024*1024)
print(f"=== FREE_output.html built: {size_mb:.2f} MB ===")
print(f"  asset images embedded: {len(ASSET_DATAURI)}")
print(f"  generated images embedded: {len(GEN_DATAURI)}")
