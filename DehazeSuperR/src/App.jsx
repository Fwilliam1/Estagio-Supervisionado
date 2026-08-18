import { useState } from 'react'
import Login from './login/Login'
import Cadastro from './cadastro/Cadastro'
import Home from './home/Home'
import Historico from './historico/Historico'
import {
  getCurrentUser,
  setCurrentUser as saveCurrentUser,
  clearCurrentUser,
} from './utils/historyStorage'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('login') // 'login' | 'cadastro' | 'home' | 'historico'
  const [currentUser, setCurrentUserState] = useState(() => getCurrentUser())
  const [pendingHistoryItem, setPendingHistoryItem] = useState(null)

  const handleLogin = (userData) => {
    const user = saveCurrentUser(userData)
    setCurrentUserState(user)
    setCurrentPage('home')
  }

  const handleRegister = (userData) => {
    const user = saveCurrentUser(userData)
    setCurrentUserState(user)
    setCurrentPage('home')
  }

  const handleLogout = () => {
    clearCurrentUser()
    setCurrentUserState(null)
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
        onLogin={handleLogin}
        onNavigateToRegister={() => setCurrentPage('cadastro')}
      />
    )
  }

  if (currentPage === 'cadastro') {
    return (
      <Cadastro
        onRegisterSuccess={handleRegister}
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
      key={pendingHistoryItem ? pendingHistoryItem.id : 'home-default'}
      currentUser={currentUser}
      onLogout={handleLogout}
      onNavigateToHistory={() => setCurrentPage('historico')}
      pendingHistoryItem={pendingHistoryItem}
      onClearPendingHistoryItem={() => setPendingHistoryItem(null)}
    />
  )
}

export default App
