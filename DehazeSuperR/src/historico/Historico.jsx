import { useState, useMemo, useEffect } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import {
  getUserHistory,
  fetchUserHistoryFromApi,
  deleteHistoryItem,
  clearUserHistory,
} from '../utils/historyStorage'
import './Historico.css'

export default function Historico({
  currentUser,
  onNavigateToHome,
  onSelectHistoryItem,
  onLogout,
}) {
  const [historyList, setHistoryList] = useState(() =>
    getUserHistory(currentUser?.email)
  )
  const [filterProcess, setFilterProcess] = useState('all') // 'all' | 'dehazing' | 'super-resolution'
  const [searchTerm, setSearchTerm] = useState('')

  // Sincroniza com o banco de dados Django via API REST ao abrir a tela
  useEffect(() => {
    let isMounted = true
    if (currentUser?.email) {
      fetchUserHistoryFromApi(currentUser.email).then((apiData) => {
        if (isMounted && Array.isArray(apiData)) {
          setHistoryList(apiData)
        }
      })
    }
    return () => {
      isMounted = false
    }
  }, [currentUser])

  // Filtragem dos itens de histórico
  const filteredHistory = useMemo(() => {
    return historyList.filter((item) => {
      const isSR =
        item.process === 'super-resolution' ||
        String(item.process || '').toLowerCase().includes('super-resolution') ||
        String(item.process || '').toLowerCase().includes('esc')

      const normalizedProcess = isSR ? 'super-resolution' : 'dehazing'

      const matchFilter =
        filterProcess === 'all' || normalizedProcess === filterProcess

      const matchSearch =
        searchTerm.trim() === '' ||
        (item.fileName &&
          item.fileName.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (item.date && item.date.includes(searchTerm)) ||
        (item.processLabel &&
          item.processLabel.toLowerCase().includes(searchTerm.toLowerCase()))

      return matchFilter && matchSearch
    })
  }, [historyList, filterProcess, searchTerm])

  const handleDeleteItem = async (e, itemId) => {
    e.stopPropagation()
    if (window.confirm('Deseja realmente remover esta imagem do seu histórico?')) {
      const updated = await deleteHistoryItem(currentUser?.email, itemId)
      setHistoryList(updated)
    }
  }

  const handleClearAll = async () => {
    if (
      window.confirm(
        'Tem certeza que deseja apagar TODO o seu histórico de imagens? Esta ação não pode ser desfeita.'
      )
    ) {
      await clearUserHistory(currentUser?.email)
      setHistoryList([])
    }
  }

  const handleCardClick = (item) => {
    // Retorna para a página inicial carregando e re-enviando a imagem
    onSelectHistoryItem(item)
  }

  return (
    <div className="app-container history-page-wrapper">
      {/* Top Header */}
      <header className="app-header">
        <div className="logo-container">
          <img src={pavicLogo} className="pavic-logo-img" alt="PAVIC Lab Logo" />
        </div>
        <div className="header-right header-right-user">
          <div className="user-profile-badge">
            <div className="user-avatar-circle">
              {(currentUser?.name || currentUser?.email || 'U')
                .charAt(0)
                .toUpperCase()}
            </div>
            <div className="user-info-text">
              <span className="header-tag">USUÁRIO CONECTADO</span>
              <span className="header-app-name">
                {currentUser?.name || currentUser?.email || 'Usuário'}
              </span>
            </div>
          </div>

          <div className="header-nav-actions">
            <button
              type="button"
              className="btn-header-nav"
              onClick={onNavigateToHome}
              title="Voltar para a página inicial"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              Início
            </button>

            <button
              type="button"
              className="btn-logout"
              onClick={onLogout}
              title="Sair da aplicação"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Sair
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content history-main-content">
        {/* Hero Section */}
        <section className="hero-section">
          <div className="category-tag">
            <span className="category-line"></span>
            HISTÓRICO DE PROCESSAMENTOS
          </div>
          <div className="hero-header-row">
            <div>
              <h1 className="hero-title">
                Histórico de <span className="highlight">Imagens</span>
              </h1>
              <p className="hero-subtitle">
                Acompanhe o registro de imagens processadas para sua conta (
                <strong>{currentUser?.email}</strong>). Clique em qualquer item
                para carregar a imagem e enviá-la novamente para processamento na
                página inicial.
              </p>
            </div>
            {historyList.length > 0 && (
              <button
                type="button"
                className="btn-clear-history"
                onClick={handleClearAll}
                title="Limpar todos os registros do seu histórico"
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                Limpar Histórico
              </button>
            )}
          </div>
        </section>

        {/* Barra de Filtros e Busca */}
        <div className="history-toolbar">
          {/* Abas de Filtro */}
          <div className="history-filter-tabs">
            <button
              type="button"
              className={`filter-tab ${filterProcess === 'all' ? 'active' : ''}`}
              onClick={() => setFilterProcess('all')}
            >
              Todos ({historyList.length})
            </button>
            <button
              type="button"
              className={`filter-tab ${filterProcess === 'dehazing' ? 'active' : ''}`}
              onClick={() => setFilterProcess('dehazing')}
            >
              <span className="filter-dot dehaze-dot"></span>
              Dehazing (
              {historyList.filter((i) => !String(i.process || '').toLowerCase().includes('super-resolution') && !String(i.process || '').toLowerCase().includes('esc')).length})
            </button>
            <button
              type="button"
              className={`filter-tab ${filterProcess === 'super-resolution' ? 'active' : ''}`}
              onClick={() => setFilterProcess('super-resolution')}
            >
              <span className="filter-dot sr-dot"></span>
              Super-Resolution (
              {historyList.filter((i) => String(i.process || '').toLowerCase().includes('super-resolution') || String(i.process || '').toLowerCase().includes('esc')).length})
            </button>
          </div>

          {/* Campo de Busca */}
          <div className="history-search-wrapper">
            <svg
              className="search-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="search-input"
              placeholder="Buscar por arquivo, data ou algoritmo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button
                type="button"
                className="btn-clear-search"
                onClick={() => setSearchTerm('')}
                title="Limpar busca"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Lista de Registros */}
        {filteredHistory.length > 0 ? (
          <div className="history-grid">
            {filteredHistory.map((item) => (
              <div
                key={item.id}
                className="history-card"
                onClick={() => handleCardClick(item)}
                title="Clique para voltar à página inicial e reenviar esta imagem"
              >
                {/* Visual Header / Process Badge */}
                <div className="history-card-header">
                  <div
                    className={`process-pill ${
                      item.process === 'dehazing'
                        ? 'pill-dehazing'
                        : 'pill-super-resolution'
                    }`}
                  >
                    {item.process === 'dehazing' ? (
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M2 8c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                        <path d="M2 13c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                        <path d="M2 18c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                      </svg>
                    ) : (
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      </svg>
                    )}
                    <span>{item.processLabel}</span>
                  </div>

                  <button
                    type="button"
                    className="btn-delete-item"
                    onClick={(e) => handleDeleteItem(e, item.id)}
                    title="Excluir item do histórico"
                  >
                    <svg
                      width="15"
                      height="15"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>

                {/* Imagem de Entrada Container */}
                <div className="history-image-preview-container">
                  <div className="image-wrapper">
                    <img
                      src={item.inputImage}
                      alt={`Entrada: ${item.fileName}`}
                      className="history-input-img"
                    />
                    <span className="input-image-tag">IMAGEM DE ENTRADA</span>
                  </div>

                  {item.processedImage && (
                    <div className="image-wrapper processed-thumb">
                      <img
                        src={item.processedImage}
                        alt={`Resultado: ${item.fileName}`}
                        className="history-input-img"
                      />
                      <span className="input-image-tag result-tag">
                        RESULTADO
                      </span>
                    </div>
                  )}
                </div>

                {/* Detalhes do Registro: Data, Hora, Arquivo e Processo */}
                <div className="history-card-details">
                  <div className="history-file-name" title={item.fileName}>
                    📁 {item.fileName || 'imagem_upload.png'}
                  </div>

                  <div className="history-meta-grid">
                    {/* Data */}
                    <div className="history-meta-item">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <rect
                          x="3"
                          y="4"
                          width="18"
                          height="18"
                          rx="2"
                          ry="2"
                        />
                        <line x1="16" y1="2" x2="16" y2="6" />
                        <line x1="8" y1="2" x2="8" y2="6" />
                        <line x1="3" y1="10" x2="21" y2="10" />
                      </svg>
                      <span>
                        <strong>Data:</strong> {item.date}
                      </span>
                    </div>

                    {/* Hora */}
                    <div className="history-meta-item">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12 6 12 12 16 14" />
                      </svg>
                      <span>
                        <strong>Hora:</strong> {item.time}
                      </span>
                    </div>

                    {/* Tamanho */}
                    {item.fileSize && (
                      <div className="history-meta-item">
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                          <polyline points="7 10 12 15 17 10" />
                          <line x1="12" y1="15" x2="12" y2="3" />
                        </svg>
                        <span>
                          <strong>Tamanho:</strong> {item.fileSize}
                        </span>
                      </div>
                    )}

                    {/* Algoritmo Escolhido */}
                    <div className="history-meta-item">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polygon points="12 2 2 7 12 12 22 7 12 2" />
                        <polyline points="2 17 12 22 22 17" />
                        <polyline points="2 12 12 17 22 12" />
                      </svg>
                      <span>
                        <strong>Processo:</strong> {item.processLabel}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Action Callout */}
                <div className="history-card-action">
                  <span>Reenviar e Processar na Página Inicial</span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* Estado Vazio */
          <div className="history-empty-state">
            <div className="empty-state-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
            </div>
            <h3 className="empty-state-title">
              {searchTerm || filterProcess !== 'all'
                ? 'Nenhuma imagem encontrada com os filtros atuais'
                : 'Nenhuma imagem no seu histórico'}
            </h3>
            <p className="empty-state-subtitle">
              {searchTerm || filterProcess !== 'all'
                ? 'Tente ajustar sua busca ou selecionar outro filtro de algoritmo.'
                : 'Todas as imagens que você enviar e processar na página inicial serão salvas automaticamente aqui no seu histórico individual.'}
            </p>
            <button
              type="button"
              className="btn-go-home"
              onClick={onNavigateToHome}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Enviar e processar uma imagem
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        PAVIC Lab - Pesquisa Aplicada em Visão e Inteligência Computacional
      </footer>
    </div>
  )
}
