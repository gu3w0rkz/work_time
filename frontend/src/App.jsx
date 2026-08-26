import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

export default function App(){
  const [user, setUser] = useState(null)

  useEffect(()=>{
    // try to get CSRF and check session by calling entries endpoint
    fetch('/api/entries/', {credentials: 'include'}).then(r=>{
      if (r.status===200) setUser({});
    }).catch(()=>{});
  }, [])

  return (
    <div>
      {!user ? <Login onLogin={()=>setUser({})} /> : <Dashboard />}
    </div>
  )
}
