import { useState, useEffect } from 'react'
import Login from './login/Login'
import Cadastro from './cadastro/Cadastro'
import Home from './home/Home'
import Historico from './historico/Historico'
import { authApi } from './services/authApi'
import './App.css'

function App() {
  const [currentUser, setCurrentUser] = useState(() => authApi.getCurrentUser())
  const [currentPage, setCurrentPage] = useState(() => {
    return authApi.isAuthenticated() ? 'home' : 'login'
  })
  const [pendingHistoryItem, setPendingHistoryItem] = useState(null)

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
    setPendingHistoryItem(null)
    setCurrentPage('login')
  }

  const handleSelectHistoryItem = (item) => {
    setPendingHistoryItem(item)
    setCurrentPage('home')
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

  if (currentPage === 'historico') {
    return (
      <Historico
        currentUser={currentUser}
        onNavigateToHome={() => setCurrentPage('home')}
        onSelectHistoryItem={handleSelectHistoryItem}
        onLogout={handleLogout}
      />
    )
  }

  return (
    <Home
      currentUser={currentUser}
      onLogout={handleLogout}
      onNavigateToHistory={() => setCurrentPage('historico')}
      pendingHistoryItem={pendingHistoryItem}
      onClearPendingHistoryItem={() => setPendingHistoryItem(null)}
    />
  )
}

export default App

