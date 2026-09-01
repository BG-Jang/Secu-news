#!/usr/bin/env python3
"""
일자별 보안 다이제스트 HTML들을 하나의 '아카이브 허브' HTML로 합칩니다.

사용법:
    python3 build_hub.py issues/ -o dist/index.html            # 단독 실행용 완전한 HTML
    python3 build_hub.py issues/ -o dist/artifact.html --body  # 아티팩트 게시용(뼈대 태그 제외)

issues/ 폴더에 기존 일자별 파일을 그대로 떨궈두기만 하면 됩니다.
파일명이나 <title>에서 날짜(YYYYMMDD 또는 YYYY.MM.DD)를 자동으로 읽습니다.
"""
import argparse
import hashlib
import html as html_mod
import json
import re
import sys
from datetime import date
from pathlib import Path

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def find_date(text: str):
    m = re.search(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if not m:
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", text)
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return html_mod.unescape(s).strip()


def parse_issue(path: Path):
    raw = path.read_text(encoding="utf-8", errors="replace")

    title_tag = re.search(r"<title>(.*?)</title>", raw, re.S)
    title_text = strip_tags(title_tag.group(1)) if title_tag else ""

    d = find_date(path.name) or find_date(title_text) or find_date(raw[:4000])
    if d is None:
        print(f"  ! 날짜를 못 찾아 건너뜁니다: {path.name}", file=sys.stderr)
        return None

    style = re.search(r"<style[^>]*>(.*?)</style>", raw, re.S)
    css = style.group(1).strip() if style else ""

    slides = re.findall(r'<section class="slide.*?</section>', raw, re.S)
    if not slides:
        print(f"  ! 슬라이드를 못 찾아 건너뜁니다: {path.name}", file=sys.stderr)
        return None

    first = slides[0]
    foot = re.search(r'<div class="title-foot">(.*?)</div>', first, re.S)
    sub = re.search(r'<div class="title-date">(.*?)</div>', first, re.S)
    metas = re.findall(
        r'<div class="n">(.*?)</div>\s*<div class="l">(.*?)</div>', first, re.S
    )

    return {
        "date": d.isoformat(),
        "dow": WEEKDAY_KO[d.weekday()],
        "sub": strip_tags(sub.group(1)) if sub else "",
        "foot": strip_tags(foot.group(1)) if foot else "",
        "meta": [{"n": strip_tags(a), "l": strip_tags(b)} for a, b in metas][:3],
        "slides": slides,
        "_css": css,
        "_file": path.name,
    }


def build(issue_dir: Path, body_only: bool) -> str:
    files = sorted(
        p for p in issue_dir.iterdir()
        if p.suffix.lower() in (".html", ".htm") and p.is_file()
    )
    days = []
    for p in files:
        parsed = parse_issue(p)
        if parsed:
            days.append(parsed)
            print(f"  + {parsed['date']}  슬라이드 {len(parsed['slides'])}장  ({p.name})")

    if not days:
        sys.exit("issues 폴더에서 읽을 수 있는 파일이 없습니다.")

    # 같은 날짜가 여러 번 있으면 마지막 것만 사용
    dedup = {}
    for day in days:
        dedup[day["date"]] = day
    days = sorted(dedup.values(), key=lambda x: x["date"], reverse=True)

    # 날짜별 CSS는 대부분 동일하므로 해시로 풀링해 파일 크기를 줄임
    pool, order = {}, []
    for day in days:
        h = hashlib.sha1(day["_css"].encode()).hexdigest()[:8]
        if h not in pool:
            pool[h] = day["_css"]
            order.append(h)
        day["css"] = h
        del day["_css"]

    data = json.dumps(days, ensure_ascii=False, separators=(",", ":"))
    css_pool = json.dumps(pool, ensure_ascii=False, separators=(",", ":"))

    page = TEMPLATE.replace("/*__DAYS__*/[]", data).replace("/*__CSSPOOL__*/{}", css_pool)
    page = page.replace("__COUNT__", str(len(days)))
    page = page.replace("__LATEST__", days[0]["date"].replace("-", "."))

    if body_only:
        return page
    return (
        "<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0, "
        "maximum-scale=1.0, user-scalable=no, viewport-fit=cover\">\n"
        "</head>\n<body>\n" + page + "\n</body>\n</html>\n"
    )


TEMPLATE = r"""<title>보안 다이제스트 아카이브</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=JetBrains+Mono:wght@400;700&family=Noto+Sans+KR:wght@400;500;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --paper:oklch(98% 0.012 45);--paper-3:oklch(92% 0.016 45);
  --ink:oklch(18% 0.012 45);--ink-2:oklch(32% 0.014 45);--ink-3:oklch(48% 0.012 45);
  --accent:oklch(42% 0.20 25);--rule:oklch(84% 0.010 45);
  --void:#14151a;
  color-scheme:light;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;background:var(--void);
  font-family:'Noto Sans KR','Inter',system-ui,-apple-system,sans-serif;
  -webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent}
body{overflow:hidden}
body.mode-index{overflow:auto;-webkit-overflow-scrolling:touch;background:var(--paper)}

/* ---------- 아카이브 인덱스 ---------- */
#index{display:none;max-width:560px;margin:0 auto;padding:34px 22px 56px;
  background:var(--paper);color:var(--ink);min-height:100%}
body.mode-index #index{display:block}
.ix-tag{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.ix-title{font-family:'Oswald','Noto Sans KR',sans-serif;font-weight:700;
  font-size:40px;line-height:1.08;letter-spacing:-.01em;margin-top:12px}
.ix-sub{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.1em;
  color:var(--ink-3);margin-top:12px}
.ix-rule{border:none;border-top:3px solid var(--ink);position:relative;margin:20px 0 0}
.ix-rule::after{content:"";position:absolute;top:4px;left:0;right:0;border-top:1px solid var(--ink)}

.ix-search{width:100%;margin-top:22px;padding:12px 14px;border:1.5px solid var(--rule);
  background:#fff;font-size:15px;font-family:inherit;color:var(--ink);border-radius:0}
.ix-search:focus{outline:none;border-color:var(--ink)}
.ix-search::placeholder{color:var(--ink-3)}

.ix-month{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  letter-spacing:.16em;color:var(--ink-3);margin:30px 0 10px;
  padding-bottom:6px;border-bottom:1px solid var(--rule)}

.card{display:flex;gap:16px;align-items:flex-start;width:100%;text-align:left;
  background:none;border:none;border-bottom:1px solid var(--rule);
  padding:16px 2px;cursor:pointer;font:inherit;color:inherit}
.card:active{background:var(--paper-3)}
.card-d{flex:0 0 62px}
.card-dd{font-family:'Oswald','Noto Sans KR',sans-serif;font-size:30px;font-weight:700;
  line-height:1;letter-spacing:-.02em}
.card-dow{font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:.12em;
  color:var(--ink-3);margin-top:5px}
.card-body{flex:1;min-width:0}
.card-h{font-size:14px;font-weight:700;line-height:1.45;color:var(--ink)}
.card-sub{font-size:12.5px;line-height:1.5;color:var(--ink-2);margin-top:5px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-meta{display:flex;flex-wrap:wrap;gap:6px;margin-top:9px}
.chip{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
  letter-spacing:.06em;padding:3px 7px;border:1px solid var(--rule);color:var(--ink-3)}
.card-go{flex:0 0 auto;align-self:center;color:var(--ink-3);font-size:18px}
.ix-empty{padding:40px 0;text-align:center;color:var(--ink-3);font-size:14px}
.ix-foot{margin-top:36px;padding-top:16px;border-top:1px solid var(--rule);
  font-size:11.5px;line-height:1.7;color:var(--ink-3)}

/* ---------- 덱 뷰어 ---------- */
#deck{display:none;position:fixed;inset:0;overflow:hidden;background:var(--void)}
body.mode-deck #deck{display:block}
.slide{position:absolute;left:50%;top:50%;width:430px;height:932px;
  transform:translate(-50%,-50%) scale(var(--mb-scale,1));transform-origin:center center;
  opacity:0;pointer-events:none;transition:opacity .32s ease}
.slide.is-active{opacity:1;pointer-events:auto}
.notes{display:none}
/* 원본 파일에 정의가 빠져 있던 트렌드 카드 스타일 보강 */
.trend-card{margin-top:16px;padding-left:14px;border-left:3px solid var(--accent)}
.trend-kicker{font-size:14.5px;font-weight:700;line-height:1.4;color:var(--ink)}
.trend-body{font-size:12.8px;line-height:1.55;color:var(--ink-2);margin-top:5px}

.pbar{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);
  z-index:42;transition:width .3s ease}
.navzone{position:fixed;top:0;bottom:52px;width:22%;z-index:38;cursor:pointer}
.navzone.l{left:0}.navzone.r{right:0}
.botbar{position:fixed;left:0;right:0;bottom:0;height:52px;z-index:41;
  display:flex;align-items:center;justify-content:space-between;padding:0 10px;
  background:linear-gradient(to top,rgba(20,21,26,.92),rgba(20,21,26,0))}
.back{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,.92);
  border:none;padding:8px 14px 8px 11px;font:inherit;font-size:13px;font-weight:700;
  color:var(--ink);cursor:pointer;border-radius:999px;box-shadow:0 1px 6px rgba(0,0,0,.28)}
.daylabel{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;
  letter-spacing:.12em;color:rgba(255,255,255,.6);padding-right:4px}
.counter{position:absolute;left:0;right:0;text-align:center;pointer-events:none;
  font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;
  color:rgba(255,255,255,.72);transition:opacity .4s ease}
</style>

<div id="index">
  <div class="ix-tag">24시간 보안 뉴스 다이제스트</div>
  <h1 class="ix-title">아카이브</h1>
  <div class="ix-sub">__COUNT__개 호 · 최신 __LATEST__</div>
  <hr class="ix-rule">
  <input id="q" class="ix-search" type="search" placeholder="날짜, CVE, 키워드로 찾기" autocomplete="off">
  <div id="list"></div>
  <div class="ix-foot">
    날짜를 누르면 그날의 슬라이드 덱이 열립니다. 덱 안에서는 좌우로 밀거나 화면 가장자리를 눌러 이동합니다.<br>
    이 페이지 주소 하나만 공유하면 되며, 새 호가 올라오면 같은 주소가 갱신됩니다.
  </div>
</div>

<div id="deck">
  <div class="pbar" id="pbar"></div>
  <div class="navzone l" data-dir="-1"></div>
  <div class="navzone r" data-dir="1"></div>
  <div class="botbar">
    <button class="back" id="back">← 목록</button>
    <div class="counter" id="counter"></div>
    <div class="daylabel" id="daylabel"></div>
  </div>
  <style id="daycss"></style>
</div>

<script>
(function(){
'use strict';
var DAYS = /*__DAYS__*/[];
var CSSPOOL = /*__CSSPOOL__*/{};
var MONTH_KO = ['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'];

var body = document.body;
var listEl = document.getElementById('list');
var qEl = document.getElementById('q');
var deckEl = document.getElementById('deck');
var dayCss = document.getElementById('daycss');
var pbar = document.getElementById('pbar');
var counter = document.getElementById('counter');
var dayLabel = document.getElementById('daylabel');

/* ---------- 인덱스 ---------- */
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}

function renderList(filter){
  var f = (filter||'').trim().toLowerCase();
  var shown = DAYS.filter(function(d){
    if(!f) return true;
    var hay = (d.date+' '+d.dow+' '+d.sub+' '+d.foot+' '+d.slides.join(' ')).toLowerCase();
    return hay.indexOf(f) !== -1;
  });
  if(!shown.length){ listEl.innerHTML = '<div class="ix-empty">일치하는 호가 없습니다.</div>'; return; }
  var out = [], lastMonth = '';
  shown.forEach(function(d){
    var p = d.date.split('-');
    var mk = p[0]+'-'+p[1];
    if(mk !== lastMonth){
      lastMonth = mk;
      out.push('<div class="ix-month">'+p[0]+' '+MONTH_KO[parseInt(p[1],10)-1]+'</div>');
    }
    var chips = (d.meta||[]).map(function(m){
      return '<span class="chip">'+esc(m.n)+' '+esc(m.l)+'</span>';
    }).join('');
    out.push(
      '<button class="card" data-date="'+d.date+'">'+
        '<div class="card-d"><div class="card-dd">'+p[1]+'.'+p[2]+'</div>'+
          '<div class="card-dow">'+esc(d.dow)+'요일</div></div>'+
        '<div class="card-body">'+
          '<div class="card-h">'+esc(d.sub||'보안 뉴스 다이제스트')+'</div>'+
          '<div class="card-sub">'+esc(d.foot)+'</div>'+
          (chips ? '<div class="card-meta">'+chips+'</div>' : '')+
        '</div>'+
        '<div class="card-go">›</div>'+
      '</button>');
  });
  listEl.innerHTML = out.join('');
}

listEl.addEventListener('click', function(e){
  var c = e.target.closest ? e.target.closest('.card') : null;
  if(c) location.hash = '#/'+c.dataset.date+'/1';
});
qEl.addEventListener('input', function(){ renderList(qEl.value) });

/* ---------- 덱 ---------- */
var W=430, H=932, cur=null, idx=0, slideEls=[], hinted=false;

function fit(){
  var vw = window.innerWidth||390, vh = window.innerHeight||844;
  deckEl.style.setProperty('--mb-scale', Math.min(vw/W, vh/H).toFixed(4));
}
window.addEventListener('resize', fit);
window.addEventListener('orientationchange', function(){ setTimeout(fit,200) });

function openDay(dateStr, n){
  var d = null;
  for(var i=0;i<DAYS.length;i++){ if(DAYS[i].date===dateStr){ d=DAYS[i]; break } }
  if(!d) return showIndex();

  if(cur !== dateStr){
    cur = dateStr;
    dayCss.textContent = CSSPOOL[d.css] || '';
    slideEls.forEach(function(el){ el.remove() });
    slideEls = [];
    var frag = document.createElement('div');
    frag.innerHTML = d.slides.join('');
    Array.prototype.slice.call(frag.children).forEach(function(el){
      deckEl.appendChild(el);
      slideEls.push(el);
    });
    dayLabel.textContent = dateStr.replace(/-/g,'.');
  }
  body.className = 'mode-deck';
  fit();
  show(n-1);
  if(!hinted){
    hinted = true;
    counter.textContent = '← 스와이프 →';
    setTimeout(function(){ show(idx) }, 2600);
  }
}

function show(i){
  if(!slideEls.length) return;
  i = Math.max(0, Math.min(slideEls.length-1, i));
  idx = i;
  slideEls.forEach(function(el,k){ el.classList.toggle('is-active', k===i) });
  pbar.style.width = ((i+1)/slideEls.length*100)+'%';
  counter.textContent = (i+1)+' / '+slideEls.length;
}

function go(delta){
  var next = idx + delta;
  if(next < 0 || next >= slideEls.length) return;
  setHash('#/'+cur+'/'+(next+1));
  show(next);
}

function showIndex(){
  cur = null;
  slideEls.forEach(function(el){ el.remove() });
  slideEls = [];
  dayCss.textContent = '';
  body.className = 'mode-index';
  window.scrollTo(0,0);
}

var suppress = false;
function setHash(h){
  if(location.hash === h) return;
  suppress = true;
  try{ history.replaceState(null,'',h) }catch(e){ location.hash = h }
  setTimeout(function(){ suppress = false }, 0);
}

document.getElementById('back').addEventListener('click', function(){
  suppress = true;
  try{ history.replaceState(null,'','#/') }catch(e){}
  setTimeout(function(){ suppress=false }, 0);
  showIndex();
});

Array.prototype.slice.call(document.querySelectorAll('.navzone')).forEach(function(z){
  z.addEventListener('click', function(){ go(parseInt(z.dataset.dir,10)) });
});

document.addEventListener('keydown', function(e){
  if(body.className !== 'mode-deck') return;
  if(e.key === 'ArrowRight' || e.key === ' ') go(1);
  else if(e.key === 'ArrowLeft') go(-1);
  else if(e.key === 'Escape'){ location.hash = '#/' }
});

var sx=0, sy=0, tracking=false;
deckEl.addEventListener('touchstart', function(e){
  if(e.touches.length!==1) return;
  sx = e.touches[0].clientX; sy = e.touches[0].clientY; tracking = true;
}, {passive:true});
deckEl.addEventListener('touchend', function(e){
  if(!tracking) return; tracking = false;
  var t = e.changedTouches[0], dx = t.clientX-sx, dy = t.clientY-sy;
  if(Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) go(dx < 0 ? 1 : -1);
}, {passive:true});

var mx = null;
deckEl.addEventListener('mousedown', function(e){ mx = e.clientX });
deckEl.addEventListener('mouseup', function(e){
  if(mx === null) return;
  var dx = e.clientX - mx; mx = null;
  if(Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
});

/* ---------- 라우팅 ---------- */
function route(){
  if(suppress) return;
  var m = /^#\/(\d{4}-\d{2}-\d{2})(?:\/(\d+))?/.exec(location.hash||'');
  if(m) openDay(m[1], m[2] ? parseInt(m[2],10) : 1);
  else showIndex();
}
window.addEventListener('hashchange', route);

renderList('');
route();
})();
</script>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("issues", type=Path, help="일자별 HTML이 들어있는 폴더")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--body", action="store_true", help="아티팩트 게시용 본문만 출력")
    a = ap.parse_args()
    print(f"'{a.issues}' 스캔 중…")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(build(a.issues, a.body), encoding="utf-8")
    print(f"→ {a.out} ({a.out.stat().st_size/1024:.1f} KB)")
