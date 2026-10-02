import { useState } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import { authApi } from '../services/authApi'
import './Login.css'

export default function Login({ onLogin, onNavigateToRegister, onNavigateToLanding }) {
  const [view, setView] = useState('login') // 'login'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorMessage('')

    if (!email.trim()) {
      setErrorMessage('Por favor, informe seu e-mail.')
      return
    }

    if (!password) {
      setErrorMessage('Por favor, informe sua senha.')
      return
    }

    try {
      setIsLoading(true)
      const data = await authApi.login({ email, password })
      // Login com sucesso -> navega para a Tela Principal
      onLogin(data.dados)
    } catch (error) {
      setErrorMessage(error.message || 'Erro ao efetuar login.')
    } finally {
      setIsLoading(false)
    }
  }


  return (
    <div className="app-container login-page-wrapper">
      {/* Top Header */}
      <header className="app-header">
        <div className="logo-container">
          <img src={pavicLogo} className="pavic-logo-img" alt="PAVIC Lab Logo" />
        </div>
        <div className="header-right">
          <span className="header-tag">APLICAÇÃO</span>
          <span className="header-app-name">Dehazing & Super-Resolution</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content login-main-content">
        <div className="login-card-container">
          {view === 'login' && (
            <div className="login-card">
              <div className="login-card-header">
                <div className="category-tag">
                  <span className="category-line"></span>
                  AUTENTICAÇÃO
                </div>
                <h1 className="login-title">
                  Acesse a <span className="highlight">plataforma</span>
                </h1>
                <p className="login-subtitle">
                  Entre com suas credenciais para acessar as ferramentas de Visão Computacional.
                </p>
              </div>

              {/* Mensagem de Erro de Autenticação */}
              {errorMessage && (
                <div className="login-alert-error" role="alert">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span>{errorMessage}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="login-form">
                {/* Campo E-mail */}
                <div className="form-group">
                  <label htmlFor="login-email" className="form-label">
                    E-MAIL
                  </label>
                  <div className="input-icon-wrapper">
                    <span className="input-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="4" width="20" height="16" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                      </svg>
                    </span>
                    <input
                      id="login-email"
                      type="email"
                      className="form-input"
                      placeholder="seu.email@exemplo.com"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value)
                        if (errorMessage) setErrorMessage('')
                      }}
                      disabled={isLoading}
                      required
                    />
                  </div>
                </div>

                {/* Campo Senha */}
                <div className="form-group">
                  <label htmlFor="login-password" className="form-label">
                    SENHA
                  </label>
                  <div className="input-icon-wrapper">
                    <span className="input-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                      </svg>
                    </span>
                    <input
                      id="login-password"
                      type={showPassword ? 'text' : 'password'}
                      className="form-input"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value)
                        if (errorMessage) setErrorMessage('')
                      }}
                      disabled={isLoading}
                      required
                    />
                    <button
                      type="button"
                      className="btn-toggle-password"
                      onClick={() => setShowPassword(!showPassword)}
                      title={showPassword ? "Ocultar senha" : "Exibir senha"}
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>



                {/* Botão de Entrar */}
                <button
                  type="submit"
                  className="btn-login-submit"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <div className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2px', borderColor: '#ffffff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
                      <span>Entrando...</span>
                    </>
                  ) : (
                    <>
                      <span>Entrar</span>
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="5" y1="12" x2="19" y2="12" />
                        <polyline points="12 5 19 12 12 19" />
                      </svg>
                    </>
                  )}
                </button>

                {/* Divisor */}
                <div className="login-divider">
                  <span>ou</span>
                </div>

                {/* Botão de Cadastrar / Criar Conta */}
                <button
                  type="button"
                  className="btn-register-secondary"
                  onClick={onNavigateToRegister}
                  disabled={isLoading}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <line x1="19" y1="8" x2="19" y2="14" />
                    <line x1="22" y1="11" x2="16" y2="11" />
                  </svg>
                  <span>Cadastrar nova conta</span>
                </button>

                {/* Link para Landing Page / Sobre o Projeto */}
                <div style={{ textAlign: 'center', marginTop: '16px' }}>
                  <button
                    type="button"
                    onClick={onNavigateToLanding || (() => { window.location.hash = '#landing' })}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--brand-blue, #2563eb)',
                      fontSize: '13px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textDecoration: 'underline',
                    }}
                  >
                    Apresentação do Projeto
                  </button>
                </div>
              </form>
            </div>
          )}


        </div>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        PAVIC Lab - Pesquisa Aplicada em Visão e Inteligência Computacional
      </footer>
    </div>
  )
}
