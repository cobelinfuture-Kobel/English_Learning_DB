'use strict';

// Unit01-only learner adapter.  The existing app.js remains authoritative for
// Unit02-24, dashboard, M7/M8, human review and session completion.
const u01qb15LegacyBegin = begin;
const u01qb15LegacyRenderGate = renderGate;

function u01qb15Semantics(){
  return (state&&state.learner_product_semantics)||{};
}

function u01qb15LessonIds(){
  return u01qb15Semantics().unit01_questionbank_lesson_ids||{};
}

function isU01QB15Lane(lane){
  if(!lane||u01qb15Semantics().unit01_questionbank_browser_route_active!==true)return false;
  return u01qb15LessonIds()[String(lane.skill||'').toUpperCase()]===lane.lesson_id;
}

function u01qb15GateIndex(row,index){
  return row.asset_index??row.item_index??index;
}

renderGate=function(gate){
  gateItems.replaceChildren();
  if(!active||!gate){gatePanel.hidden=true;complete.disabled=true;return;}
  gatePanel.hidden=false;
  const rows=gate.assets||[];
  if(gate.skill==='SPEAKING'){
    text(gateSummary,`口說是練習模式：已完成 ${gate.completed_exposure_count||0}／${gate.required_exposure_count||rows.length} 張，不錄音、不評分。`);
    rows.forEach((row,index)=>{
      const card=document.createElement('article');
      card.className='gate-item '+(row.completion_state==='EXPOSED'?'gate-ready':'gate-blocked');
      const title=document.createElement('strong');text(title,`第 ${u01qb15GateIndex(row,index+1)} 張`);
      const stateNode=document.createElement('p');text(stateNode,row.completion_state==='EXPOSED'?'練習已記錄':'尚未完成');
      card.append(title,stateNode);gateItems.append(card);
    });
    complete.disabled=!gate.completion_allowed;
    return;
  }
  text(gateSummary,gate.completion_allowed?'全部最新作答已通過，可以完成本次學習。':`已通過 ${gate.passed_response_count||0}／${gate.required_response_count||rows.length}；請完成其餘項目。`);
  rows.forEach((row,index)=>{
    const card=document.createElement('article');
    card.className='gate-item '+(row.completion_state==='PASSED'?'gate-ready':'gate-blocked');
    const title=document.createElement('strong');text(title,`第 ${u01qb15GateIndex(row,index+1)} 題`);
    const stateNode=document.createElement('p');text(stateNode,gateStateLabel(row.completion_state));
    const attempts=document.createElement('p');attempts.className='attempt-note';
    text(attempts,`作答次數：${row.attempt_count||0}${row.latest_outcome?'；最新：'+outcomeLabel(row.latest_outcome):''}`);
    card.append(title,stateNode,attempts);gateItems.append(card);
  });
  complete.disabled=!gate.completion_allowed;
};

function u01qb15ResponseFor(card,item){
  const options=item.options||[];
  if(options.length){
    const checked=card.querySelector('input[type=radio]:checked');
    if(!checked)throw new Error('請先選擇答案');
    return checked.value;
  }
  const area=card.querySelector('textarea');
  if(!area||!area.value.trim())throw new Error('請先輸入答案');
  if(item.response_mode==='ordered_tokens')return area.value.trim().split(/\s+/);
  return area.value;
}

async function u01qb15Expose(item){
  const result=await api('/api/u01qb15/exposure',{
    session_id:active.session_id,
    item_id:item.item_id,
    expected_session_version:active.session_version
  });
  active.session_version=result.session_version;
  return result;
}

