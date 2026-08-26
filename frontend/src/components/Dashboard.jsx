import React, {useEffect, useState} from 'react'

function getCookie(name){
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)')
  return v ? decodeURIComponent(v[2]) : null
}

export default function Dashboard(){
  const [projects,setProjects] = useState([])
  const [tags,setTags] = useState([])
  const [entries,setEntries] = useState([])
  const [selectedProject,setSelectedProject] = useState('')
  const [selectedTag,setSelectedTag] = useState('')
  const [tagDropdownOpen, setTagDropdownOpen] = useState(false)
  const [selectedProjectName, setSelectedProjectName] = useState('')
  const [description,setDescription] = useState('')
  const [jiraQuery, setJiraQuery] = useState('')
  const [jiraResults, setJiraResults] = useState([])
  const [jiraOpen, setJiraOpen] = useState(false)
  const [jiraIssueType, setJiraIssueType] = useState('')
  const [hours,setHours] = useState('0')
  const [minutes,setMinutes] = useState('0')
  const [date,setDate] = useState(new Date().toISOString().slice(0,10))
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('10:00')
  const [weekTotal, setWeekTotal] = useState('')

  useEffect(()=>{ fetchData() }, [])

  useEffect(()=>{
    async function search(){
      if(!jiraQuery || jiraQuery.length<2) { setJiraResults([]); return }
      try{
        const resp = await fetch('/api/jira/search/?q='+encodeURIComponent(jiraQuery), {credentials:'include'})
        if(!resp.ok) return
        const j = await resp.json()
        setJiraResults(j.issues || [])
        setJiraOpen(true)
      }catch(err){ console.error(err) }
    }
    const t = setTimeout(search, 300)
    return ()=>clearTimeout(t)
  }, [jiraQuery])

  async function fetchData(){
    const p = await (await fetch('/api/projects/', {credentials:'include'})).json()
    setProjects(p.projects||[])
    const t = await (await fetch('/api/tags/', {credentials:'include'})).json()
    setTags(t.tags||[])
    const e = await (await fetch('/api/entries/', {credentials:'include'})).json()
    setEntries(e.entries||[])
    calcWeekTotal(e.entries||[])
  }

  function calcWeekTotal(entries){
    let totalSec = 0
    entries.forEach(e=>{
      if(e.start){
        const s = new Date(e.start)
        const en = e.end ? new Date(e.end) : new Date()
        totalSec += Math.max(0, (en - s)/1000)
      }
    })
    const h = Math.floor(totalSec/3600)
    const m = Math.floor((totalSec - h*3600)/60)
    setWeekTotal(`${h}h ${m}m`)
  }

  function findProjectIdByName(name){
    const p = projects.find(x=>x.name===name)
    return p ? p.id : ''
  }

  function groupByDate(entries){
    const map = {}
    entries.forEach(e=>{
      const key = e.start ? e.start.slice(0,10) : (new Date().toISOString().slice(0,10))
      if(!map[key]) map[key]=[]
      map[key].push(e)
    })
    return Object.keys(map).sort((a,b)=>b.localeCompare(a)).map(k=>({date:k, items: map[k]}))
  }

  function formatTime(iso){
    if(!iso) return ''
    const d = new Date(iso)
    return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})
  }

  function formatDate(dateStr){
    const d = new Date(dateStr)
    return d.toLocaleDateString()
  }

  function formatDuration(startIso, endIso){
    const s = new Date(startIso)
    const e = endIso ? new Date(endIso) : new Date()
    let diff = Math.max(0, (e - s)/1000)
    const hours = Math.floor(diff/3600)
    diff -= hours*3600
    const minutes = Math.floor(diff/60)
    return `${hours}h ${minutes}m`
  }

  async function toggle(){
    const data = new URLSearchParams();
    data.append('project', selectedProject);
    if (selectedTag) data.append('tags', selectedTag);
    const resp = await fetch('/api/toggle/', {method:'POST', credentials:'include', headers:{'X-CSRFToken': getCookie('csrftoken')}, body: data})
    if (resp.ok){ fetchData() }
  }

  function recap(){
    const h = Number(hours)||0
    const m = Number(minutes)||0
    return `${h}h ${m}m`
  }

  async function addEntry(){
    const data = new URLSearchParams()
    // project: prefer id found from typed project name
    const projectId = selectedProject || findProjectIdByName(selectedProjectName)
    data.append('project', projectId)
    if (selectedTag) data.append('tag', selectedTag)
    data.append('description', description)
    data.append('date', date)
    if (jiraIssueType) data.append('jira_issue_type', jiraIssueType)
    // prefer start/end if provided
    if (startTime && endTime){
      const startIso = new Date(date + 'T' + startTime + ':00').toISOString()
      const endIso = new Date(date + 'T' + endTime + ':00').toISOString()
      data.append('start', startIso)
      data.append('end', endIso)
    } else {
      data.append('hours', hours)
      data.append('minutes', minutes)
    }
    const resp = await fetch('/api/add_entry/', {method:'POST', credentials:'include', headers:{'X-CSRFToken': getCookie('csrftoken')}, body: data})
    if (resp.ok){
      setDescription('')
      setHours('0')
      setMinutes('0')
      setSelectedProject('')
      setSelectedTag('')
      setSelectedProjectName('')
      setStartTime('09:00')
      setEndTime('10:00')
      fetchData()
    } else {
      const j = await resp.json().catch(()=>null)
      alert('Errore: ' + (j && j.error ? j.error : resp.status))
    }
  }

  const isValidAdd = () => {
    if(!description || description.trim().length<2) return false
    const proj = selectedProject || findProjectIdByName(selectedProjectName)
    if(!proj) return false
    // if using times
    if(startTime && endTime){
      const s = new Date(date + 'T' + startTime + ':00')
      const e = new Date(date + 'T' + endTime + ':00')
      if(e <= s) return false
      return true
    }
    // else duration
    const h = Number(hours)||0
    const m = Number(minutes)||0
    return (h>0 || m>0)
  }

  // single tag selection handled by the select input

  return (
    <div className="container py-4">
      <div className="card-panel">
        <h3 className="brand-title">Dashboard</h3>

        <div className="top-bar mb-3">
          <div style={{position:'relative', flex:'1 1 40%', display:'flex', flexDirection:'column', gap:6}}>
            <div style={{position:'relative'}}>
              <div style={{display:'flex', alignItems:'center', gap:8}}>
                <input className="form-control jira-input" placeholder="Jira ticket" value={jiraQuery} onChange={e=>setJiraQuery(e.target.value)} />
                {jiraIssueType ? <span className="jira-type-badge">{jiraIssueType}</span> : null}
              </div>
              {jiraOpen && jiraResults.length>0 && (
                  <div className="jira-dropdown above" style={{left:8, width:'calc(100% - 16px)', maxHeight:200, overflow:'auto'}}>
                  {jiraResults.map(i=> (
                      <div key={i.key} className="jira-item" onClick={()=>{ setDescription((prev)=>`${i.key}: ${i.summary}`); setJiraOpen(false); setJiraQuery(''); setJiraIssueType(i.issuetype || '') }}>{i.key} — {i.summary}</div>
                    ))}
                </div>
              )}
            </div>
            <input className="form-control desc" placeholder="What have you worked on?" value={description} onChange={e=>setDescription(e.target.value)} />
          </div>

          <div>
            <select className="form-control project-w" value={selectedProject} onChange={e=>{
              const val = e.target.value
              setSelectedProject(val)
              const p = projects.find(p=>String(p.id)===String(val))
              setSelectedProjectName(p ? p.name : '')
            }}>
              <option value="">-- Project --</option>
              {projects.map(p=> (<option key={p.id} value={p.id}>{p.name}</option>))}
            </select>
          </div>

            <div className="tag-select-wrapper">
              {!selectedTag ? (
                <button className="tag-open" onClick={()=>setTagDropdownOpen(open=>!open)} title="Select tag">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <path d="M20.59 13.41L13.41 20.59C12.85 21.15 12.07 21.15 11.51 20.59L3.41 12.49C2.82 11.9 2.82 11.0 3.41 10.41L10.59 3.23C11.17 2.64 12.01 2.64 12.59 3.23L20.59 11.23C21.17 11.82 21.17 12.68 20.59 13.26V13.41Z" stroke="#2f8f5d" strokeWidth="1" fill="#e8fff3" />
                  </svg>
                </button>
              ) : (
                <div className="tag-display tag-selected" onClick={()=>setTagDropdownOpen(true)}>
                  <span className="tag-chip">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="tag-icon"><path d="M3 11L11 3L21 13L13 21L3 11Z" stroke="#2f8f5d" strokeWidth="1" fill="#e8fff3"/></svg>
                    {(tags.find(t=>String(t.id)===String(selectedTag))||{name:''}).name}
                  </span>
                </div>
              )}
              {tagDropdownOpen && (
                <div className="tag-dropdown">
                  {tags.map(t=> (
                    <div key={t.id} className="tag-dropdown-item" onClick={()=>{ setSelectedTag(t.id); setTagDropdownOpen(false) }}>{t.name}</div>
                  ))}
                </div>
              )}
            </div>

          <input type="time" className="form-control time-w" value={startTime} onChange={e=>setStartTime(e.target.value)} />
          <input type="time" className="form-control time-w" value={endTime} onChange={e=>setEndTime(e.target.value)} />

          <input type="date" className="form-control date-w" value={date} onChange={e=>setDate(e.target.value)} />

          <div className="px-2 duration">{formatDuration(date+'T'+startTime+':00', date+'T'+endTime+':00')}</div>

          <div className="add-toggle-stack">
            <button aria-label="Add entry" className="btn-add-icon" onClick={addEntry} disabled={!isValidAdd()} title={isValidAdd() ? 'Add entry' : 'Compila tutti i campi richiesti'}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="2" y="11" width="20" height="2" rx="1" fill="white"/>
                <rect x="11" y="2" width="2" height="20" rx="1" fill="white"/>
              </svg>
            </button>
            <button className="btn btn-toggle" onClick={toggle} title="Start/Stop timer">⏱</button>
          </div>

          {/* week total moved below */}
        </div>

        <h5>Ultime attività</h5>
        <div className="week-total mb-3">Week total: <strong>{weekTotal}</strong></div>

        {groupByDate(entries).map(g=> {
            // compute day total
            let daySec = 0
            g.items.forEach(e=>{
              if(e.start){
                const s = new Date(e.start)
                const en = e.end ? new Date(e.end) : new Date()
                daySec += Math.max(0, (en - s)/1000)
              }
            })
            const dh = Math.floor(daySec/3600)
            const dm = Math.floor((daySec - dh*3600)/60)
            const dayTotal = `${dh}h ${dm}m`
            return (
            <div key={g.date} className="mb-3">
              <div className="entries-day-header p-2">{formatDate(g.date)} <span className="day-total">{dayTotal}</span></div>
              
              
              <table className="entries-table">
                <thead>
                  <tr>
                    <th>Orario</th>
                    <th>Durata</th>
                    <th>Tipo</th>
                    <th>Progetto</th>
                    <th>Tag</th>
                    <th>Descrizione</th>
                  </tr>
                </thead>
                <tbody>
                  {g.items.map(e=> (
                    <tr key={e.id}>
                      <td>{formatTime(e.start)} — {e.end ? formatTime(e.end) : 'in corso'}</td>
                      <td>{formatDuration(e.start, e.end)}</td>
                      <td>{e.jira_issue_type || ''}</td>
                      <td>{e.project || 'No project'}</td>
                      <td>
                        {(e.tags || []).map((tname, idx)=> (
                          <span key={idx} className="tag-chip">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="tag-icon"><path d="M3 11L11 3L21 13L13 21L3 11Z" stroke="#2f8f5d" strokeWidth="1" fill="#e8fff3"/></svg>
                            {tname}
                          </span>
                        ))}
                      </td>
                      <td>{e.description || ''}</td>
                      <td className="row-action">
                        {e.end ? (
                          <></>
                        ) : (
                          <button className="btn-pause" title="Stop running timer" onClick={()=>{ toggle() }}>⏸</button>
                        )}
                        <button className="btn-delete" title="Delete entry" onClick={async()=>{
                          if(!confirm('Eliminare questa attività?')) return
                          const data = new URLSearchParams(); data.append('id', e.id)
                          const resp = await fetch('/api/delete_entry/', {method:'POST', credentials:'include', headers:{'X-CSRFToken': getCookie('csrftoken')}, body: data})
                          if(resp.ok){ fetchData() } else { alert('Errore durante l\'eliminazione') }
                        }}>🗑</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
          })
        }
      </div>
    </div>
  )
}
