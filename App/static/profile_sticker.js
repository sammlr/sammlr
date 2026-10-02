(function(){
    'use strict';
    const editor=document.querySelector('[data-sticker-editor]');
    if(!editor)return;
    const form=editor.querySelector('[data-sticker-form]');
    const sticker=editor.querySelector('.profile-sticker-70');
    const portrait=sticker.querySelector('.profile-sticker-portrait');
    const nameInput=form.querySelector('[data-sticker-name]');
    const clubInput=form.querySelector('[data-sticker-club]');
    const countryInput=form.querySelector('[data-sticker-country]');
    const fileInput=form.querySelector('[data-portrait-input]');
    const countries=JSON.parse(editor.dataset.countries);
    const colors=JSON.parse(editor.dataset.colors);
    const csrf=document.querySelector('meta[name="csrf-token"]').content;
    let portraitBlob=null, objectUrl=null, cameraStream=null;

    function nameClass(value){const n=value.trim().length;return n<=7?'is-short':n<=14?'is-medium':n<=22?'is-long':'is-extra-long'}
    function updateText(){
        const value=nameInput.value.trim()||'SAMMLR';
        sticker.querySelector('.profile-sticker-name').textContent=value.toUpperCase();
        sticker.querySelector('.profile-sticker-portrait').alt='Profilfoto von '+value;
        ['is-short','is-medium','is-long','is-extra-long'].forEach(c=>sticker.classList.remove(c));sticker.classList.add(nameClass(value));
        const club=clubInput.value.trim();const clubNode=sticker.querySelector('.profile-sticker-club');clubNode.textContent=club.toUpperCase();clubNode.classList.toggle('is-empty',!club);
    }
    function updateCountry(){const item=countries[countryInput.value];if(!item)return;sticker.dataset.countryCode=item.code;sticker.querySelector('.profile-sticker-country-name').textContent=item.label;sticker.querySelector('.profile-sticker-nation-corner').setAttribute('aria-label','Nationalfarben '+item.label);sticker.querySelectorAll('.profile-sticker-nation-color').forEach((node,i)=>node.style.setProperty('--nation-band',item.bands[i]));}
    function updateColor(input){const item=colors[input.value];if(!item)return;sticker.dataset.accent=item.code;sticker.style.setProperty('--sticker-accent',item.hex);const club=sticker.querySelector('.profile-sticker-club');club.classList.remove('contrast-light','contrast-dark');club.classList.add('contrast-'+item.contrast);}
    nameInput.addEventListener('input',updateText);clubInput.addEventListener('input',updateText);countryInput.addEventListener('change',updateCountry);form.querySelectorAll('[data-sticker-color]').forEach(input=>input.addEventListener('change',()=>updateColor(input)));

    const cropModal=document.querySelector('[data-crop-modal]'),cropImage=cropModal.querySelector('[data-crop-image]');
    const hidden={x:form.querySelector('[data-crop-x]'),y:form.querySelector('[data-crop-y]'),zoom:form.querySelector('[data-crop-zoom]')};
    const controls={x:cropModal.querySelector('[data-crop-control="x"]'),y:cropModal.querySelector('[data-crop-control="y"]'),zoom:cropModal.querySelector('[data-crop-control="zoom"]')};
    function paintCrop(){cropImage.style.setProperty('--crop-x',controls.x.value+'%');cropImage.style.setProperty('--crop-y',controls.y.value+'%');cropImage.style.setProperty('--crop-zoom',controls.zoom.value)}
    Object.values(controls).forEach(control=>control.addEventListener('input',paintCrop));
    function openCrop(blob){portraitBlob=blob;if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=URL.createObjectURL(blob);cropImage.src=objectUrl;controls.x.value=hidden.x.value;controls.y.value=hidden.y.value;controls.zoom.value=hidden.zoom.value;paintCrop();cropModal.hidden=false;}
    function normaliseImage(file){
        if(!/^image\/(jpeg|png)$/.test(file.type)){return Promise.reject(new Error('Bitte ein JPEG- oder PNG-Bild auswählen.'))}
        return new Promise((resolve,reject)=>{const img=new Image();const url=URL.createObjectURL(file);img.onload=()=>{URL.revokeObjectURL(url);const scale=Math.min(1,1400/Math.max(img.naturalWidth,img.naturalHeight));const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(img.naturalWidth*scale));canvas.height=Math.max(1,Math.round(img.naturalHeight*scale));canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>blob?resolve(blob):reject(new Error('Das Foto konnte nicht verarbeitet werden.')),'image/jpeg',.84)};img.onerror=()=>{URL.revokeObjectURL(url);reject(new Error('Das Foto konnte nicht gelesen werden.'))};img.src=url;});
    }
    function report(error){const status=form.querySelector('[data-camera-status]');status.textContent=error.message;status.classList.add('is-error')}
    fileInput.addEventListener('change',()=>{const file=fileInput.files[0];if(file)normaliseImage(file).then(openCrop).catch(report)});
    cropModal.querySelector('[data-crop-apply]').addEventListener('click',()=>{Object.keys(hidden).forEach(k=>hidden[k].value=controls[k].value);portrait.src=objectUrl;portrait.style.setProperty('--crop-x',controls.x.value+'%');portrait.style.setProperty('--crop-y',controls.y.value+'%');portrait.style.setProperty('--crop-zoom',controls.zoom.value);sticker.style.setProperty('--crop-x',controls.x.value+'%');sticker.style.setProperty('--crop-y',controls.y.value+'%');sticker.style.setProperty('--crop-zoom',controls.zoom.value);cropModal.hidden=true;});
    cropModal.querySelector('[data-crop-cancel]').addEventListener('click',()=>{portraitBlob=null;cropModal.hidden=true;fileInput.value=''});

    const cameraModal=document.querySelector('[data-camera-modal]'),video=cameraModal.querySelector('[data-camera-video]');
    function closeCamera(){cameraModal.hidden=true;if(cameraStream){cameraStream.getTracks().forEach(track=>track.stop());cameraStream=null}}
    form.querySelector('[data-open-camera]').addEventListener('click',async()=>{if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){report(new Error('Kamera nicht verfügbar. Bitte Foto auswählen.'));fileInput.focus();return}try{cameraStream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});video.srcObject=cameraStream;await video.play();cameraModal.hidden=false}catch(error){report(new Error('Kamerazugriff nicht möglich. Bitte Foto auswählen.'));fileInput.focus()}});
    cameraModal.querySelector('[data-camera-close]').addEventListener('click',closeCamera);
    cameraModal.querySelector('[data-camera-capture]').addEventListener('click',()=>{const canvas=document.createElement('canvas');const scale=Math.min(1,1400/Math.max(video.videoWidth,video.videoHeight));canvas.width=Math.max(1,Math.round(video.videoWidth*scale));canvas.height=Math.max(1,Math.round(video.videoHeight*scale));const context=canvas.getContext('2d');context.translate(canvas.width,0);context.scale(-1,1);context.drawImage(video,0,0,canvas.width,canvas.height);canvas.toBlob(blob=>{closeCamera();if(blob)openCrop(blob)},'image/jpeg',.84)});

    form.addEventListener('submit',async event=>{if(!portraitBlob)return;event.preventDefault();const data=new FormData(form);data.set('portrait',portraitBlob,'portrait.jpg');const button=form.querySelector('[type="submit"]');button.disabled=true;form.setAttribute('aria-busy','true');try{const response=await fetch(form.action,{method:'POST',headers:{'X-CSRF-Token':csrf},body:data,credentials:'same-origin'});if(response.redirected){window.location.assign(response.url);return}if(!response.ok)throw new Error('Speichern nicht möglich. Bitte Eingaben prüfen.');window.location.assign('/profil')}catch(error){button.disabled=false;form.removeAttribute('aria-busy');report(error)}});
})();
