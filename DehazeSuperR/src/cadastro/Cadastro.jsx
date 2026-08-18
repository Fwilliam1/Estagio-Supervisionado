import { useState } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import './Cadastro.css'

export default function Cadastro({ onRegisterSuccess, onNavigateToLogin }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })

  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    setIsSuccess(true)
  }

  return (
    <div className="app-container cadastro-page-wrapper">
      {/* Header */}
      <header className="app-header">
        <div className="logo-container">
          <img src={pavicLogo} className="pavic-logo-img" alt="PAVIC Lab Logo" />
        </div>
        <div className="header-right">
          <span className="header-tag">APLICAÇÃO</span>
          <span className="header-app-name">Dehazing & Super-Resolution</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content cadastro-main-content">
        <div className="cadastro-card-container">
          {!isSuccess ? (
            <div className="cadastro-card">
              <div className="cadastro-card-header">
                <div className="category-tag">
                  <span className="category-line"></span>
                  NOVA CONTA
                </div>
                <h1 className="cadastro-title">
                  Crie sua <span className="highlight">conta</span>
                </h1>
                <p className="cadastro-subtitle">
                  Preencha os campos abaixo para ter acesso às ferramentas de Visão Computacional.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="cadastro-form">
                {/* Nome Completo */}
                <div className="form-group">
                  <label htmlFor="cad-name" className="form-label">
                    NOME COMPLETO
                  </label>
                  <div className="input-icon-wrapper">
                    <span className="input-icon">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </span>
                    <input
                      id="cad-name"
                      name="name"
                      type="text"
                      className="form-input"
                      placeholder="Ex: João da Silva"
                      value={formData.name}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                {/* E-mail */}
                <div className="form-group">
                  <label htmlFor="cad-email" className="form-label">
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
                      id="cad-email"
                      name="email"
                      type="email"
                      className="form-input"
                      placeholder="seu.email@exemplo.com"
                      value={formData.email}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                {/* Senha e Confirmar Senha em Grid */}
                <div className="form-row-2col">
                  {/* Senha */}
                  <div className="form-group">
                    <label htmlFor="cad-password" className="form-label">
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
                        id="cad-password"
                        name="password"
                        type={showPassword ? 'text' : 'password'}
                        className="form-input"
                        placeholder="••••••••"
                        value={formData.password}
                        onChange={handleChange}
                      />
                      <button
                        type="button"
                        className="btn-toggle-password"
                        onClick={() => setShowPassword(!showPassword)}
                        title={showPassword ? "Ocultar senha" : "Exibir senha"}
                      >
                        {showPassword ? (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        ) : (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Confirmar Senha */}
                  <div className="form-group">
                    <label htmlFor="cad-confirm-password" className="form-label">
                      CONFIRMAR SENHA
                    </label>
                    <div className="input-icon-wrapper">
                      <span className="input-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                        </svg>
                      </span>
                      <input
                        id="cad-confirm-password"
                        name="confirmPassword"
                        type={showConfirmPassword ? 'text' : 'password'}
                        className="form-input"
                        placeholder="••••••••"
                        value={formData.confirmPassword}
                        onChange={handleChange}
                      />
                      <button
                        type="button"
                        className="btn-toggle-password"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        title={showConfirmPassword ? "Ocultar confirmação" : "Exibir confirmação"}
                      >
                        {showConfirmPassword ? (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                            <line x1="1" y1="1" x2="23" y2="23" />
                          </svg>
                        ) : (
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Botão de Cadastro */}
                <button type="submit" className="btn-cadastro-submit">
                  <span>Criar minha conta</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>

                {/* Divisor */}
                <div className="cadastro-divider">
                  <span>Já possui conta?</span>
                </div>

                {/* Botão de Voltar para Login */}
                <button
                  type="button"
                  className="btn-back-to-login"
                  onClick={onNavigateToLogin}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12" />
                    <polyline points="12 19 5 12 12 5" />
                  </svg>
                  <span>Fazer login</span>
                </button>
              </form>
            </div>
          ) : (
            /* Tela de Sucesso */
            <div className="cadastro-card success-card">
              <div className="success-icon-circle">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h2 className="cadastro-title">Cadastro realizado com sucesso!</h2>
              <p className="cadastro-subtitle">
                {formData.name ? (
                  <>Bem-vindo(a) ao PAVIC Lab, <strong>{formData.name}</strong>! Sua conta foi criada e está pronta para uso.</>
                ) : (
                  <>Bem-vindo(a) ao PAVIC Lab! Sua conta foi criada e está pronta para uso.</>
                )}
              </p>

              <div className="success-actions">
                <button
                  type="button"
                  className="btn-cadastro-submit"
                  onClick={() =>
                    onRegisterSuccess({
                      name: formData.name.trim() || formData.email.split('@')[0],
                      email: formData.email.trim(),
                    })
                  }
                >
                  <span>Acessar plataforma agora</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>

                <button
                  type="button"
                  className="btn-back-to-login"
                  onClick={onNavigateToLogin}
                >
                  <span>Ir para tela de login</span>
                </button>
              </div>
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
