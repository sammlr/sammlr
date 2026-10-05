"""Resolve one search field to album-qualified canonical needs; no matching engine."""
from dataclasses import dataclass
import re


def code_key(value):
    return re.sub(r'[\s\-_.]+', '', value).upper()


@dataclass(frozen=True)
class SearchIntent:
    kind: str
    targets: frozenset = frozenset()
    collector: str = ''
    ambiguous: tuple = ()


def resolve_search(text, album_names, planning_albums, needs, usernames=()):
    text=text.strip()
    if not text:return SearchIntent('all')
    if text.startswith('@'):return SearchIntent('collector',collector=text[1:].strip().casefold())
    aliases={}
    for album,name in album_names:
        for label in (album,name):aliases[code_key(label)]=aliases.get(code_key(label),set())|{album}
    normalized=code_key(text)
    album_matches=aliases.get(normalized,set())
    if not album_matches:
        album_matches={a for a,n in album_names if text.casefold() in n.casefold()}
    needed={(p.album_id,p.sticker_code) for p in needs}
    if album_matches:
        return SearchIntent('album',frozenset(k for k in needed if k[0] in album_matches))
    catalog={}
    for album in planning_albums:
        for code in album.catalog_codes:
            catalog.setdefault(code_key(code),set()).add((album.album_id,code))
    # Album-prefix search is an instruction, never a renamed physical code.
    words=text.split();scope=None;remainder=text
    for cut in range(len(words)-1,0,-1):
        match=aliases.get(code_key(' '.join(words[:cut])))
        if match:
            scope=match;remainder=' '.join(words[cut:]);break
    remainder=re.sub(r'\b([A-Za-z]{2,6})\s+(\d+)\b',r'\1\2',remainder)
    tokens=tuple(dict.fromkeys(code_key(t) for t in re.split(r'[,;\s/|]+',remainder) if t))
    concrete=bool(tokens) and all(t in catalog or re.fullmatch(r'[A-Z]{0,6}\d+',t) for t in tokens)
    if scope is None and not set(tokens)&catalog.keys() and any(text.casefold() in n.casefold() for n in usernames):
        concrete=False
    if not concrete:return SearchIntent('collector',collector=text.casefold())
    targets=set()
    for token in tokens:
        targets.update(k for k in catalog.get(token,set()) & needed if scope is None or k[0] in scope)
    ambiguity=tuple((token,len({a for a,c in targets if code_key(c)==token})) for token in tokens
                    if len({a for a,c in targets if code_key(c)==token})>1)
    return SearchIntent('stickers',frozenset(targets),ambiguous=ambiguity)
