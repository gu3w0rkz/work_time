import React, {useState, useEffect} from 'react'

const API_URL = import.meta.env.VITE_API_URL

function getCookie(name){
  const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)')
  return v ? decodeURIComponent(v[2]) : null
}

export default function Login({onLogin}){
  const [email,setEmail] = useState('')
  const [password,setPassword] = useState('')

  useEffect(()=>{
    // fetch csrf to ensure cookie set
    fetch(`${API_URL}/api/csrf/`, {credentials: 'include'})
  },[])

  const [error, setError] = React.useState(null)

  async function submit(e){
    e.preventDefault()
    setError(null)
    const data = new URLSearchParams();
    data.append('email', email);
    data.append('password', password);
    const resp = await fetch(`${API_URL}/api/login/`, {method:'POST', credentials:'include', headers:{'X-CSRFToken': getCookie('csrftoken')}, body: data})
    const j = await resp.json().catch(()=>null)
    if (resp.ok){
      onLogin()
    } else {
      setError((j && j.error) || 'Login fallito')
    }
  }

  return (
    <div style={{maxWidth:400, margin:'2rem auto'}} className="card-panel">
      <h3 className="brand-title">Accedi</h3>
      <form onSubmit={submit}>
        <div><input className="form-control" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} /></div>
        <div className="mt-2"><input type="password" className="form-control" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} /></div>
        <div className="mt-2"><button className="btn btn-start">Accedi</button></div>
        {error && <div className="mt-2 text-danger">{error}</div>}
      </form>
    </div>
  )
}