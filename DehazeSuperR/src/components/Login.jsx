import { useState } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import './Login.css'

export default function Login({ onLogin }) {
  const [view, setView] = useState('login') // 'login' | 'forgot-password' | 'success-reset'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    // Como solicitado, não precisa de validação real agora.
    onLogin()
  }

  const handleForgotPasswordSubmit = (e) => {
    e.preventDefault()
    setView('success-reset')
  }

  return (
    <div className="app-container login-page-wrapper">
      {/* Top Header matching App header */}
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
                      onChange={(e) => setEmail(e.target.value)}
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
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-toggle-password"
                      onClick={() => setShowPassword(!showPassword)}
                      title={showPassword ? "Ocultar senha" : "Exibir senha"}
                    >
                      {showPassword ? (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </svg>
                      ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                {/* Opções extras: Lembrar de mim & Esqueci a senha */}
                <div className="login-options-row">
                  <label className="remember-me-label">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="custom-checkbox"
                    />
                    <span>Lembrar de mim</span>
                  </label>
                  <button
                    type="button"
                    className="btn-forgot-password"
                    onClick={() => setView('forgot-password')}
                  >
                    Esqueci a senha
                  </button>
                </div>

                {/* Botão de Entrar */}
                <button type="submit" className="btn-login-submit">
                  <span>Entrar</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
              </form>
            </div>
          )}

          {/* View: Esqueci a Senha */}
          {view === 'forgot-password' && (
            <div className="login-card">
              <div className="login-card-header">
                <div className="category-tag">
                  <span className="category-line"></span>
                  RECUPERAÇÃO DE CONTA
                </div>
                <h1 className="login-title">
                  Recuperar <span className="highlight">senha</span>
                </h1>
                <p className="login-subtitle">
                  Informe o seu e-mail cadastrado e enviaremos as instruções para redefinição.
                </p>
              </div>

              <form onSubmit={handleForgotPasswordSubmit} className="login-form">
                <div className="form-group">
                  <label htmlFor="reset-email" className="form-label">
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
                      id="reset-email"
                      type="email"
                      className="form-input"
                      placeholder="seu.email@exemplo.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>

                <button type="submit" className="btn-login-submit">
                  <span>Enviar link de recuperação</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>

                <button
                  type="button"
                  className="btn-back-to-login"
                  onClick={() => setView('login')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12" />
                    <polyline points="12 19 5 12 12 5" />
                  </svg>
                  <span>Voltar para o login</span>
                </button>
              </form>
            </div>
          )}

          {/* View: E-mail Enviado */}
          {view === 'success-reset' && (
            <div className="login-card success-card">
              <div className="success-icon-circle">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h2 className="login-title">E-mail enviado!</h2>
              <p className="login-subtitle">
                Enviamos as instruções de recuperação para <strong>{email || 'seu e-mail'}</strong>. Verifique sua caixa de entrada.
              </p>

              <button
                type="button"
                className="btn-login-submit"
                onClick={() => setView('login')}
                style={{ marginTop: '20px' }}
              >
                <span>Voltar para o login</span>
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Footer matching App footer */}
      <footer className="app-footer">
        PAVIC Lab - Pesquisa Aplicada em Visão e Inteligência Computacional
      </footer>
    </div>
  )
}
