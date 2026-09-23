const providersEl=document.querySelector('#providers');
const expectedEl=document.querySelector('#expected-calls');
const questionEl=document.querySelector('#question');
const countEl=document.querySelector('#char-count');
const runEl=document.querySelector('#run');
const progressEl=document.querySelector('#progress');
const globalErrorEl=document.querySelector('#global-error');
const resultsEl=document.querySelector('#results');
const finalEl=document.querySelector('#final-answer');
const analysisGridEl=document.querySelector('#analysis-grid');
let providerState=[];

function errorText(error){
  if(!error)return '알 수 없는 오류';
  return [error.message,error.hint,error.status_code?`HTTP ${error.status_code}`:'',error.error_type?`유형: ${error.error_type}`:'',error.request_id?`요청 ID: ${error.request_id}`:'',error.response_excerpt?`응답: ${error.response_excerpt}`:''].filter(Boolean).join('\n');
}
function renderProviders(items){
  providerState=items;
  providersEl.replaceChildren(...items.map(p=>{
    const card=document.createElement('article');card.className='provider';
    const top=document.createElement('div');top.className='provider-top';
    const title=document.createElement('h3');title.textContent=p.label;
    const badge=document.createElement('span');badge.className=`badge ${p.ready?'ready':''}`;badge.textContent=p.ready?'준비됨':p.enabled?'키 필요':'비활성';
    top.append(title,badge);
    const model=document.createElement('p');model.className='model';model.textContent=p.model;
    const button=document.createElement('button');button.className='test-btn';button.type='button';button.textContent='연결 테스트';button.disabled=!p.ready;
    const detail=document.createElement('p');detail.className='test-detail';
    button.addEventListener('click',()=>testProvider(p.id,button,badge,detail));
    card.append(top,model,button,detail);return card;
  }));
}
async function loadStatus(){
  try{const response=await fetch('/api/status');const data=await response.json();renderProviders(data.providers);expectedEl.textContent=`${data.expected_calls}회`;document.querySelector('#workflow').textContent=data.workflow;runEl.disabled=data.expected_calls!==4;}
  catch(error){showGlobal(`상태를 불러오지 못했습니다.\n${error.message}`);}
}
async function testProvider(id,button,badge,detail){
  button.disabled=true;button.textContent='테스트 중…';detail.textContent='';
  try{const response=await fetch(`/api/test/${id}`,{method:'POST'});const data=await response.json();if(!response.ok||!data.ok)throw data.error||{message:'연결 실패'};badge.className='badge ready';badge.textContent='연결 성공';detail.textContent=`${data.latency_ms}ms · ${data.preview}`;}
  catch(error){badge.className='badge fail';badge.textContent='연결 실패';detail.textContent=errorText(error);}
  finally{button.disabled=false;button.textContent='다시 테스트';}
}
function showGlobal(text){globalErrorEl.textContent=text;globalErrorEl.hidden=false;}
function renderResults(data){
  resultsEl.hidden=false;finalEl.textContent=data.final||'최종 종합이 생성되지 않았습니다.';analysisGridEl.replaceChildren();
  const labels={gemini:'Gemini 독립 분석',groq:'Groq 독립 분석',openrouter:'OpenRouter 독립 분석',synthesis:'최종 종합'};
  ['gemini','groq','openrouter'].forEach(id=>{const card=document.createElement('article');card.className=`panel analysis-card ${data.errors?.[id]?'error':''}`;const h=document.createElement('h3');h.textContent=labels[id];const body=document.createElement('div');body.className='answer';body.textContent=data.errors?.[id]?errorText(data.errors[id]):data.analyses?.[id]||'결과 없음';card.append(h,body);analysisGridEl.append(card);});
  if(data.errors?.synthesis)showGlobal(`최종 종합 오류\n${errorText(data.errors.synthesis)}`);
  resultsEl.scrollIntoView({behavior:'smooth',block:'start'});
}
questionEl.addEventListener('input',()=>{countEl.textContent=`${questionEl.value.length.toLocaleString()} / 12,000자`;});
runEl.addEventListener('click',async()=>{
  const question=questionEl.value.trim();if(!question){showGlobal('질문을 입력하세요.');questionEl.focus();return;}
  runEl.disabled=true;progressEl.hidden=false;globalErrorEl.hidden=true;resultsEl.hidden=true;runEl.textContent='검토 중…';
  try{const response=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});const data=await response.json();if(!response.ok&&data.error){throw data.error;}renderResults(data);if(!data.ok&&!data.error)showGlobal(`일부 공급자 호출에 실패했습니다. 실제 완료 호출: ${data.calls_completed}회`);}
  catch(error){showGlobal(errorText(error));}
  finally{runEl.disabled=providerState.filter(p=>p.ready).length!==3;progressEl.hidden=true;runEl.textContent='4단계 검토 시작';}
});
loadStatus();
