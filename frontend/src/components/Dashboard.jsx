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
  const [selectedTags,setSelectedTags] = useState([])
  const [selectedProjectName, setSelectedProjectName] = useState('')
  const [description,setDescription] = useState('')
  const [hours,setHours] = useState('0')
  const [minutes,setMinutes] = useState('0')
  const [date,setDate] = useState(new Date().toISOString().slice(0,10))
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('10:00')
  const [weekTotal, setWeekTotal] = useState('')

  useEffect(()=>{ fetchData() }, [])

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
    if (selectedTags && selectedTags.length>0){ selectedTags.forEach(t=> data.append('tags', t)) }
    else if (selectedTag) data.append('tags', selectedTag);
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
    // append multiple tags if selected
    if(selectedTags && selectedTags.length>0){
      selectedTags.forEach(t=> data.append('tags', t))
    } else if (selectedTag){
      data.append('tag', selectedTag)
    }
    data.append('description', description)
    data.append('date', date)
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
      setSelectedTags([])
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
          <input className="form-control desc" placeholder="What have you worked on?" value={description} onChange={e=>setDescription(e.target.value)} />

          <div>
            <input list="projects-list" className="form-control project-w" placeholder="-- Project --" value={selectedProjectName} onChange={e=>{setSelectedProjectName(e.target.value); setSelectedProject('')}} />
            <datalist id="projects-list">
              {projects.map(p=> <option key={p.id} value={p.name} />)}
            </datalist>
          </div>

          <select multiple className="form-select med-w" value={selectedTags} onChange={e=>{
            const opts = Array.from(e.target.selectedOptions).map(o=>o.value)
            setSelectedTags(opts)
            setSelectedTag(opts[0]||'')
          }}>
            {tags.map(t=> <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>

          <div className="selected-tags">
            {selectedTags.map(id => {
              const t = tags.find(x=>String(x.id)===String(id))
              if(!t) return null
              return (
                <span key={id} className="tag-chip">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="tag-icon"><path d="M3 11L11 3L21 13L13 21L3 11Z" stroke="#2f8f5d" strokeWidth="1" fill="#e8fff3"/></svg>
                  {t.name}
                  <button className="tag-remove" onClick={()=> setSelectedTags(prev => prev.filter(x=>String(x)!==String(id)))}>×</button>
                </span>
              )
            })}
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
        <div className="week-total mb-3">Week total: <strong>{weekTotal}</strong>
          <ul className="week-summary">
            {groupByDate(entries).map(g=>{
              let daySec=0
              g.items.forEach(e=>{ if(e.start){ const s=new Date(e.start); const en=e.end?new Date(e.end):new Date(); daySec+=Math.max(0,(en-s)/1000) } })
              const dh = Math.floor(daySec/3600)
              const dm = Math.floor((daySec-dh*3600)/60)
              return <li key={g.date}>{g.date}: {dh}h {dm}m</li>
            })}
          </ul>
        </div>

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
                          <button className="btn-play" title="Start a new timer for this project" onClick={()=>{
                            // start new timer with same project/tags
                            setSelectedProject(projects.find(p=>p.name===e.project)?.id || '')
                            const tagIds = (e.tags || []).map(tname=> tags.find(t=>t.name===tname)?.id).filter(Boolean)
                            if(tagIds.length) setSelectedTags(tagIds)
                            // call toggle to start
                            toggle()
                          }}>▶</button>
                        ) : (
                          <button className="btn-pause" title="Stop running timer" onClick={()=>{ toggle() }}>⏸</button>
                        )}
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
