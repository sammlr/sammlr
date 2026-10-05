from pathlib import Path
import json
from flask import Flask
from playwright.sync_api import sync_playwright
app=Flask(__name__);app.secret_key='sammlr-explicit-testing-secret';c=app.session_interface.get_signing_serializer(app).dumps({'user_id':1,'auth_version':1})
OUT=Path(__file__).resolve().parents[2]/'tests/research/artifacts/borse-ui01'
OUT.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
 b=p.chromium.launch();page=b.new_page(viewport={'width':375,'height':900});page.context.add_cookies([{'name':'session','value':c,'url':'http://127.0.0.1:18081'}]);
 for route,label in [('/album/vfl','wall'),('/tauschen','trade')]:
  signed=app.session_interface.get_signing_serializer(app).dumps({'user_id':3 if label=='wall' else 1,'auth_version':1})
  page.context.add_cookies([{'name':'session','value':signed,'url':'http://127.0.0.1:18081'}])
  page.goto('http://127.0.0.1:18081'+route)
  page.locator('.slot[data-code="116"]').first.scroll_into_view_if_needed()
  page.locator('.slot[data-code="116"]').first.screenshot(path=str(OUT/f'bubble-{label}-116.png'))
  result=page.evaluate('''async()=>{
 const data=new DOMParser().parseFromString(await (await fetch('/static/sammlr-retro-digits-v3.svg')).text(),'image/svg+xml');
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.style.cssText='position:fixed;left:-1000px;width:0;height:0';document.body.append(svg);
 const result=[...document.querySelectorAll('.slot[data-code="116"]')].map(e=>{
 const q=e.querySelector('.sticker-qty').getBoundingClientRect(),cx=(q.left+q.right)/2,cy=(q.top+q.bottom)/2,r=q.width/2;
 let hits=0;
 for(const use of e.querySelectorAll('.sammlr-retro-number-visual use')){
 const id=use.getAttribute('href').split('#')[1],path=data.getElementById(id).querySelector('path').cloneNode(true);svg.append(path);
 const inverse=use.getScreenCTM().inverse();
 for(let x=q.left+.25;x<q.right;x+=.5)for(let y=q.top+.25;y<q.bottom;y+=.5){if((x-cx)**2+(y-cy)**2>=r*r)continue;const point=new DOMPoint(x,y).matrixTransform(inverse);if(path.isPointInFill(point))hits++;}
 path.remove();
 }
 return {code:e.dataset.code,hits};
 });svg.remove();return result;
 }''')
  results.append({'source':label,'viewport':375,'glyph_circle_intersections':result})
 b.close()
(OUT/'bubble-conflict.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['glyph_circle_intersections'][0]['hits']>0 for r in results)
print('CONFIRMED: existing canonical bubble conflict in both wall and Trade; no geometry changed')