function renderU01QB15Form(lane,form){
  currentLane=lane;renderUnits();renderLanes();items.replaceChildren();
  text(laneNote,`U01QB15-R1｜Form ${form.form_ordinal}／12｜只顯示 ${form.blueprint_activity_count} 個 blueprint activities；support fillers 不呈現給學習者。`);
  for(const item of form.items||[]){
    const card=document.createElement('article');card.className='card';card.dataset.u01qb15ItemId=item.item_id;
    const prompt=document.createElement('p');prompt.className='prompt';text(prompt,item.prompt);card.append(prompt);
    if(item.stimulus){
      const block=document.createElement('section');block.className='stimulus';
      const title=document.createElement('h4');text(title,`情境：${item.setting||item.situation_family||'Unit 01'}`);
      const body=document.createElement('p');text(body,item.stimulus);block.append(title,body);card.append(block);
    }
    const meta=document.createElement('p');meta.className='support-text';
    text(meta,`${item.task_angle}｜${item.support_level}${item.assessment_candidate?'｜Assessment':''}`);card.append(meta);
    const options=item.options||[];
    if(options.length){
      const box=document.createElement('div');box.className='options';
      for(const option of options){
        const label=document.createElement('label'),input=document.createElement('input');
        input.type='radio';input.name=item.item_id;input.value=option;
        label.append(input,document.createTextNode(' '+option));box.append(label);
      }
      card.append(box);
    }else if(item.capture_enabled){
      const area=document.createElement('textarea');area.setAttribute('aria-label','回答');card.append(area);
    }
    const button=document.createElement('button'),result=document.createElement('p');
    button.className='submit';result.className='result';
    if(item.capture_enabled){
      text(button,'送出回答');
      button.addEventListener('click',async()=>{
        try{
          button.disabled=true;
          await u01qb15Expose(item);
          const scored=await api('/api/u01qb15/response',{
            session_id:active.session_id,
            item_id:item.item_id,
            response:u01qb15ResponseFor(card,item),
            expected_session_version:active.session_version
          });
          active.session_version=scored.session_version;
          text(result,outcomeLabel(scored.outcome));
          await loadProgress();renderGate(scored.completion_gate);
        }catch(error){text(status,error.message)}finally{button.disabled=false}
      });
    }else{
      text(button,'完成這張口說練習');
      button.addEventListener('click',async()=>{
        try{
          button.disabled=true;
          const exposed=await u01qb15Expose(item);
          text(result,'練習已記錄');
          await loadProgress();renderGate(exposed.completion_gate);
        }catch(error){text(status,error.message)}finally{button.disabled=false}
      });
    }
    card.append(button,result);items.append(card);
  }
}

begin=async function(lane){
  if(!isU01QB15Lane(lane))return u01qb15LegacyBegin(lane);
  if(locked())throw new Error('請先繼續或放棄目前的本次學習');
  const form=await api('/api/u01qb15/form/start',{skill:lane.skill});
  active={
    session_id:form.session_id,
    session_version:form.session_version,
    lesson_id:lane.lesson_id,
    skill:form.skill,
    session_state:'ACTIVE'
  };
  pendingResume=null;updateActivePanel();complete.hidden=false;complete.disabled=true;
  renderU01QB15Form(lane,form);
  text(status,`Unit 01 新題庫開始：Form ${form.form_ordinal}／12・${lane.learner_label}`);
  await loadProgress();renderGate(form.completion_gate);
};

// The legacy resume listener is synchronous.  Intercept only Unit01 in capture
// phase so an active U01QB15 form can be loaded asynchronously from its bindings.
resume.addEventListener('click',async event=>{
  if(!pendingResume)return;
  const match=findLane(pendingResume.session.lesson_id);
  if(!match||!isU01QB15Lane(match.lane))return;
  event.preventDefault();event.stopImmediatePropagation();
  try{
    const value=await api('/api/u01qb15/form/active');
    if(!value.active)throw new Error('u01qb15_active_form_missing');
    const form=value.form;
    pendingResume=null;
    active={
      session_id:form.session_id,
      session_version:form.session_version,
      lesson_id:match.lane.lesson_id,
      skill:form.skill,
      session_state:'ACTIVE'
    };
    currentUnit=match.unit;currentLane=match.lane;updateActivePanel();
    complete.hidden=false;complete.disabled=true;renderU01QB15Form(match.lane,form);
    text(status,`繼續 Unit 01 新題庫：Form ${form.form_ordinal}／12・${match.lane.learner_label}`);
    await loadProgress();renderGate(value.completion_gate);
  }catch(error){text(status,error.message)}
},true);
