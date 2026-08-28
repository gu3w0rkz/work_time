import React, { useState, useEffect } from 'react'
import Login from './components/Login'
import Dashboard from './components/Dashboard'

const API_URL = import.meta.env.VITE_API_URL

export default function App(){
  const [user, setUser] = useState(null)

  useEffect(()=>{
    fetch(`${API_URL}/api/entries/`, {credentials: 'include'}).then(r=>{
      if (r.status===200) setUser({});
    }).catch(()=>{});
  }, [])

  return (
    <div>
      {!user ? <Login onLogin={()=>setUser({})} /> : <Dashboard />}
    </div>
  )
}