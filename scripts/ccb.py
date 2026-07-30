#!/usr/bin/env python3
"""Thin CLI for the ClaudeCodeBrowser HTTP API.

Usage:
  ccb.py call <tool> '<json-args>'          # one tool call, prints JSON result
  ccb.py eval <tab_id> <js-file-or-code>    # execute_script from a file or literal
"""
import json
import sys
import urllib.request
from pathlib import Path

TOKEN = (Path.home() / '.claudecodebrowser' / 'api_token').read_text().strip()
URL = 'http://127.0.0.1:8765/mcp/call'


def call(name, args, timeout=45):
    payload = json.dumps({'name': name, 'arguments': args}).encode()
    req = urllib.request.Request(
        URL, data=payload,
        headers={'Content-Type': 'application/json', 'X-API-Key': TOKEN})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


CLAIM_JS = r'''(()=>{
  if (document.getElementById('ccb-claim-style')) return 'already claimed';
  const st = document.createElement('style'); st.id = 'ccb-claim-style';
  st.textContent = 'html::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:2147483647;box-shadow:inset 0 0 0 4px #ff7a00, inset 0 0 18px rgba(255,122,0,.55);}';
  document.documentElement.appendChild(st);
  window.__ccbFavStash = [...document.querySelectorAll('link[rel~="icon"]')].map(l => { l.remove(); return l; });
  const fav = document.createElement('link'); fav.id = 'ccb-claim-fav'; fav.rel = 'icon';
  fav.href = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="#ff7a00"/><text x="8" y="12" font-size="10" text-anchor="middle" fill="#fff" font-family="monospace" font-weight="bold">C</text></svg>');
  document.head.appendChild(fav);
  const PFX = '[CC] ';
  const apply = () => { if (!document.title.startsWith(PFX)) document.title = PFX + document.title; };
  apply();
  const t = document.querySelector('title');
  if (t) { window.__ccbClaimMO = new MutationObserver(apply); window.__ccbClaimMO.observe(t, {childList:true, characterData:true, subtree:true}); }
  return 'claimed';
})()'''

RELEASE_JS = r'''(()=>{
  if (window.__ccbClaimMO) { window.__ccbClaimMO.disconnect(); delete window.__ccbClaimMO; }
  document.getElementById('ccb-claim-style')?.remove();
  document.getElementById('ccb-claim-fav')?.remove();
  (window.__ccbFavStash || []).forEach(l => document.head.appendChild(l));
  delete window.__ccbFavStash;
  if (document.title.startsWith('[CC] ')) document.title = document.title.slice(5);
  return 'released';
})()'''


def main():
    mode = sys.argv[1]
    if mode in ('claim', 'release'):
        js = CLAIM_JS if mode == 'claim' else RELEASE_JS
        r = call('browser_execute_script', {'tab_id': int(sys.argv[2]), 'script': js})
        print(r.get('result', r))
    elif mode == 'tabs':
        for t in call('browser_get_tabs', {})['tabs']:
            print(t['id'], 'ACTIVE' if t['active'] else '      ', t['url'][:70])
    elif mode == 'call':
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(call(sys.argv[2], args), indent=1)[:4000])
    elif mode == 'eval':
        tab = int(sys.argv[2])
        src = sys.argv[3]
        code = Path(src).read_text() if Path(src).exists() else src
        r = call('browser_execute_script', {'tab_id': tab, 'script': code})
        print(json.dumps(r, indent=1)[:4000])
    else:
        sys.exit(f'unknown mode {mode}')


if __name__ == '__main__':
    main()
