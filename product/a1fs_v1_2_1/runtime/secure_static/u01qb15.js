'use strict';

// Unit01-only learner adapter. The existing app.js remains authoritative for
// Unit02-24, dashboard, M7/M8, human review and the underlying session authority.
const u01qb15LegacyBegin = begin;
const u01qb15LegacyFinish = finish;
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

function u01qb15ActiveSession(){
  if(!active)return false;
  return Object.values(u01qb15LessonIds()).includes(active.lesson_id);
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
  if(gate.gate_mode==='U01QB16E_ATTEMPT_ONCE_THEN_DIAGNOSE_REASSESS'){
    const failed=gate.different_item_reassessment_required_count||0;
    text(
      gateSummary,
      gate.completion_allowed
        ? (failed?`本 Form 已完成一次作答；${failed} 題會在完成後進入補救與換題重評。`:'本 Form 已完成一次作答，可以完成本次學習。')
        :`已作答 ${gate.attempted_response_count||0}／${gate.required_response_count||rows.length}；每題只作答一次。`
    );
  }else{
    text(gateSummary,gate.completion_allowed?'全部最新作答已通過，可以完成本次學習。':`已通過 ${gate.passed_response_count||0}／${gate.required_response_count||rows.length}；請完成其餘項目。`);
  }
  rows.forEach((row,index)=>{
    const card=document.createElement('article');
    const captured=row.completion_state==='PASSED'||row.completion_state==='RETRY_REQUIRED';
    card.className='gate-item '+(captured?'gate-ready':'gate-blocked');
    const title=document.createElement('strong');text(title,`第 ${u01qb15GateIndex(row,index+1)} 題`);
    const stateNode=document.createElement('p');
    text(stateNode,row.completion_state==='RETRY_REQUIRED'?'已記錄錯誤；完成後換題補救':gateStateLabel(row.completion_state));
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
  if(item.response_mode==='ordered_tokens'||item.task_angle==='WORD_ORDER')return area.value.trim().split(/\s+/);
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

function u01qb15AppendResponseControls(card,item,onSubmit){
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
  button.className='submit';result.className='result';text(button,'送出回答');
  button.addEventListener('click',async()=>{
    try{
      button.disabled=true;
      const scored=await onSubmit(card,item);
      text(result,outcomeLabel(scored.outcome));
      card.dataset.u01qb16eAttempted='true';
    }catch(error){text(status,error.message)}finally{
      button.disabled=card.dataset.u01qb16eAttempted==='true';
    }
  });
  card.append(button,result);
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
    if(item.capture_enabled){
      u01qb15AppendResponseControls(card,item,async(cardNode,itemNode)=>{
        await u01qb15Expose(itemNode);
        const scored=await api('/api/u01qb15/response',{
          session_id:active.session_id,
          item_id:itemNode.item_id,
          response:u01qb15ResponseFor(cardNode,itemNode),
          expected_session_version:active.session_version
        });
        active.session_version=scored.session_version;
        await loadProgress();renderGate(scored.completion_gate);
        return scored;
      });
    }else{
      const button=document.createElement('button'),result=document.createElement('p');
      button.className='submit';result.className='result';text(button,'完成這張口說練習');
      button.addEventListener('click',async()=>{
        try{
          button.disabled=true;
          const exposed=await u01qb15Expose(item);
          text(result,'練習已記錄');card.dataset.u01qb16eAttempted='true';
          await loadProgress();renderGate(exposed.completion_gate);
        }catch(error){text(status,error.message)}finally{button.disabled=card.dataset.u01qb16eAttempted==='true'}
      });
      card.append(button,result);
    }
    items.append(card);
  }
}

async function u01qb16ePending(){
  if(u01qb15Semantics().unit01_different_item_reassessment_active!==true)return {pending:false,count:0,reassessments:[]};
  return api('/api/u01qb16e/reassessment/pending');
}

function renderU01QB16ERemediation(row){
  items.replaceChildren();gatePanel.hidden=true;complete.hidden=true;complete.disabled=true;
  const card=document.createElement('article');card.className='card';
  const title=document.createElement('h3');text(title,'錯題補救');
  const reason=document.createElement('p');text(reason,`診斷：${row.targeted_error_tag}`);
  const strategy=document.createElement('p');strategy.className='support-text';text(strategy,`補救：${row.targeted_remediation_strategy}`);
  const note=document.createElement('p');text(note,'完成補救後，系統會用不同題目重新評量；不會直接重做剛才的錯題。');
  const button=document.createElement('button');button.className='submit';text(button,'完成補救，開始換題重評');
  button.addEventListener('click',async()=>{
    try{
      button.disabled=true;
      const value=await api('/api/u01qb16e/reassessment/start',{
        diagnosis_id:row.diagnosis_id,
        remediation_acknowledged:true
      });
      active={
        session_id:value.session_id,
        session_version:value.session_version,
        lesson_id:value.lesson_id,
        skill:value.skill,
        session_state:'ACTIVE',
        u01qb16e_reassessment:true
      };
      pendingResume=null;updateActivePanel();renderU01QB16EReassessment(value);
    }catch(error){text(status,error.message);button.disabled=false}
  });
  card.append(title,reason,strategy,note,button);items.append(card);
  text(laneNote,'Unit 01｜Adaptive remediation → different-item reassessment');
  text(status,'有錯題需要先補救，再以不同題目重新評量。');
}

function renderU01QB16EReassessment(value){
  items.replaceChildren();gatePanel.hidden=true;complete.hidden=true;complete.disabled=true;
  const item=value.item;
  const card=document.createElement('article');card.className='card';card.dataset.u01qb16eItemId=item.item_id;
  const title=document.createElement('h3');text(title,'換題重新評量');
  const remediation=document.createElement('p');remediation.className='support-text';
  text(remediation,`補救策略：${value.targeted_remediation_strategy}`);
  const prompt=document.createElement('p');prompt.className='prompt';text(prompt,item.prompt);
  card.append(title,remediation,prompt);
  if(item.stimulus){
    const block=document.createElement('section');block.className='stimulus';
    const heading=document.createElement('h4');text(heading,`新情境：${item.setting||item.situation_family||'Unit 01'}`);
    const body=document.createElement('p');text(body,item.stimulus);block.append(heading,body);card.append(block);
  }
  const meta=document.createElement('p');meta.className='support-text';
  text(meta,`${item.task_angle}｜${item.support_level}｜Different-item reassessment`);card.append(meta);
  u01qb15AppendResponseControls(card,item,async(cardNode,itemNode)=>{
    const scored=await api('/api/u01qb16e/reassessment/response',{
      session_id:active.session_id,
      response:u01qb15ResponseFor(cardNode,itemNode),
      expected_session_version:active.session_version
    });
    const outcome=scored.outcome;
    active=null;pendingResume=null;updateActivePanel();
    await loadProgress();
    text(status,`換題重評：${outcomeLabel(outcome)}`);
    setTimeout(()=>{u01qb16eMaybeRenderPending().catch(error=>text(status,error.message));},0);
    return scored;
  });
  items.append(card);
  text(laneNote,'Unit 01｜不同題目重新評量｜原錯題不重播');
}

async function u01qb16eMaybeRenderPending(){
  const value=await u01qb16ePending();
  if(!value.pending||!(value.reassessments||[]).length)return false;
  const row=value.reassessments.find(item=>item.active_reassessment_session!==true)||value.reassessments[0];
  if(row.active_reassessment_session){
    const activeValue=await api('/api/u01qb16e/reassessment/active');
    if(activeValue.active){
      const reassessment=activeValue.reassessment;
      active={
        session_id:reassessment.session_id,
        session_version:reassessment.session_version,
        lesson_id:reassessment.lesson_id,
        skill:reassessment.skill,
        session_state:'ACTIVE',
        u01qb16e_reassessment:true
      };
      updateActivePanel();renderU01QB16EReassessment(reassessment);return true;
    }
  }
  renderU01QB16ERemediation(row);return true;
}

async function u01qb15BackendTerminalTruth(){
  const [sessionState,formState]=await Promise.all([
    api('/api/session/active'),
    api('/api/u01qb15/form/active')
  ]);
  return {
    session_inactive:sessionState.active===false,
    form_inactive:formState.active===false
  };
}

async function u01qb15ClearFinishedState(done,{reconciled=false}={}){
  const stateLabel=String(done&&done.session_state||'COMPLETED');
  const refreshStatus=String(done&&done.canonical_refresh_status||'');
  active=null;pendingResume=null;updateActivePanel();complete.hidden=true;complete.disabled=true;
  items.replaceChildren();gatePanel.hidden=true;
  if(refreshStatus==='RECOVERY_REQUIRED'){
    text(status,'本次學習已完成；精熟／複習狀態將在下一個 Unit 01 Form 前自動恢復。');
  }else if(reconciled){
    text(status,`${stateLabel}｜已依後端狀態完成前端同步`);
  }else{
    text(status,stateLabel);
  }
  await loadProgress();
}

finish=async function(path){
  if(!u01qb15ActiveSession()||active.u01qb16e_reassessment)return u01qb15LegacyFinish(path);
  const expectedTerminal=path==='/api/session/abandon'?'ABANDONED':'COMPLETED';
  const sessionId=active.session_id;
  const expectedVersion=active.session_version;
  try{
    const done=await api(path,{session_id:sessionId,expected_session_version:expectedVersion});
    await u01qb15ClearFinishedState(done);
    if(expectedTerminal==='COMPLETED')await u01qb16eMaybeRenderPending();
    return done;
  }catch(error){
    try{
      const truth=await u01qb15BackendTerminalTruth();
      if(truth.session_inactive&&truth.form_inactive){
        const recovered={
          session_id:sessionId,
          session_state:expectedTerminal,
          completion_committed:expectedTerminal==='COMPLETED',
          frontend_reconciled_after_transport_failure:true
        };
        await u01qb15ClearFinishedState(recovered,{reconciled:true});
        if(expectedTerminal==='COMPLETED')await u01qb16eMaybeRenderPending();
        return recovered;
      }
    }catch(_reconcileError){
      // Preserve the original request error unless backend truth proves terminal.
    }
    throw error;
  }
};

begin=async function(lane){
  if(!isU01QB15Lane(lane))return u01qb15LegacyBegin(lane);
  if(locked())throw new Error('請先繼續或放棄目前的本次學習');
  if(await u01qb16eMaybeRenderPending())return;
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

// The legacy resume listener is synchronous. Intercept only Unit01 in capture
// phase so an active U01QB15 form or U01QB16E reassessment can be restored.
resume.addEventListener('click',async event=>{
  if(!pendingResume)return;
  const match=findLane(pendingResume.session.lesson_id);
  if(!match||!isU01QB15Lane(match.lane))return;
  event.preventDefault();event.stopImmediatePropagation();
  try{
    const reassessment=await api('/api/u01qb16e/reassessment/active');
    if(reassessment.active){
      const value=reassessment.reassessment;
      pendingResume=null;
      active={
        session_id:value.session_id,
        session_version:value.session_version,
        lesson_id:value.lesson_id,
        skill:value.skill,
        session_state:'ACTIVE',
        u01qb16e_reassessment:true
      };
      currentUnit=match.unit;currentLane=match.lane;updateActivePanel();
      renderU01QB16EReassessment(value);return;
    }
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
