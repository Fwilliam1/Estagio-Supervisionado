import { useState, useEffect } from 'react'
import Login from './login/Login'
import Cadastro from './cadastro/Cadastro'
import Home from './home/Home'
import { authApi } from './services/authApi'
import './App.css'

function App() {
  const [currentUser, setCurrentUser] = useState(() => authApi.getCurrentUser())
  const [currentPage, setCurrentPage] = useState(() => {
    return authApi.isAuthenticated() ? 'home' : 'login'
  })

  // Verifica se o token salvo ainda é válido no backend ao carregar o app
  useEffect(() => {
    if (authApi.isAuthenticated()) {
      authApi.getMe().then((user) => {
        if (user) {
          setCurrentUser(user)
        } else {
          // Token expirado ou invalidado por outro login
          setCurrentUser(null)
          setCurrentPage('login')
        }
      })
    }
  }, [])

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData)
    // Login -> Tela principal
    setCurrentPage('home')
  }

  const handleLogout = async () => {
    await authApi.logout()
    setCurrentUser(null)
    setCurrentPage('login')
  }

  if (currentPage === 'login') {
    return (
      <Login
        onLogin={handleLoginSuccess}
        onNavigateToRegister={() => setCurrentPage('cadastro')}
      />
    )
  }

  if (currentPage === 'cadastro') {
    return (
      <Cadastro
        onNavigateToLogin={() => setCurrentPage('login')}
      />
    )
  }

  return (
    <Home
      currentUser={currentUser}
      onLogout={handleLogout}
    />
  )
}

export default App
