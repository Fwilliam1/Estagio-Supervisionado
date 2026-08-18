import { useState } from 'react'
import Login from './login/Login'
import Cadastro from './cadastro/Cadastro'
import Home from './home/Home'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('login') // 'login' | 'cadastro' | 'home'

  if (currentPage === 'login') {
    return (
      <Login
        onLogin={() => setCurrentPage('home')}
        onNavigateToRegister={() => setCurrentPage('cadastro')}
      />
    )
  }

  if (currentPage === 'cadastro') {
    return (
      <Cadastro
        onRegisterSuccess={() => setCurrentPage('home')}
        onNavigateToLogin={() => setCurrentPage('login')}
      />
    )
  }

  return (
    <Home
      onLogout={() => setCurrentPage('login')}
    />
  )
}

export default App
