from pathlib import Path
import datetime as dt
import html as htmlmod
import json
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
SRC = ROOT / "overviews"
OUT = ROOT / "calendar.html"
SEEN = ROOT / "seen_bookings.json"
GUEST_HISTORY = ROOT / "guest_history.json"
BLOCKED_FILE = ROOT / "blocked_out_dates.txt"
PASS_FILE = ROOT / "calendar_password.txt"

# display name overrides
NAME_OVERRIDES = {
	"Lüdde Wattwurm 4d": "Lüdde Watt 4d",
}

# default UI scale (1.5 ≈ 150% zoom)
SCALE = 1.5

# auto refresh in minutes (0 disables). Page will reload with cache-buster.
AUTO_REFRESH_MIN = 60

# desired display order (top to bottom)
HOMES_ORDER = [
	"Sonnenwende 2a",
	"Dämmerlicht 2b",
	"Regenbogen 2c",
	"Wolke7 2d",
	"Küstenzauber 4a",
	"Strandliebe 4b",
	"Wellengang 4c",
	"Lüdde Wattwurm 4d",
	"Kl. Austernfischer",
	"Austernfischer",
	"Dat Lütte Huus1",
	"Dat Lütte Huus2",
	"Lütte Stuuv",
	"Fischers Huus",
	"Michels Koje",
	"Fietes Kajüte",
	"Fietes Lütte Huus",
	"Bös Lütte Stuuv",
]

def booking_key(home: str, start: dt.date, end: dt.date) -> str:
	return f"{home}|{start.isoformat()}|{end.isoformat()}"

