import { useState, useEffect } from 'react'
import Login from './login/Login'
import Cadastro from './cadastro/Cadastro'
import Home from './home/Home'
import Historico from './historico/Historico'
import Landing from './landing/Landing'
import { authApi } from './services/authApi'
import './App.css'

function App() {
  const [currentUser, setCurrentUser] = useState(() => authApi.getCurrentUser())
  // A Landing Page é a página inicial padrão da aplicação
  const [currentPage, setCurrentPage] = useState(() => {
    const path = window.location.pathname.toLowerCase()
    const hash = window.location.hash.toLowerCase()

    // Permite acesso direto via rota/hash se especificado
    if (path === '/app' || hash === '#app' || hash === '#home') {
      return authApi.isAuthenticated() ? 'home' : 'login'
    }
    if (path === '/login' || hash === '#login') {
      return 'login'
    }
    if (path === '/cadastro' || hash === '#cadastro') {
      return 'cadastro'
    }
    if (path === '/historico' || hash === '#historico') {
      return authApi.isAuthenticated() ? 'historico' : 'login'
    }

    // Padrão: primeira página ao executar o frontend
    return 'landing'
  })
  const [pendingHistoryItem, setPendingHistoryItem] = useState(null)

  // Sincroniza navegação via hash (#landing, #app, #login, etc.)
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.toLowerCase()
      if (hash === '#landing' || hash === '#/landing') {
        setCurrentPage('landing')
      } else if (hash === '#app' || hash === '#home') {
        setCurrentPage(authApi.isAuthenticated() ? 'home' : 'login')
      } else if (hash === '#login') {
        setCurrentPage('login')
      } else if (hash === '#cadastro') {
        setCurrentPage('cadastro')
      } else if (hash === '#historico') {
        setCurrentPage(authApi.isAuthenticated() ? 'historico' : 'login')
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Verifica se o token salvo ainda é válido no backend ao carregar o app
  useEffect(() => {
    if (authApi.isAuthenticated()) {
      authApi.getMe().then((user) => {
        if (user) {
          setCurrentUser(user)
        } else {
          // Token expirado ou invalidado por outro login
          setCurrentUser(null)
          if (currentPage === 'home' || currentPage === 'historico') {
            setCurrentPage('login')
          }
        }
      })
    }
  }, [currentPage])

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData)
    // Login -> Tela principal
    setCurrentPage('home')
  }

  const handleLogout = async () => {
    await authApi.logout()
    setCurrentUser(null)
    setPendingHistoryItem(null)
    setCurrentPage('landing')
  }

  const handleSelectHistoryItem = (item) => {
    setPendingHistoryItem(item)
    setCurrentPage('home')
  }

  if (currentPage === 'landing') {
    return (
      <Landing
        onNavigateToApp={() => {
          if (window.location.hash) {
            window.location.hash = ''
          }
          setCurrentPage('login')
        }}
        onNavigateToLogin={() => {
          if (window.location.hash) {
            window.location.hash = ''
          }
          setCurrentPage('login')
        }}
      />
    )
  }

  if (currentPage === 'login') {
    return (
      <Login
        onLogin={handleLoginSuccess}
        onNavigateToRegister={() => setCurrentPage('cadastro')}
        onNavigateToLanding={() => setCurrentPage('landing')}
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
      onNavigateToLanding={() => setCurrentPage('landing')}
      pendingHistoryItem={pendingHistoryItem}
      onClearPendingHistoryItem={() => setPendingHistoryItem(null)}
    />
  )
}

export default App
