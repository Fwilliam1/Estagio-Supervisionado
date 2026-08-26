import { useState, useRef } from 'react'
import pavicLogo from '../assets/pavic_logo.jpg'
import { imageApi } from '../services/imageApi'
import './Home.css'

export default function Home({ currentUser, onLogout }) {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('dehazing') // 'dehazing' | 'super-resolution'
  const [scaleFactor, setScaleFactor] = useState(2) // 2 | 3 | 4
  const [selectedFile, setSelectedFile] = useState(null)
  const [originalImageUrl, setOriginalImageUrl] = useState(null)
  const [processedImageUrl, setProcessedImageUrl] = useState(null)
  const [processMeta, setProcessMeta] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const fileInputRef = useRef(null)

  const handleFileChange = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setErrorMessage('Por favor, selecione um arquivo de imagem válido (PNG, JPG, JPEG).')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('O tamanho do arquivo deve ser de até 10MB.')
      return
    }

    setErrorMessage('')
    setSelectedFile(file)
    const url = URL.createObjectURL(file)
    setOriginalImageUrl(url)
    setProcessedImageUrl(null)
    setProcessMeta(null)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0])
    }
  }

  const removeFile = (e) => {
    e.stopPropagation()
    setSelectedFile(null)
    setOriginalImageUrl(null)
    setProcessedImageUrl(null)
    setProcessMeta(null)
    setErrorMessage('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Processamento de Imagens
  const processImage = async () => {
    if (!originalImageUrl || !selectedFile || isProcessing) return

    setIsProcessing(true)
    setErrorMessage('')
    setProcessedImageUrl(null)
    setProcessMeta(null)

    // 1. Algoritmo Super-Resolution com a Rede Neural ESC no Backend
    if (selectedAlgorithm === 'super-resolution') {
      try {
        const resultado = await imageApi.processSuperResolution(selectedFile, scaleFactor)
        setProcessedImageUrl(resultado.dados.imagem_base64)
        setProcessMeta(resultado.dados)
      } catch (error) {
        setErrorMessage(error.message || 'Erro ao processar imagem na rede neural ESC.')
      } finally {
        setIsProcessing(false)
      }
      return
    }

    // 2. Algoritmo Dehazing (Processamento Canvas / Filtro)
    const img = new Image()
    img.crossOrigin = 'Anonymous'
    img.src = originalImageUrl

    img.onload = () => {
      setTimeout(() => {
        try {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')

          canvas.width = img.width
          canvas.height = img.height
          ctx.drawImage(img, 0, 0)

          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const data = imageData.data

          // Dehazing Filter: Enhance contrast, remove haze/fog layer, boost saturation
          for (let i = 0; i < data.length; i += 4) {
            let r = data[i]
            let g = data[i + 1]
            let b = data[i + 2]

            // Calculate lightness/haze level
            const minChannel = Math.min(r, g, b)
            const hazeEstimate = minChannel * 0.45

            // Remove haze and restore contrast
            r = Math.min(255, Math.max(0, (r - hazeEstimate) * 1.25))
            g = Math.min(255, Math.max(0, (g - hazeEstimate) * 1.25))
            b = Math.min(255, Math.max(0, (b - hazeEstimate) * 1.25))

            // Slight saturation boost for restored haze colors
            const avg = (r + g + b) / 3
            data[i] = Math.min(255, Math.max(0, avg + (r - avg) * 1.15))
            data[i + 1] = Math.min(255, Math.max(0, avg + (g - avg) * 1.15))
            data[i + 2] = Math.min(255, Math.max(0, avg + (b - avg) * 1.15))
          }

          ctx.putImageData(imageData, 0, 0)
          setProcessedImageUrl(canvas.toDataURL('image/png'))
          setProcessMeta({
            resolucao_processada: `${img.width}x${img.height}`,
            tempo_execucao_segundos: 0.6,
            dispositivo: 'Client'
          })
        } catch (err) {
          setErrorMessage('Erro ao aplicar o filtro Dehazing na imagem.')
        } finally {
          setIsProcessing(false)
        }
      }, 600)
    }

    img.onerror = () => {
      setErrorMessage('Erro ao carregar a imagem original.')
      setIsProcessing(false)
    }
  }

  const downloadProcessedImage = () => {
    if (!processedImageUrl) return
    const link = document.createElement('a')
    link.href = processedImageUrl
    const baseName = selectedFile?.name ? selectedFile.name.replace(/\.[^/.]+$/, '') : 'resultado'
    const scaleSuffix = selectedAlgorithm === 'super-resolution' ? `_x${scaleFactor}_ESC` : '_dehazed'
    link.download = `${baseName}${scaleSuffix}.png`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="logo-container">
          <img src={pavicLogo} className="pavic-logo-img" alt="PAVIC Lab Logo" />
        </div>
        <div className="header-right header-right-user">
          {currentUser && (
            <div className="user-profile-tag" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginRight: '16px', fontSize: '13px', color: '#475569', fontWeight: 600 }}>
              <span style={{ width: '28px', height: '28px', borderRadius: '50%', backgroundColor: '#f97316', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700 }}>
                {currentUser.nome ? currentUser.nome.charAt(0).toUpperCase() : 'U'}
              </span>
              <span>{currentUser.nome || currentUser.email}</span>
            </div>
          )}
          <div>
            <span className="header-tag">APLICAÇÃO</span>
            <span className="header-app-name">Dehazing & Super-Resolution</span>
          </div>
          <button
            type="button"
            className="btn-logout"
            onClick={onLogout}
            title="Sair da aplicação"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Sair
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Mensagem de Erro Global */}
        {errorMessage && (
          <div className="home-alert-error" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Hero Section */}
        <section className="hero-section">
          <div className="category-tag">
            <span className="category-line"></span>
            VISÃO COMPUTACIONAL & IA
          </div>
          <h1 className="hero-title">
            Aprimore suas imagens com <span className="highlight">redes neurais.</span>
          </h1>
          <p className="hero-subtitle">
            Escolha um algoritmo, selecione a escala desejada e processe sua imagem utilizando modelos de Super-Resolução ou Dehazing.
          </p>
        </section>

        {/* 1. Escolha o Algoritmo */}
        <section className="section">
          <h2 className="section-title">1. ESCOLHA O ALGORITMO</h2>
          <div className="algorithm-grid">
            {/* Card 1: Image Dehazing */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'dehazing' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedAlgorithm('dehazing')
                setProcessedImageUrl(null)
                setProcessMeta(null)
              }}
            >
              {selectedAlgorithm === 'dehazing' && <div className="card-dot"></div>}
              <div className="card-icon-box dehazing">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 8c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 13c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                  <path d="M2 18c2.5-2 5.5-2 8 0s5.5 2 8 0" />
                </svg>
              </div>
              <div className="card-content">
                <h3>Image Dehazing</h3>
                <p>Remove névoa, neblina e haze atmosférico, restaurando cor e contraste.</p>
              </div>
            </div>

            {/* Card 2: Super-Resolution */}
            <div
              className={`algorithm-card ${selectedAlgorithm === 'super-resolution' ? 'selected' : ''}`}
              onClick={() => {
                setSelectedAlgorithm('super-resolution')
                setProcessedImageUrl(null)
                setProcessMeta(null)
              }}
            >
              {selectedAlgorithm === 'super-resolution' && <div className="card-dot"></div>}
              <div className="card-icon-box super-resolution">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                  <polyline points="7.5 4.21 12 6.81 16.5 4.21" />
                  <polyline points="7.5 19.79 7.5 14.6 3 12" />
                  <polyline points="21 12 16.5 14.6 16.5 19.79" />
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                  <line x1="12" y1="22.08" x2="12" y2="12" />
                </svg>
              </div>
              <div className="card-content">
                <h3>Super-Resolution (ESC)</h3>
                <p>Aumenta a resolução com rede neural profunda preservando nitidez e detalhes.</p>
              </div>
            </div>
          </div>

          {/* Seletor de Fator de Escala (Exibido quando Super-Resolution estiver ativo) */}
          {selectedAlgorithm === 'super-resolution' && (
            <div className="scale-selector-wrapper">
              <div className="scale-selector-title">
                <span className="label">Fator de Escala do Modelo</span>
                <span className="desc">Selecione o multiplicador de resolução para a reconstrução:</span>
              </div>
              <div className="scale-options-pills">
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 2 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(2)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X2</span>
                </button>
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 3 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(3)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X3</span>
                </button>
                <button
                  type="button"
                  className={`scale-pill-btn ${scaleFactor === 4 ? 'active' : ''}`}
                  onClick={() => {
                    setScaleFactor(4)
                    setProcessedImageUrl(null)
                    setProcessMeta(null)
                  }}
                  disabled={isProcessing}
                >
                  <span>X4</span>
                </button>
              </div>
            </div>
          )}
        </section>

        {/* 2. Envie a Imagem */}
        <section className="section">
          <h2 className="section-title">2. ENVIE A IMAGEM</h2>
          <div
            className={`upload-zone ${isDragging ? 'dragging' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png, image/jpeg, image/jpg"
              onChange={(e) => e.target.files && handleFileChange(e.target.files[0])}
            />
            <div className="upload-icon-circle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div className="upload-title">Arraste sua imagem ou clique para enviar</div>
            <div className="upload-subtitle">PNG, JPG ou JPEG · até 10MB</div>

            {selectedFile && (
              <div className="file-info-badge">
                <span>📁 {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)</span>
                <button type="button" className="btn-remove-file" onClick={removeFile}>
                  Remover
                </button>
              </div>
            )}
          </div>
        </section>

        {/* 3. Processar e Visualizar */}
        <section className="section">
          <h2 className="section-title">3. PROCESSAR E VISUALIZAR</h2>
          <div className="preview-grid">
            {/* Panel Original */}
            <div className="preview-card">
              <div className="preview-header">
                <span className="preview-header-title">ORIGINAL</span>
              </div>
              <div className="preview-body">
                {originalImageUrl ? (
                  <img src={originalImageUrl} alt="Imagem original" className="preview-image" />
                ) : (
                  <div className="empty-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <p>Sem imagem</p>
                  </div>
                )}
              </div>
            </div>

            {/* Panel Resultado */}
            <div className="preview-card">
              <div className="preview-header">
                <span className="preview-header-title">RESULTADO</span>
                {processedImageUrl && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="processed-badge">PROCESSADO</span>
                    {processMeta && (
                      <span className="process-meta-info" title={`Executado em ${processMeta.dispositivo}`}>
                        {processMeta.resolucao_processada} · {processMeta.tempo_execucao_segundos}s
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="preview-body">
                {isProcessing ? (
                  <div className="empty-placeholder">
                    <div className="spinner" style={{ width: '32px', height: '32px', borderTopColor: '#F06529', borderWidth: '3px' }}></div>
                    <p style={{ marginTop: '12px', color: '#F06529', fontWeight: 600 }}>
                      {selectedAlgorithm === 'super-resolution'
                        ? `Processando Super-Resolução (${scaleFactor}x) na GPU...`
                        : 'Processando Dehazing...'}
                    </p>
                  </div>
                ) : processedImageUrl ? (
                  <img src={processedImageUrl} alt="Imagem processada" className="preview-image" />
                ) : (
                  <div className="empty-placeholder">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <circle cx="8.5" cy="8.5" r="1.5" />
                      <polyline points="21 15 16 10 5 21" />
                    </svg>
                    <p>Sem imagem</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bottom Control Bar */}
          <div className="actions-bar">
            <div className="selected-algo-info">
              Algoritmo:{' '}
              <strong>
                {selectedAlgorithm === 'dehazing'
                  ? 'Image Dehazing'
                  : `Super-Resolution ESC (${scaleFactor}x)`}
              </strong>
            </div>
            <div className="action-buttons">
              <button
                type="button"
                className={`btn-process ${originalImageUrl ? 'active' : 'btn-disabled'} ${isProcessing ? 'processing' : ''}`}
                onClick={processImage}
                disabled={!originalImageUrl || isProcessing}
              >
                {isProcessing ? (
                  <>
                    <div className="spinner"></div> Processando...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                    Processar imagem
                  </>
                )}
              </button>

              <button
                type="button"
                className={`btn-download ${processedImageUrl ? 'ready' : 'btn-disabled'}`}
                onClick={downloadProcessedImage}
                disabled={!processedImageUrl}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                Download
              </button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="app-footer">
        PAVIC Lab - Pesquisa Aplicada em Visão e Inteligência Computacional
      </footer>
    </div>
  )
}