def update_seen_and_new(bookings):
	"""Update first-seen store; return keys considered new (≤7 days)."""
	today = dt.date.today()
	first_run = not SEEN.exists()
	try:
		seen = json.loads(SEEN.read_text(encoding="utf-8"))
		# if file existed but was empty/invalid, treat as first run
		if not isinstance(seen, dict):
			seen = {}
			first_run = True
	except Exception:
		seen = {}
		first_run = True
	# migrate: if all stored dates equal today (from a previous version), backdate them
	if seen:
		_dates = []
		for _v in seen.values():
			try:
				_dates.append(dt.date.fromisoformat(_v))
			except Exception:
				pass
		if _dates and all(d == today for d in _dates):
			_back = (today - dt.timedelta(days=8)).isoformat()
			for _k in list(seen.keys()):
				seen[_k] = _back
	current = {booking_key(h, s, e) for (h, s, e, *_) in bookings}
	seed_date = (today - dt.timedelta(days=8)).isoformat() if first_run else today.isoformat()
	for k in current:
		if k not in seen:
			seen[k] = seed_date
	# prune
	seen = {k: v for k, v in seen.items() if k in current}
	def parse(d: str) -> dt.date:
		try:
			return dt.date.fromisoformat(d)
		except Exception:
			return today
	new_keys = {k for k in current if (today - parse(seen.get(k, today.isoformat()))).days <= 7}
	SEEN.write_text(json.dumps(seen, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
	return new_keys

def update_guest_history_and_repeat(bookings):
	"""Update guest history and return keys for repeat guest bookings."""
	try:
		history = json.loads(GUEST_HISTORY.read_text(encoding="utf-8"))
		if not isinstance(history, dict):
			history = {}
	except Exception:
		history = {}
	today = dt.date.today()
	repeat_keys = set()
	for home, start, end, guest, *_ in bookings:
		key = booking_key(home, start, end)
		if guest in history:
			repeat_keys.add(key)
		if guest not in history and end < today:
			history[guest] = today.isoformat()
	GUEST_HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
	return repeat_keys

def _to_sha256_hex(value: str) -> str:
	"""Return sha256 hex of value; if prefixed with 'sha256:' treat as pre-hashed."""
	s = (value or "").strip()
	if not s:
		return ""
	if s.startswith("sha256:"):
		return s.split(":", 1)[1].strip()
	return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_password_hash_hex() -> str:
	"""Load password from env or file and return its sha256 hex; empty string disables gate.

	Sources (first match wins):
	- env CALENDAR_PASSWORD (plain or 'sha256:<hex>')
	- file 'calendar_password.txt' next to this script (plain or 'sha256:<hex>')

	Returns empty string if no password configured (disables password gate).
	"""
	pw = os.environ.get("CALENDAR_PASSWORD", "").strip()
	if not pw and PASS_FILE.exists():
		try:
			pw = PASS_FILE.read_text(encoding="utf-8").strip()
		except Exception:
			pw = ""
	return _to_sha256_hex(pw)

def parse_date(s: str) -> dt.date:
	s = s.strip()
	# try full year format first
	for fmt in ("%d.%m.%Y", "%d.%m.%y"):
		try:
			return dt.datetime.strptime(s, fmt).date()
		except ValueError:
			continue
	raise ValueError(f"Cannot parse date: {s}")

def load_blocked_dates():
	"""Parse blocked out dates file; return list of (home, start, end)."""
	if not BLOCKED_FILE.exists():
		return []
	blocked = []
	for line in BLOCKED_FILE.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#"):
			continue
		parts = [p.strip() for p in line.split(",")]
		if len(parts) < 3:
			continue
		try:
			home, start, end = parts[0], parse_date(parts[1]), parse_date(parts[2])
			if end >= start:
				blocked.append((home, start, end))
		except Exception:
			continue
	return blocked

def collect_bookings():
	homes, bookings = [], []
	for fp in sorted(SRC.glob("*.txt")):
		home = fp.stem
		homes.append(home)
		lines = [ln for ln in fp.read_text(encoding="utf-8").splitlines() if ln.strip()]
		# Filter out summary lines (handles merged files with multiple summaries)
		lines = [ln for ln in lines if "Belegungen" not in ln]
		for line in lines:
			if "|" not in line: continue
			parts = [p.strip() for p in line.split("|")]
			if len(parts) < 4: continue
			try:
				start, end = parse_date(parts[2]), parse_date(parts[3])
			except Exception:
				continue
			if end < start: continue
			guest = parts[1]
			guest_count = None
			animals = None
			if len(parts) > 5:
				try:
					nums = [int(n.strip()) for n in parts[5].split("/")]
					a = nums[0] if len(nums) > 0 else 0
					b = nums[1] if len(nums) > 1 else 0
					animals = nums[2] if len(nums) > 2 else 0
					guest_count = a + b
				except Exception:
					pass
			bookings.append((home, start, end, guest, guest_count, animals))
	# order homes by desired display order, unknowns appended alphabetically
	unique = sorted(set(homes))
	order_idx = {name: i for i, name in enumerate(HOMES_ORDER)}
	homes_ordered = sorted(unique, key=lambda h: (order_idx.get(h, 10**6), h))
	return homes_ordered, bookings

def render(homes, bookings, blocked_dates=None, new_keys=frozenset(), repeat_keys=frozenset(), password_hash_hex: str = ""):
	if blocked_dates is None:
		blocked_dates = []
	if not homes: return "<h1>No homes found</h1>"
	if bookings:
		pass
	# show 1 year starting from 3 months ago
	today = dt.date.today()
	min_d = today - dt.timedelta(days=90)  # ~3 months back
	max_d = min_d + dt.timedelta(days=365)  # 1 year forward from start date
	days = (max_d - min_d).days
	# dynamic left label width and geometry with scale
	display_names = [NAME_OVERRIDES.get(h, h) for h in homes]
	max_name_len = max((len(n) for n in display_names), default=0)
	char_px = 6 * SCALE
	label_w = max(96 * SCALE, min(200 * SCALE, int(max_name_len * char_px + 12 * SCALE)))
	row_h, gap, top_h, day_w = 24 * SCALE, 6 * SCALE, 52 * SCALE, 16 * SCALE
	chart_w = max(1, days) * day_w
	h = top_h + len(homes) * row_h
	w = label_w + chart_w
	indices = {h:i for i, h in enumerate(homes)}
	def x(d: dt.date) -> float:
		return label_w + (d - min_d).days * day_w
	def row_y(i: int) -> float:
		return top_h + i * row_h
	def fmt(d: dt.date) -> str:
		return d.strftime("%d.%m.%Y")
	def ellipsize(text: str, max_px: float, px_per_char: float = 6.5) -> str:
		if max_px <= 0: return ""
		max_chars = int(max_px / px_per_char)
		if max_chars <= 0: return ""
		if len(text) <= max_chars: return text
		return (text[:max(1, max_chars-1)] + "…")
	# group bookings per home, sorted by start
	by_home = {}
	for home, start, end, guest, *rest in sorted(bookings, key=lambda t: (t[0], t[1], t[2])):
		gc = rest[0] if rest else None
		an = rest[1] if len(rest) > 1 else None
		by_home.setdefault(home, []).append((start, end, guest, gc, an, False))
	# add blocked dates as well
	for home, start, end in blocked_dates:
		by_home.setdefault(home, []).append((start, end, "BLOCKED", None, None, True))
	# sort each home's list by start date
	for home in by_home:
		by_home[home].sort(key=lambda t: (t[0], t[1]))
	lines = []
	lines.append("<!doctype html><meta charset=\"utf-8\"><meta http-equiv=\"Cache-Control\" content=\"no-cache, no-store, must-revalidate\"><meta http-equiv=\"Pragma\" content=\"no-cache\"><meta http-equiv=\"Expires\" content=\"0\"><title>Bookings Calendar</title>")
	# immediate cache-bust redirect if URL lacks ?t=
	lines.append("<script>(function(){try{var u=new URL(window.location.href);if(!u.searchParams.get('t')){u.searchParams.set('t',Date.now().toString());window.location.replace(u.toString());}}catch(e){}})();</script>")
	fs = 12 * SCALE
	smallfs = 10 * SCALE
	barlabfs = 11 * SCALE
	tipfs = 12 * SCALE
	sw1, sw2 = 1 * SCALE, 2 * SCALE
	# optional auth CSS
	auth_css = ""
	if password_hash_hex:
		auth_css = f"""
#gate{{position:fixed;inset:0;background:#fff;display:flex;align-items:center;justify-content:center;z-index:2000}}
#gate form{{background:#f7f7f7;padding:{12*SCALE}px {14*SCALE}px;border-radius:{8*SCALE}px;box-shadow:0 2px {12*SCALE}px rgba(0,0,0,.15);min-width:{260*SCALE}px}}
#gate label{{display:block;margin-bottom:{6*SCALE}px;color:#333;font-weight:600}}
#gate input{{font-size:{fs}px;padding:{6*SCALE}px {8*SCALE}px;width:100%;box-sizing:border-box;margin-bottom:{8*SCALE}px}}
#gate button{{font-size:{fs}px;padding:{6*SCALE}px {10*SCALE}px}}
"""

	lines.append(f"""
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,sans-serif;margin:0}}
.wrap{{display:flex;padding:8px}}
.labels-col{{flex:0 0 {label_w}px;overflow:hidden}}
.chart-col{{flex:1;overflow-x:auto}}
text{{font-size:{fs}px;fill:#222}}
.grid{{stroke:#eee;stroke-width:{sw1}}}
.day{{stroke:#f3f3f3;stroke-width:{sw1}}}
.sun{{fill:#d9e1f0}}
.month{{stroke:#ddd;stroke-width:{sw1}}}
.name{{fill:#111}}
.bar{{fill:#2b8cbe;rx:{3*SCALE};ry:{3*SCALE};stroke:#fff;stroke-width:{sw2};paint-order:stroke fill}}
.bar.new{{fill:#e67e22}}
.bar:hover{{fill:#1b6f97}}
.blocked{{fill:#ccc;rx:{3*SCALE};ry:{3*SCALE};stroke:#fff;stroke-width:{sw2};paint-order:stroke fill}}
.blocked:hover{{fill:#aaa}}
.today{{stroke:#f33;stroke-width:{sw1}}}
.legend{{font-size:{fs}px;fill:#555}}
.small{{font-size:{smallfs}px;fill:#666}}
.barlabel{{fill:#fff;font-size:{barlabfs}px;pointer-events:none}}
.tooltip{{position:fixed;z-index:1000;background:rgba(0,0,0,.85);color:#fff;padding:6px 8px;border-radius:4px;font-size:{tipfs}px;max-width:60vw;pointer-events:none;display:none}}
.turnover{{stroke:#f00;stroke-width:{4*SCALE}}}
{auth_css}
</style>
""")
	# auth gate markup + script (shown only if password configured)
	if password_hash_hex:
		lines.append("""
<div id=gate>
  <form id=gateForm>
    <label for=gateInput>Passwort</label>
    <input id=gateInput type=password autocomplete=current-password autofocus required>
    <button type=submit>Öffnen</button>
    <div id=gateMsg class=small style="margin-top:6px;color:#b00"></div>
  </form>
</div>
""")
	# hide calendar until authed when gate is active
	wrap_style = " style=\"display:none\"" if password_hash_hex else ""
	nav_html = "<p><a href='calendar.html'>Visual Calendar</a> &nbsp; <a href='quick_overview.html'>Quick Overview</a> &nbsp; <a href='arrivals.html'>Arrivals</a> &nbsp; <a href='departures.html'>Departures</a></p><br>"
	lines.append(f"<div id=nav{wrap_style} style=\"font-family:initial;margin:8px\">{nav_html}</div>")
	lines.append(f"<div class=wrap{wrap_style}>")
	# labels column
	lines.append(f"<div class=labels-col><svg width=\"{label_w}\" height=\"{h}\" xmlns=\"http://www.w3.org/2000/svg\">")
	for home, i in indices.items():
		y = row_y(i)
		mid = y + row_h/2
		display_home = NAME_OVERRIDES.get(home, home)
		name_label = ellipsize(display_home, label_w - 12*SCALE, 6.5*SCALE)
		lines.append(f"<text class=name x=\"8\" y=\"{mid+4}\">{htmlmod.escape(name_label)}</text>")
	lines.append("</svg></div>")
	# chart column
	lines.append(f"<div class=chart-col><svg class=cal width=\"{chart_w}\" height=\"{h}\" xmlns=\"http://www.w3.org/2000/svg\">")
	# month grid + labels
	m = dt.date(min_d.year, min_d.month, 1)
	while m <= max_d:
		xm = (m - min_d).days * day_w
		lines.append(f"<line class=month x1=\"{xm}\" y1=\"0\" x2=\"{xm}\" y2=\"{h}\"/>")
		label = m.strftime("%b %Y")
		lines.append(f"<text x=\"{xm + 4*SCALE}\" y=\"{top_h - 32*SCALE}\">{htmlmod.escape(label)}</text>")
		# next month
		next_month = m.replace(day=28) + dt.timedelta(days=4)
		m = next_month.replace(day=1)
	# daily grid and day numbers
	d = min_d
	show_every = 1 if day_w >= 14*SCALE else (2 if day_w >= 8*SCALE else 5)
	while d <= max_d:
		xd = (d - min_d).days * day_w
		# light sunday background band
		if d.weekday() == 6:
			lines.append(f"<rect class=sun x=\"{xd}\" y=\"{top_h}\" width=\"{day_w}\" height=\"{h-top_h}\"/>")
		lines.append(f"<line class=day x1=\"{xd}\" y1=\"{top_h}\" x2=\"{xd}\" y2=\"{h}\"/>")
		if (d.day % show_every == 0) or d.day == 1:
			lines.append(f"<text class=small x=\"{xd + 2*SCALE}\" y=\"{top_h - 10*SCALE}\">{d.day}</text>")
		d += dt.timedelta(days=1)
	# today marker
	today = dt.date.today()
	if min_d <= today <= max_d:
		x_t = (today - min_d).days * day_w
		lines.append(f"<line class=today x1=\"{x_t}\" y1=\"0\" x2=\"{x_t}\" y2=\"{h}\"/>")
	# rows and bookings
	for home, i in indices.items():
		y = row_y(i)
		mid = y + row_h/2
		lines.append(f"<line class=grid x1=\"0\" y1=\"{mid}\" x2=\"{chart_w}\" y2=\"{mid}\"/>")
		display_home = NAME_OVERRIDES.get(home, home)
		lst = by_home.get(home, [])
		for j, item in enumerate(lst):
			start, end, guest = item[:3]
			gc = item[3] if len(item) > 3 else None
			an = item[4] if len(item) > 4 else None
			is_blocked = item[5] if len(item) > 5 else False
			key = booking_key(home, start, end)
			display_guest = f"Stamm: {guest}" if key in repeat_keys else guest
			# clamp booking to visible window
			s, e = start, end
			if e < min_d or s > max_d:
				continue
			s = max(s, min_d)
			e = min(e, max_d)
			x0 = (s - min_d).days * day_w
			# inclusive end day
			dur_days = (e - s).days + 1
			bw = max(day_w, dur_days * day_w)
			# trim 1px if next booking touches this one and we did not clip the end
			if e == end and j+1 < len(lst) and lst[j+1][0] == end:
				bw = max(day_w, bw - 1)
			if is_blocked:
				tip = f"BLOCKED — {display_home}: {fmt(start)} – {fmt(end)}"
				cls = "blocked"
			else:
				is_new = key in new_keys
				extra = f" — {gc} guests" if gc is not None else ""
				animals_extra = f", {an} animals" if (an or 0) > 0 else ""
				tip = f"{display_guest} — {display_home}: {fmt(start)} – {fmt(end)}{extra}{animals_extra}" + (" — NEW" if is_new else "")
				cls = "bar new" if is_new else "bar"
			lines.append(f"<rect class=\"{cls}\" x=\"{x0}\" y=\"{y}\" width=\"{bw}\" height=\"{row_h-gap}\" data-tip=\"{htmlmod.escape(tip)}\"><title>{htmlmod.escape(tip)}</title></rect>")
			if bw >= 40*SCALE:
				label = ellipsize(display_guest if not is_blocked else "x", bw - 8*SCALE, 6.5*SCALE)
				if label:
					ly = y + (row_h - gap)/2 + 4*SCALE
					lines.append(f"<text class=barlabel x=\"{x0 + 4*SCALE}\" y=\"{ly}\">{htmlmod.escape(label)}</text>")
			# mark same-day turnover (departure day = next arrival day) - not for blocked dates
			if not is_blocked and j+1 < len(lst) and end == lst[j+1][0]:
				x_turn = (end - min_d).days * day_w
				if min_d <= end <= max_d:
					lines.append(f"<line class=turnover x1=\"{x_turn}\" y1=\"{y}\" x2=\"{x_turn}\" y2=\"{y + row_h - gap}\"/>")
	lines.append("</svg></div>")
	lines.append("</div>")
	lines.append("""
<div id=tip class=tooltip></div>
<script>
(function(){
const tip=document.getElementById('tip');
const svg=document.querySelector('svg.cal');
function show(t,x,y){tip.textContent=t;tip.style.display='block';tip.style.left=(x+12)+'px';tip.style.top=(y+12)+'px';}
function hide(){tip.style.display='none';}
svg.addEventListener('click',function(e){
  var r=e.target.closest&&e.target.closest('rect.bar,rect.bar.new');
  if(r){show(r.getAttribute('data-tip')||'',e.clientX,e.clientY);e.stopPropagation();}
});
document.addEventListener('click',hide);
})();
</script>
""")
	# auth script
	if password_hash_hex:
		# 30 days token
		days30_ms = 30*24*60*60*1000
		lines.append(f"""
<script>
(function(){{
const HASH='{password_hash_hex}';
const KEY='calAuth';
const TTL_MS={days30_ms};
const wrap=document.querySelector('.wrap');
const gate=document.getElementById('gate');
const nav=document.getElementById('nav');
function showApp(){{if(wrap)wrap.style.display='flex';if(nav)nav.style.display='block';if(gate)gate.style.display='none';}}
function valid(tok){{return tok&&tok.hash===HASH&&tok.exp>Date.now();}}
try{{
  const raw=localStorage.getItem(KEY);
  const tok=raw?JSON.parse(raw):null;
  if(valid(tok)){{showApp();}}
}}catch(_e){{}}
async function sha256Hex(s){{
  const b=new TextEncoder().encode(s);
  const d=await crypto.subtle.digest('SHA-256',b);
  return Array.from(new Uint8Array(d)).map(x=>x.toString(16).padStart(2,'0')).join('');
}}
function setOk(){{try{{localStorage.setItem(KEY,JSON.stringify({{hash:HASH,exp:Date.now()+TTL_MS}}));}}catch(_e){{}};showApp();}}
const form=document.getElementById('gateForm');
if(form){{
  form.addEventListener('submit',async function(e){{
    e.preventDefault();
    const msg=document.getElementById('gateMsg');
    const inp=document.getElementById('gateInput');
    const val=(inp&&inp.value)||'';
    try{{
      const h=await sha256Hex(val);
      if(h===HASH){{setOk();return;}}
    }}catch(_e){{}}
    if(msg)msg.textContent='Falsches Passwort';
  }});
}}
}})();
</script>
""")
	if AUTO_REFRESH_MIN > 0:
		ms = int(AUTO_REFRESH_MIN * 60 * 1000)
		gen_ms = int(dt.datetime.now(dt.UTC).timestamp() * 1000)
		snippet = """
<script>(function(){{
var GEN_MS={gen_ms};
var REFRESH_MS={ms};
var LOAD_TIME=Date.now();
var MIN_AGE_BEFORE_CHECK=5000;
function bust(u){{var x=new URL(u);x.searchParams.set('t',Date.now().toString());return x.toString();}}
function reload(){{window.location.replace(bust(window.location.href));}}
function reloadIfVisible(){{if(document.visibilityState==='visible') reload();}}
function reloadIfStale(){{
var timeSinceLoad=Date.now()-LOAD_TIME;
if(timeSinceLoad<MIN_AGE_BEFORE_CHECK)return;
if(Date.now()-GEN_MS>REFRESH_MS)reload();
}}
if(REFRESH_MS>0)setInterval(reloadIfVisible,REFRESH_MS);
document.addEventListener('visibilitychange',function(){{if(document.visibilityState==='visible')reloadIfStale();}});
window.addEventListener('focus',reloadIfStale);
window.addEventListener('pageshow',reloadIfStale);
}})();</script>
""".format(gen_ms=gen_ms, ms=ms)
		lines.append(snippet)
	# auto-scroll to 5 days before today
	days_to_scroll = max(0, (today - min_d).days - 5)
	scroll_px = days_to_scroll * day_w
	lines.append(f"""
<script>
(function(){{
const col=document.querySelector('.chart-col');
if(col)col.scrollLeft={scroll_px};
}})();
</script>
""")
	lines.append("</div>")
	return "".join(lines)

def main():
	homes, bookings = collect_bookings()
	blocked = load_blocked_dates()
	new_keys = update_seen_and_new(bookings)
	repeat_keys = update_guest_history_and_repeat(bookings)
	pass_hash = load_password_hash_hex()
	OUT.write_text(render(homes, bookings, blocked, new_keys, repeat_keys, pass_hash), encoding="utf-8")
	print(f"Wrote {OUT}")

if __name__ == "__main__":
	main()
